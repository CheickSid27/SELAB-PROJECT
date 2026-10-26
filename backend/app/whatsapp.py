"""Pont WhatsApp Business Cloud API : vérification, réception, envoi.

Non testé contre l'API réelle de Meta : les tests utilisent des charges utiles de forme documentée
et un faux expéditeur. Un essai avec un numéro de test Meta reste à faire.
"""
import hashlib
import hmac
import sqlite3

import httpx

from . import config
from .db import transaction


def configure() -> bool:
    return all([config.WHATSAPP_TOKEN, config.WHATSAPP_PHONE_ID, config.WHATSAPP_VERIFY_TOKEN, config.WHATSAPP_APP_SECRET])


def signature_valide(corps: bytes, entete: str | None) -> bool:
    """Vérifie X-Hub-Signature-256 (HMAC-SHA256 du corps brut avec le secret de l'application)."""
    if not config.WHATSAPP_APP_SECRET or not entete or not entete.startswith("sha256="):
        return False
    attendu = hmac.new(config.WHATSAPP_APP_SECRET.encode(), corps, hashlib.sha256).hexdigest()
    return hmac.compare_digest(attendu, entete[len("sha256="):])


def extraire_messages(payload: dict) -> list[dict]:
    """Messages entrants : {id, phone (avec +), type, text}. Ignore les statuts de livraison."""
    messages = []
    for entree in payload.get("entry", []):
        for changement in entree.get("changes", []):
            for m in changement.get("value", {}).get("messages", []) or []:
                messages.append({
                    "id": m.get("id", ""),
                    "phone": "+" + str(m.get("from", "")),
                    "type": m.get("type", ""),
                    "text": (m.get("text") or {}).get("body", ""),
                })
    return messages


def envoyer_texte(phone: str, texte: str) -> None:
    url = f"https://graph.facebook.com/{config.WHATSAPP_API_VERSION}/{config.WHATSAPP_PHONE_ID}/messages"
    r = httpx.post(
        url,
        headers={"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"},
        json={"messaging_product": "whatsapp", "to": phone.lstrip("+"), "type": "text", "text": {"body": texte}},
        timeout=10,
    )
    r.raise_for_status()


def traiter_payload(conn: sqlite3.Connection, payload: dict, repondre, envoyer=None) -> int:
    """Traite chaque message une seule fois (Meta peut renvoyer). `repondre(phone, texte) -> réponse`."""
    envoyer = envoyer or envoyer_texte
    traites = 0
    for m in extraire_messages(payload):
        try:
            with transaction(conn):
                conn.execute("INSERT INTO wa_seen(message_id) VALUES (?)", (m["id"],))
                conn.execute("INSERT OR IGNORE INTO wa_contacts(phone) VALUES (?)", (m["phone"],))
        except sqlite3.IntegrityError:
            continue
        if m["type"] == "text" and m["text"].strip():
            reponse = repondre(m["phone"], m["text"])
        else:
            reponse = "Je ne comprends pas encore les vocaux, photos ni documents : écrivez-moi votre message en texte."
        envoyer(m["phone"], reponse)
        traites += 1
    return traites


MAX_TENTATIVES = 5


def vider_outbox(conn: sqlite3.Connection, envoyer=None) -> int:
    """Envoie les notifications destinées à des contacts WhatsApp.

    Un échec laisse le message en attente, jusqu'à MAX_TENTATIVES : hors de la fenêtre de 24 h après le dernier
    message de la personne, Meta n'accepte qu'un modèle approuvé (non géré ici), donc on ne réessaie pas sans fin."""
    envoyer = envoyer or envoyer_texte
    rows = conn.execute(
        "SELECT o.id, o.phone, o.body FROM outbox o JOIN wa_contacts c ON c.phone=o.phone WHERE o.delivered=0 AND o.tentatives<? ORDER BY o.id", (MAX_TENTATIVES,)
    ).fetchall()
    envoyes = 0
    for r in rows:
        try:
            envoyer(r["phone"], r["body"])
        except Exception:
            with transaction(conn):
                conn.execute("UPDATE outbox SET tentatives=tentatives+1 WHERE id=?", (r["id"],))
            continue
        with transaction(conn):
            conn.execute("UPDATE outbox SET delivered=1 WHERE id=?", (r["id"],))
        envoyes += 1
    return envoyes
