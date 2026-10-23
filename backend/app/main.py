from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import matching, orders
from .agent.conversation import traiter_message
from .db import connect, transaction

app = FastAPI(title="IVOIRE ÉLEVAGE 360 — prototype")
conn = connect()
STATIC = Path(__file__).parent / "static"


class MessageEntrant(BaseModel):
    phone: str
    text: str


@app.get("/", include_in_schema=False)
def chat():
    return FileResponse(STATIC / "chat.html")


@app.post("/chat")
def chat_message(msg: MessageEntrant):
    return {"reply": traiter_message(conn, msg.phone, msg.text)}


@app.get("/demands")
def demands():
    return [dict(r) for r in conn.execute("SELECT * FROM demands ORDER BY id")]


@app.get("/offers")
def offers():
    return [dict(r) for r in conn.execute("SELECT * FROM offers ORDER BY id")]


@app.get("/matching")
def matching_proposal(produit: str, localite: str, date_livraison: date):
    return matching.proposer(conn, produit, localite, date_livraison.isoformat())


@app.post("/admin/verification/{phone}")
def set_verification(phone: str, niveau: str):
    if niveau not in ("declare", "verifie", "certifie"):
        raise HTTPException(422, "niveau invalide")
    with transaction(conn):
        cur = conn.execute("UPDATE actors SET verification = ? WHERE phone = ?", (niveau, phone))
    if cur.rowcount == 0:
        raise HTTPException(404, "acteur inconnu")
    return {"phone": phone, "verification": niveau}


@app.post("/orders/propose")
def propose_order(produit: str, localite: str, date_livraison: date):
    """Crée une commande en attente et notifie éleveurs et acheteurs (file d'attente `outbox`)."""
    commande = orders.proposer_commande(conn, produit, localite, date_livraison.isoformat())
    if commande is None:
        raise HTTPException(404, "aucune offre compatible")
    return commande


@app.get("/orders")
def list_orders():
    return [orders.detail(conn, r["id"]) for r in conn.execute("SELECT id FROM orders ORDER BY id")]


@app.get("/orders/{order_id}")
def get_order(order_id: int):
    commande = orders.detail(conn, order_id)
    if commande is None:
        raise HTTPException(404, "commande inconnue")
    return commande


@app.get("/outbox")
def outbox(phone: str):
    """Notifications en attente pour ce numéro (le simulateur les interroge régulièrement)."""
    return {"messages": orders.recuperer_notifications(conn, phone)}
