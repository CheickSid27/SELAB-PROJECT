from fastapi.testclient import TestClient

from app import main
from app.db import connect


def test_chat_et_matching_bout_en_bout(monkeypatch):
    monkeypatch.setattr(main, "conn", connect(":memory:"))
    c = TestClient(main.app)

    def dire(phone, texte):
        return c.post("/chat", json={"phone": phone, "text": texte}).json()["reply"]

    for phone, role in (("+1", "acheteur"), ("+2", "eleveur")):
        dire(phone, "bonjour"); dire(phone, role); dire(phone, "oui")
    dire("+1", "80 poulets de chair le 2030-01-10 à Cocody"); dire("+1", "oui")
    dire("+2", "j'ai 100 poulets de chair le 2030-01-05 à Dabou"); dire("+2", "oui")

    r = c.get("/matching", params={"produit": "poulet_chair", "localite": "cocody", "date_livraison": "2030-01-10"}).json()
    assert r["quantite_totale"] == 80 and r["quantite_couverte"] == 80

    assert c.post("/admin/verification/+2", params={"niveau": "verifie"}).status_code == 200
    assert c.post("/admin/verification/+9", params={"niveau": "verifie"}).status_code == 404
    assert c.get("/").status_code == 200
