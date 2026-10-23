"""Commandes : proposition issue du moteur de correspondance, accord des deux parties, notifications.

Une commande n'est « confirmée » que si chaque éleveur et chaque acheteur concerné a répondu OUI.
Un seul NON annule la commande et libère les demandes et offres encore valables.
"""
import re
import sqlite3

from . import config, matching
from .db import transaction
from .pricing import ComposantesPrix

LIBELLES = {"poulet_chair": "poulets de chair", "oeufs": "œufs", "pondeuse": "pondeuses"}


def _notifier(conn, phone: str, texte: str) -> None:
    conn.execute("INSERT INTO outbox(phone, body) VALUES (?, ?)", (phone, texte))


def _prix_rendu_livre(propositions: list[dict], quantite: int) -> float | None:
    """Moyenne pondérée des offres, transport estimé par kilomètre, pertes incluses.
    None si un prix manque : on n'affiche jamais un prix inventé."""
    if not propositions or any(p["prix_fcfa"] is None for p in propositions):
        return None
    produit = sum(p["prix_fcfa"] * p["quantite"] for p in propositions)
    transport = sum(p["distance_km"] * config.TRANSPORT_FCFA_PAR_KM for p in propositions)
    c = ComposantesPrix(
        prix_produit_fcfa=round(produit / quantite),
        transport_total_fcfa=round(transport),
        perte_estimee_pct=config.PERTE_ESTIMEE_PCT,
    )
    return c.prix_rendu_livre(quantite)


def proposer_commande(conn: sqlite3.Connection, produit: str, localite: str, date_livraison: str) -> dict | None:
    """Crée une commande en attente à partir des demandes et offres compatibles, et notifie chacun."""
    prop = matching.proposer(conn, produit, localite, date_livraison)
    if not prop["propositions"]:
        return None
    couverte = prop["quantite_couverte"]
    prix = _prix_rendu_livre(prop["propositions"], couverte)
    nom = LIBELLES.get(produit, produit)
    quand = f"le {date_livraison} à {localite.capitalize()}"

    with transaction(conn):
        oid = conn.execute(
            "INSERT INTO orders(produit, localite, date_livraison, quantite, prix_rendu_livre_fcfa) VALUES (?,?,?,?,?)",
            (produit, localite, date_livraison, couverte, prix),
        ).lastrowid

        # Les quantités couvertes sont attribuées aux demandes dans l'ordre d'arrivée.
        restant = couverte
        for d in conn.execute(
            "SELECT * FROM demands WHERE statut='ouverte' AND produit=? AND localite=? AND date_livraison=? ORDER BY id",
            (produit, localite, date_livraison),
        ).fetchall():
            if restant <= 0:
                break
            q = min(restant, d["quantite"])
            restant -= q
            conn.execute(
                "INSERT INTO order_buyers(order_id, demand_id, buyer_phone, quantite) VALUES (?,?,?,?)",
                (oid, d["id"], d["buyer_phone"], q),
            )
            conn.execute("UPDATE demands SET statut='en_proposition' WHERE id=?", (d["id"],))
            ligne_prix = f" Prix rendu livré estimé : {prix:.0f} FCFA/unité (hypothèses de transport et de pertes)." if prix else ""
            _notifier(conn, d["buyer_phone"],
                      f"Proposition n°{oid} : {q} {nom} {quand}.{ligne_prix} Répondez OUI {oid} ou NON {oid}.")

        for p in prop["propositions"]:
            conn.execute(
                "INSERT INTO order_lines(order_id, offer_id, farmer_phone, quantite, prix_fcfa, distance_km) VALUES (?,?,?,?,?,?)",
                (oid, p["offre_id"], p["eleveur"], p["quantite"], p["prix_fcfa"], p["distance_km"]),
            )
            conn.execute("UPDATE offers SET statut='en_proposition' WHERE id=?", (p["offre_id"],))
            prix_txt = f" à {p['prix_fcfa']} FCFA" if p["prix_fcfa"] else ""
            _notifier(conn, p["eleveur"],
                      f"Proposition n°{oid} : livrer {p['quantite']} {nom}{prix_txt} {quand}. Répondez OUI {oid} ou NON {oid}.")
    return detail(conn, oid)


def detail(conn: sqlite3.Connection, oid: int) -> dict | None:
    o = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if o is None:
        return None
    return {
        **dict(o),
        "eleveurs": [dict(r) for r in conn.execute("SELECT * FROM order_lines WHERE order_id=?", (oid,))],
        "acheteurs": [dict(r) for r in conn.execute("SELECT * FROM order_buyers WHERE order_id=?", (oid,))],
    }


def en_attente_pour(conn: sqlite3.Connection, phone: str) -> list[int]:
    """Commandes en attente où cette personne n'a pas encore répondu, la plus récente d'abord."""
    rows = conn.execute(
        "SELECT DISTINCT o.id FROM orders o "
        "LEFT JOIN order_lines l ON l.order_id=o.id AND l.farmer_phone=? AND l.accord IS NULL "
        "LEFT JOIN order_buyers b ON b.order_id=o.id AND b.buyer_phone=? AND b.accord IS NULL "
        "WHERE o.statut='en_attente' AND (l.id IS NOT NULL OR b.id IS NOT NULL) ORDER BY o.id DESC",
        (phone, phone),
    ).fetchall()
    return [r["id"] for r in rows]


def repondre(conn: sqlite3.Connection, phone: str, texte: str, accepte: bool) -> str | None:
    """Applique un OUI / NON (avec ou sans numéro) à une commande en attente. None si rien à traiter."""
    en_attente = en_attente_pour(conn, phone)
    if not en_attente:
        return None
    m = re.search(r"\b(\d+)\b", texte)
    oid = int(m[1]) if m else en_attente[0]
    if oid not in en_attente:
        return f"Je ne trouve pas de proposition n°{oid} en attente pour vous."

    valeur = 1 if accepte else 0
    with transaction(conn):
        conn.execute("UPDATE order_lines SET accord=? WHERE order_id=? AND farmer_phone=? AND accord IS NULL", (valeur, oid, phone))
        conn.execute("UPDATE order_buyers SET accord=? WHERE order_id=? AND buyer_phone=? AND accord IS NULL", (valeur, oid, phone))
        reponse = _conclure(conn, oid, phone, accepte)
    return reponse


def _conclure(conn, oid: int, phone: str, accepte: bool) -> str:
    concernes = {r[0] for r in conn.execute(
        "SELECT farmer_phone FROM order_lines WHERE order_id=? UNION SELECT buyer_phone FROM order_buyers WHERE order_id=?",
        (oid, oid))}
    if not accepte:
        conn.execute("UPDATE orders SET statut='annulee' WHERE id=?", (oid,))
        conn.execute("UPDATE offers SET statut='ouverte' WHERE id IN (SELECT offer_id FROM order_lines WHERE order_id=? AND (accord IS NULL OR accord=1))", (oid,))
        conn.execute("UPDATE offers SET statut='refusee' WHERE id IN (SELECT offer_id FROM order_lines WHERE order_id=? AND accord=0)", (oid,))
        conn.execute("UPDATE demands SET statut='ouverte' WHERE id IN (SELECT demand_id FROM order_buyers WHERE order_id=?)", (oid,))
        for p in concernes - {phone}:
            _notifier(conn, p, f"La proposition n°{oid} est annulée (une partie a refusé). Votre demande ou disponibilité reste ouverte.")
        return f"Proposition n°{oid} refusée. Votre entrée reste ouverte pour d'autres propositions."

    reste = conn.execute(
        "SELECT (SELECT COUNT(*) FROM order_lines WHERE order_id=? AND accord IS NOT 1) + "
        "(SELECT COUNT(*) FROM order_buyers WHERE order_id=? AND accord IS NOT 1)", (oid, oid)).fetchone()[0]
    if reste:
        return f"Merci, votre accord pour la proposition n°{oid} est enregistré. J'attends les autres parties."
    conn.execute("UPDATE orders SET statut='confirmee' WHERE id=?", (oid,))
    conn.execute("INSERT INTO order_events(order_id, etape, phone) VALUES (?, 'confirmee', ?)", (oid, phone))
    conn.execute("UPDATE offers SET statut='engagee' WHERE id IN (SELECT offer_id FROM order_lines WHERE order_id=?)", (oid,))
    conn.execute("UPDATE demands SET statut='engagee' WHERE id IN (SELECT demand_id FROM order_buyers WHERE order_id=?)", (oid,))
    for p in concernes - {phone}:
        _notifier(conn, p, f"Commande n°{oid} confirmée par toutes les parties. Je vous enverrai les étapes de livraison.")
    return f"Commande n°{oid} confirmée par toutes les parties."


def recuperer_notifications(conn: sqlite3.Connection, phone: str) -> list[str]:
    rows = conn.execute("SELECT id, body FROM outbox WHERE phone=? AND delivered=0 ORDER BY id", (phone,)).fetchall()
    with transaction(conn):
        conn.executemany("UPDATE outbox SET delivered=1 WHERE id=?", [(r["id"],) for r in rows])
    return [r["body"] for r in rows]


ETAPES = ["collecte", "en_route", "livre"]
LIBELLE_ETAPE = {"collecte": "collectée", "en_route": "en route", "livre": "livrée"}


def _parties(conn, oid: int) -> set[str]:
    return {r[0] for r in conn.execute(
        "SELECT farmer_phone FROM order_lines WHERE order_id=? UNION SELECT buyer_phone FROM order_buyers WHERE order_id=?",
        (oid, oid))}


def assigner_transporteur(conn: sqlite3.Connection, oid: int, phone: str) -> dict:
    o = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if o is None:
        raise LookupError("commande inconnue")
    if o["statut"] != "confirmee" or o["transporteur_phone"]:
        raise ValueError("la commande doit être confirmée et sans transporteur")
    t = conn.execute("SELECT role FROM actors WHERE phone=?", (phone,)).fetchone()
    if t is None or t["role"] != "transporteur":
        raise ValueError("ce numéro n'est pas un transporteur inscrit")
    with transaction(conn):
        conn.execute("UPDATE orders SET transporteur_phone=? WHERE id=?", (phone, oid))
        conn.execute("INSERT INTO order_events(order_id, etape, phone) VALUES (?, 'assignee', ?)", (oid, phone))
        nom = LIBELLES.get(o["produit"], o["produit"])
        _notifier(conn, phone, f"Mission commande n°{oid} : {o['quantite']} {nom} à livrer le {o['date_livraison']} à "
                               f"{o['localite'].capitalize()}. Écrivez COLLECTÉ, EN ROUTE puis LIVRÉ au fil de la mission.")
        for p in _parties(conn, oid):
            _notifier(conn, p, f"Un transporteur est assigné à la commande n°{oid}.")
    return detail(conn, oid)


def enregistrer_etape(conn: sqlite3.Connection, oid: int, etape: str, phone: str) -> str:
    """Enregistre une étape dans l'ordre collecte -> en_route -> livre, par le transporteur assigné."""
    o = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
    if o is None or o["transporteur_phone"] != phone:
        raise ValueError("commande non assignée à ce transporteur")
    faites = [r[0] for r in conn.execute(
        "SELECT etape FROM order_events WHERE order_id=? AND etape IN ('collecte','en_route','livre')", (oid,))]
    attendue = next((e for e in ETAPES if e not in faites), None)
    if etape != attendue:
        raise ValueError(f"étape attendue : {attendue}" if attendue else "commande déjà livrée")
    with transaction(conn):
        conn.execute("INSERT INTO order_events(order_id, etape, phone) VALUES (?,?,?)", (oid, etape, phone))
        if etape == "livre":
            conn.execute("UPDATE orders SET statut='livree' WHERE id=?", (oid,))
        for p in _parties(conn, oid):
            _notifier(conn, p, f"Commande n°{oid} : {LIBELLE_ETAPE[etape]}.")
    return f"Étape « {LIBELLE_ETAPE[etape]} » enregistrée pour la commande n°{oid}."


def mission_en_cours(conn: sqlite3.Connection, phone: str) -> int | None:
    r = conn.execute("SELECT id FROM orders WHERE transporteur_phone=? AND statut='confirmee' ORDER BY id LIMIT 1", (phone,)).fetchone()
    return r["id"] if r else None


def lot_public(conn: sqlite3.Connection, oid: int) -> dict | None:
    """Fiche de lot publique : aucune coordonnée de contact, provenance déclarative."""
    o = conn.execute("SELECT * FROM orders WHERE id=? AND statut IN ('confirmee','livree')", (oid,)).fetchone()
    if o is None:
        return None
    sources = conn.execute(
        "SELECT l.quantite, l.distance_km, f.localite, a.verification FROM order_lines l "
        "JOIN offers f ON f.id=l.offer_id JOIN actors a ON a.phone=l.farmer_phone WHERE l.order_id=?", (oid,)).fetchall()
    events = conn.execute("SELECT etape, created_at FROM order_events WHERE order_id=? ORDER BY id", (oid,)).fetchall()
    return {
        "code": f"LOT-{oid:04d}", "produit": o["produit"], "quantite": o["quantite"],
        "livraison": {"localite": o["localite"], "date": o["date_livraison"]}, "statut": o["statut"],
        "provenance_declaree": [dict(r) for r in sources], "evenements": [dict(r) for r in events],
        "avertissement": "Traçabilité déclarative issue de la plateforme : ce n'est pas une certification sanitaire.",
    }


def statistiques(conn: sqlite3.Connection) -> dict:
    n = lambda q: conn.execute(q).fetchone()[0]
    confirmees = n("SELECT COUNT(*) FROM orders WHERE statut IN ('confirmee','livree')")
    livrees = n("SELECT COUNT(*) FROM orders WHERE statut='livree'")
    propositions = n("SELECT COUNT(*) FROM orders")
    return {
        "demandes_ouvertes": n("SELECT COUNT(*) FROM demands WHERE statut='ouverte'"),
        "offres_ouvertes": n("SELECT COUNT(*) FROM offers WHERE statut='ouverte'"),
        "propositions": propositions,
        "commandes_confirmees": confirmees,
        "commandes_livrees": livrees,
        "commandes_annulees": n("SELECT COUNT(*) FROM orders WHERE statut='annulee'"),
        "taux_confirmation": round(confirmees / propositions, 2) if propositions else None,
        "taux_livraison": round(livrees / confirmees, 2) if confirmees else None,
        "volume_local_engage": n("SELECT COALESCE(SUM(quantite),0) FROM orders WHERE statut IN ('confirmee','livree')"),
        "volume_local_livre": n("SELECT COALESCE(SUM(quantite),0) FROM orders WHERE statut='livree'"),
        "prix_rendu_livre_moyen_fcfa": conn.execute(
            "SELECT ROUND(AVG(prix_rendu_livre_fcfa)) FROM orders WHERE statut IN ('confirmee','livree')").fetchone()[0],
        "unite": "unités (poulets, œufs…) du scénario simulé",
        "reference": {
            "texte": "Couverture nationale des besoins en viandes et abats : 48–49 % sur 2019–2024 (indicateur global, toutes espèces).",
            "source": "Portail d'information économique de Côte d'Ivoire, rubrique Élevage",
            "avertissement": "Contexte uniquement : ces chiffres ne mesurent pas un effet de la plateforme.",
        },
    }
