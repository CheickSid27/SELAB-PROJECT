import html
import io
from datetime import date, timedelta
from pathlib import Path

import segno
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
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


@app.post("/orders/{order_id}/assign")
def assign_carrier(order_id: int, phone: str):
    try:
        return orders.assigner_transporteur(conn, order_id, phone)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.post("/orders/{order_id}/events")
def add_event(order_id: int, etape: str, phone: str):
    if etape not in orders.ETAPES:
        raise HTTPException(422, "étape invalide")
    try:
        return {"message": orders.enregistrer_etape(conn, order_id, etape, phone)}
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/stats")
def stats():
    return orders.statistiques(conn)


@app.get("/lots/{code}/qr.svg")
def lot_qr(code: str, request: Request):
    oid = _code_vers_id(code)
    if orders.lot_public(conn, oid) is None:
        raise HTTPException(404, "lot inconnu")
    buf = io.BytesIO()
    segno.make(f"{request.base_url}lots/{code}").save(buf, kind="svg", scale=5, border=1)
    return Response(buf.getvalue(), media_type="image/svg+xml")


@app.get("/lots/{code}", response_class=HTMLResponse)
def lot_page(code: str):
    lot = orders.lot_public(conn, _code_vers_id(code))
    if lot is None:
        raise HTTPException(404, "lot inconnu")
    e = html.escape
    sources = "".join(
        f"<li>{s['quantite']} unités — élevage près de {e(s['localite'].capitalize())} "
        f"(statut : <b>{e(s['verification'])}</b>)</li>" for s in lot["provenance_declaree"])
    events = "".join(f"<li>{e(ev['created_at'])} — {e(ev['etape'])}</li>" for ev in lot["evenements"])
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(lot['code'])}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:560px;margin:0 auto;padding:16px;color:#1d2b24}}
h1{{color:#1b5e3b}} .note{{background:#fff3cd;padding:10px;border-radius:6px;font-size:14px}}</style></head><body>
<h1>{e(lot['code'])}</h1>
<p><b>{lot['quantite']}</b> {e(lot['produit'].replace('_', ' '))} — livraison {e(lot['livraison']['date'])}
à {e(lot['livraison']['localite'].capitalize())} (état : {e(lot['statut'])})</p>
<h3>Provenance déclarée</h3><ul>{sources}</ul>
<h3>Historique</h3><ul>{events}</ul>
<p class="note">{e(lot['avertissement'])} Données de démonstration simulées.</p></body></html>"""


def _code_vers_id(code: str) -> int:
    if not code.startswith("LOT-") or not code[4:].isdigit():
        raise HTTPException(404, "lot inconnu")
    return int(code[4:])


# --- Démo : acteurs et données simulés, clairement étiquetés ---------------------------------

DEMO = {
    "acheteurs": [("+2250700000001", "Maquis Chez Awa (démo)"), ("+2250700000002", "Hôtel Les Palmiers (démo)"),
                  ("+2250700000003", "Restaurant Le Baobab (démo)")],
    "eleveurs": [("+2250700000011", "Ferme Koffi (démo)"), ("+2250700000012", "Élevage Traoré (démo)"),
                 ("+2250700000013", "Ferme Yao (démo)")],
    "transporteurs": [("+2250700000021", "Transports Diallo (démo)")],
}


def _samedi_prochain() -> date:
    auj = date.today()
    return auj + timedelta(days=(5 - auj.weekday()) % 7 or 7)


@app.post("/demo/reset")
def demo_reset():
    with transaction(conn):
        for t in ("order_events", "order_lines", "order_buyers", "orders", "demands", "offers",
                  "outbox", "messages", "sessions", "actors"):
            conn.execute(f"DELETE FROM {t}")
    return {"ok": True}


@app.post("/demo/seed")
def demo_seed():
    """Inscrit les acteurs simulés. Les panneaux 1, 11 et 21 restent vides : on les joue en direct."""
    demo_reset()
    samedi = _samedi_prochain().isoformat()
    veille = (_samedi_prochain() - timedelta(days=2)).isoformat()
    with transaction(conn):
        for role, cle in (("acheteur", "acheteurs"), ("eleveur", "eleveurs"), ("transporteur", "transporteurs")):
            for phone, nom in DEMO[cle]:
                conn.execute("INSERT INTO actors(phone, role, name, consent) VALUES (?,?,?,1)", (phone, role, nom))
        conn.execute("UPDATE actors SET verification='verifie' WHERE phone='+2250700000012'")
        # Acheteurs simulés en arrière-plan (les numéros ...01 et ...11 sont joués par l'utilisateur)
        for phone, q in (("+2250700000002", 100), ("+2250700000003", 60)):
            conn.execute("INSERT INTO demands(buyer_phone, produit, quantite, date_livraison, localite, simule) "
                         "VALUES (?, 'poulet_chair', ?, ?, 'cocody', 1)", (phone, q, samedi))
        conn.execute("INSERT INTO offers(farmer_phone, produit, quantite, date_disponible, localite, prix_fcfa, simule) "
                     "VALUES ('+2250700000012', 'poulet_chair', 120, ?, 'bouake', 2400, 1)", (veille,))
        conn.execute("INSERT INTO offers(farmer_phone, produit, quantite, date_disponible, localite, prix_fcfa, simule) "
                     "VALUES ('+2250700000013', 'poulet_chair', 80, ?, 'dabou', 2600, 1)", (veille,))
    return {"livraison": samedi, "joues_par_vous": ["+2250700000001", "+2250700000011", "+2250700000021"]}


@app.post("/demo/propose")
def demo_propose():
    cmd = orders.proposer_commande(conn, "poulet_chair", "cocody", _samedi_prochain().isoformat())
    if cmd is None:
        raise HTTPException(404, "aucune offre compatible : publiez d'abord une demande et une offre")
    return cmd


@app.post("/demo/auto-accord")
def demo_auto_accord():
    """Les acteurs simulés (hors panneaux 1, 11, 21) répondent OUI aux propositions en attente."""
    joues = {"+2250700000001", "+2250700000011", "+2250700000021"}
    reponses = {}
    for phone, _ in DEMO["acheteurs"] + DEMO["eleveurs"]:
        if phone not in joues:
            r = orders.repondre(conn, phone, "oui", True)
            if r:
                reponses[phone] = r
    return reponses


@app.get("/demo", include_in_schema=False)
def demo_page():
    return FileResponse(STATIC / "demo.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC / "demo.html")
