"""Moteur de correspondance à règles, explicable et déterministe."""
import sqlite3
from datetime import date

from .geo import distance_km

POIDS_VERIF = {"declare": 0, "verifie": 1, "certifie": 2}
DISTANCE_MAX_KM = 400


def agreger_demandes(conn: sqlite3.Connection, produit: str, localite: str, date_livraison: str) -> dict:
    """Regroupe les demandes ouvertes compatibles (même produit, même localité, même date)."""
    rows = conn.execute(
        "SELECT id, quantite FROM demands WHERE statut='ouverte' AND produit=? AND localite=? AND date_livraison=?",
        (produit, localite, date_livraison),
    ).fetchall()
    return {
        "produit": produit,
        "localite": localite,
        "date": date_livraison,
        "demandes": [r["id"] for r in rows],
        "quantite_totale": sum(r["quantite"] for r in rows),
    }


def proposer(conn: sqlite3.Connection, produit: str, localite: str, date_livraison: str) -> dict:
    """Propose une répartition de la demande agrégée entre les offres compatibles."""
    groupe = agreger_demandes(conn, produit, localite, date_livraison)
    besoin = groupe["quantite_totale"]
    offres = conn.execute(
        "SELECT o.*, a.verification FROM offers o JOIN actors a ON a.phone = o.farmer_phone "
        "WHERE o.statut='ouverte' AND o.produit=? AND o.date_disponible<=?",
        (produit, date_livraison),
    ).fetchall()

    candidats = []
    for o in offres:
        dist = distance_km(o["localite"], localite)
        if dist is None or dist > DISTANCE_MAX_KM:
            continue
        candidats.append({"offre": o, "distance_km": dist, "verif": POIDS_VERIF[o["verification"]]})

    # Plus de vérification d'abord, puis plus proche, puis plus gros volume.
    candidats.sort(key=lambda c: (-c["verif"], c["distance_km"], -c["offre"]["quantite"]))

    restant, propositions = besoin, []
    for c in candidats:
        if restant <= 0:
            break
        o = c["offre"]
        qte = min(restant, o["quantite"])
        restant -= qte
        propositions.append({
            "offre_id": o["id"],
            "eleveur": o["farmer_phone"],
            "quantite": qte,
            "distance_km": c["distance_km"],
            "verification": o["verification"],
            "prix_fcfa": o["prix_fcfa"],
            "explication": (
                f"{qte} sur {o['quantite']} disponibles ; {c['distance_km']} km de {localite.capitalize()} ; "
                f"statut {o['verification']} ; disponible le {o['date_disponible']}."
            ),
        })
    return {
        **groupe,
        "propositions": propositions,
        "quantite_couverte": besoin - restant,
        "manque": max(restant, 0),
    }
