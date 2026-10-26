import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

from app import config, main, whatsapp
from app.db import connect


def payload(texte="bonjour", id_="wamid.1", type_="text", de="2250700000099"):
    msg = {"from": de, "id": id_, "type": type_}
    if type_ == "text":
        msg["text"] = {"body": texte}
    return {"entry": [{"changes": [{"value": {"messages": [msg]}}]}]}


def signer(corps: bytes, secret="s3cret"):
    return "sha256=" + hmac.new(secret.encode(), corps, hashlib.sha256).hexdigest()


@pytest.fixture
def wa(monkeypatch):
    monkeypatch.setattr(config, "WHATSAPP_APP_SECRET", "s3cret")
    monkeypatch.setattr(config, "WHATSAPP_VERIFY_TOKEN", "jeton")
    monkeypatch.setattr(main, "conn", connect(":memory:"))
    envoyes = []
    monkeypatch.setattr(whatsapp, "envoyer_texte", lambda phone, texte: envoyes.append((phone, texte)))
    return TestClient(main.app), envoyes


def test_verification_du_webhook(wa):
    c, _ = wa
    ok = c.get("/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "jeton", "hub.challenge": "1234"})
    assert ok.status_code == 200 and ok.text == "1234"
    assert c.get("/whatsapp/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "faux", "hub.challenge": "1"}).status_code == 403


def test_signature_obligatoire(wa):
    c, envoyes = wa
    corps = json.dumps(payload()).encode()
    assert c.post("/whatsapp/webhook", content=corps).status_code == 403
    assert c.post("/whatsapp/webhook", content=corps, headers={"X-Hub-Signature-256": "sha256=00"}).status_code == 403
    assert envoyes == []


def test_message_recu_recoit_une_reponse(wa):
    c, envoyes = wa
    corps = json.dumps(payload("bonjour")).encode()
    r = c.post("/whatsapp/webhook", content=corps, headers={"X-Hub-Signature-256": signer(corps)})
    assert r.status_code == 200
    assert envoyes[0][0] == "+2250700000099" and "ÉLEVEUR" in envoyes[0][1]


def test_message_renvoye_par_meta_traite_une_seule_fois(wa):
    c, envoyes = wa
    corps = json.dumps(payload("bonjour", id_="wamid.X")).encode()
    h = {"X-Hub-Signature-256": signer(corps)}
    c.post("/whatsapp/webhook", content=corps, headers=h)
    c.post("/whatsapp/webhook", content=corps, headers=h)
    assert len(envoyes) == 1


def test_vocal_recoit_un_message_clair(wa):
    c, envoyes = wa
    corps = json.dumps(payload(type_="audio", id_="wamid.A")).encode()
    c.post("/whatsapp/webhook", content=corps, headers={"X-Hub-Signature-256": signer(corps)})
    assert "vocaux" in envoyes[0][1]


def test_statuts_de_livraison_ignores():
    p = {"entry": [{"changes": [{"value": {"statuses": [{"id": "x", "status": "read"}]}}]}]}
    assert whatsapp.extraire_messages(p) == []


def test_outbox_n_envoie_qu_aux_contacts_whatsapp_et_reessaie_apres_echec():
    conn = connect(":memory:")
    conn.execute("INSERT INTO wa_contacts(phone) VALUES ('+1')")
    conn.executemany("INSERT INTO outbox(phone, body) VALUES (?, ?)", [("+1", "pour wa"), ("+2", "simulateur")])
    conn.commit()

    def panne(phone, texte):
        raise RuntimeError("réseau")
    assert whatsapp.vider_outbox(conn, panne) == 0
    assert conn.execute("SELECT COUNT(*) FROM outbox WHERE delivered=0").fetchone()[0] == 2

    envoyes = []
    assert whatsapp.vider_outbox(conn, lambda p, t: envoyes.append(p)) == 1
    assert envoyes == ["+1"]
    assert conn.execute("SELECT body FROM outbox WHERE delivered=0").fetchone()[0] == "simulateur"


def test_abandon_apres_plusieurs_echecs():
    conn = connect(":memory:")
    conn.execute("INSERT INTO wa_contacts(phone) VALUES ('+1')")
    conn.execute("INSERT INTO outbox(phone, body) VALUES ('+1', 'x')"); conn.commit()
    appels = []

    def panne(phone, texte):
        appels.append(1)
        raise RuntimeError("hors fenêtre de 24 h")
    for _ in range(10):
        whatsapp.vider_outbox(conn, panne)
    assert len(appels) == whatsapp.MAX_TENTATIVES
