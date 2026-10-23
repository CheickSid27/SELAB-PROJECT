"""Machine à états de la conversation WhatsApp (ou du simulateur).

Principe : l'agent structure et pose des questions ; il n'enregistre une demande ou
une offre qu'après un « oui » explicite de la personne.
"""
import json
import sqlite3
from datetime import date

from ..db import transaction
from .extractor import Extraction, extraire

QUESTIONS = {
    "produit": "Quel produit ? (poulets de chair, œufs…)",
    "quantite": "Quelle quantité ?",
    "date": "Pour quelle date ? (ex. samedi, 15/11)",
    "localite": "Dans quelle ville ou commune ?",
}

LIBELLES = {"poulet_chair": "poulets de chair", "oeufs": "œufs", "pondeuse": "pondeuses"}


def _charger(conn, phone: str) -> dict:
    row = conn.execute("SELECT state_json FROM sessions WHERE phone = ?", (phone,)).fetchone()
    return json.loads(row["state_json"]) if row else {}


def _sauver(conn, phone: str, etat: dict) -> None:
    conn.execute(
        "INSERT INTO sessions(phone, state_json) VALUES (?, ?) "
        "ON CONFLICT(phone) DO UPDATE SET state_json = excluded.state_json",
        (phone, json.dumps(etat)),
    )


def _resume(role: str, c: dict) -> str:
    verbe = "Besoin" if role == "acheteur" else "Disponibilité"
    prix = f", {c['prix_fcfa']} FCFA" if c.get("prix_fcfa") else ""
    return (
        f"{verbe} : {c['quantite']} {LIBELLES.get(c['produit'], c['produit'])}, "
        f"{c['date']}, {c['localite'].capitalize()}{prix}."
    )


def traiter_message(conn: sqlite3.Connection, phone: str, texte: str, aujourdhui: date | None = None) -> str:
    aujourdhui = aujourdhui or date.today()
    acteur = conn.execute("SELECT * FROM actors WHERE phone = ?", (phone,)).fetchone()
    etat = _charger(conn, phone)
    ext = extraire(texte, aujourdhui)

    # 1. Inscription : rôle et consentement avant toute collecte
    if acteur is None:
        reponse = _inscription(conn, phone, texte, etat, ext)
        _enregistrer(conn, phone, texte, reponse)
        return reponse

    role = acteur["role"]

    # 2. Réponse à une demande de confirmation
    if etat.get("attente_confirmation"):
        if ext.intention == "confirmer":
            reponse = _valider(conn, acteur, etat["brouillon"])
            _sauver(conn, phone, {})
        elif ext.intention == "annuler":
            reponse = "D'accord, j'annule. Vous pouvez m'envoyer un nouveau message."
            _sauver(conn, phone, {})
        else:
            # Correction : on fusionne les nouvelles informations et on redemande confirmation
            etat["brouillon"] = _fusion(etat["brouillon"], ext)
            etat["attente_confirmation"] = True
            _sauver(conn, phone, etat)
            reponse = _resume(role, etat["brouillon"]) + " Répondez OUI pour confirmer ou NON pour annuler."
        _enregistrer(conn, phone, texte, reponse)
        return reponse

    # 3. Collecte des champs
    brouillon = _fusion(etat.get("brouillon", {}), ext)
    if ext.intention == "annuler":
        _sauver(conn, phone, {})
        reponse = "D'accord, j'annule. Vous pouvez m'envoyer un nouveau message."
    elif ext.intention == "statut":
        reponse = _statut(conn, phone, role)
    elif ext.intention in ("confirmer", "annuler") and not brouillon:
        reponse = "Je n'ai rien en attente. Décrivez votre besoin ou votre disponibilité."
    else:
        manquants = [c for c in QUESTIONS if not brouillon.get(c)]
        if manquants:
            _sauver(conn, phone, {"brouillon": brouillon})
            reponse = QUESTIONS[manquants[0]] if brouillon else (
                "Bonjour ! Dites-moi ce que vous cherchez ou ce que vous avez, par exemple : "
                "« 80 poulets de chair samedi à Cocody »."
            )
        else:
            _sauver(conn, phone, {"brouillon": brouillon, "attente_confirmation": True})
            reponse = _resume(role, brouillon) + " Répondez OUI pour confirmer ou NON pour annuler."
    _enregistrer(conn, phone, texte, reponse)
    return reponse


def _fusion(ancien: dict, ext: Extraction) -> dict:
    brouillon = dict(ancien)
    for champ in ("produit", "quantite", "date", "localite", "prix_fcfa"):
        valeur = getattr(ext, champ)
        if valeur is not None:
            brouillon[champ] = valeur
    return brouillon


def _inscription(conn, phone, texte, etat, ext) -> str:
    from ..geo import normalise

    t = normalise(texte)
    etape = etat.get("inscription")
    if etape is None:
        _sauver(conn, phone, {"inscription": "role"})
        return (
            "Bienvenue sur IVOIRE ÉLEVAGE 360. Vos données (numéro, localité, annonces) servent "
            "uniquement à vous mettre en relation. Êtes-vous ÉLEVEUR ou ACHETEUR ?"
        )
    if etape == "role":
        if "eleveur" in t:
            role = "eleveur"
        elif "acheteur" in t or "restaurant" in t:
            role = "acheteur"
        else:
            return "Je n'ai pas compris. Répondez ÉLEVEUR ou ACHETEUR."
        _sauver(conn, phone, {"inscription": "consentement", "role": role})
        return "Merci. Acceptez-vous que vos informations soient partagées avec les partenaires concernés ? Répondez OUI ou NON."
    if etape == "consentement":
        if ext.intention == "confirmer":
            with transaction(conn):
                conn.execute(
                    "INSERT INTO actors(phone, role, consent) VALUES (?, ?, 1)", (phone, etat["role"])
                )
                _sauver(conn, phone, {})
            return "Compte créé. Décrivez votre besoin ou votre disponibilité, par exemple : « 80 poulets de chair samedi à Cocody »."
        _sauver(conn, phone, {})
        return "Sans votre accord, je ne peux pas enregistrer vos informations. Écrivez-moi quand vous voulez."
    _sauver(conn, phone, {})
    return "Écrivez-moi pour recommencer."


def _valider(conn, acteur, c: dict) -> str:
    with transaction(conn):
        if acteur["role"] == "acheteur":
            cur = conn.execute(
                "INSERT INTO demands(buyer_phone, produit, quantite, date_livraison, localite, prix_max_fcfa) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (acteur["phone"], c["produit"], c["quantite"], c["date"], c["localite"], c.get("prix_fcfa")),
            )
            return f"Demande n°{cur.lastrowid} enregistrée. Je vous préviendrai dès qu'un éleveur compatible répond."
        cur = conn.execute(
            "INSERT INTO offers(farmer_phone, produit, quantite, date_disponible, localite, prix_fcfa) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (acteur["phone"], c["produit"], c["quantite"], c["date"], c["localite"], c.get("prix_fcfa")),
        )
        return (
            f"Disponibilité n°{cur.lastrowid} enregistrée (déclarée, non vérifiée). "
            "Je vous préviendrai quand une demande correspond."
        )


def _statut(conn, phone, role) -> str:
    table, col = ("demands", "buyer_phone") if role == "acheteur" else ("offers", "farmer_phone")
    rows = conn.execute(f"SELECT id, statut FROM {table} WHERE {col} = ? ORDER BY id DESC LIMIT 3", (phone,)).fetchall()
    if not rows:
        return "Vous n'avez encore rien d'enregistré."
    return "Vos dernières entrées : " + ", ".join(f"n°{r['id']} ({r['statut']})" for r in rows) + "."


def _enregistrer(conn, phone, entrant, sortant) -> None:
    with transaction(conn):
        conn.execute("INSERT INTO messages(phone, direction, body) VALUES (?, 'in', ?)", (phone, entrant))
        conn.execute("INSERT INTO messages(phone, direction, body) VALUES (?, 'out', ?)", (phone, sortant))
