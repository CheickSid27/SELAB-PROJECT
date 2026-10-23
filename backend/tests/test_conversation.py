from datetime import date

from app.agent.conversation import traiter_message

AUJ = date(2026, 10, 21)


def parler(conn, phone, texte):
    return traiter_message(conn, phone, texte, AUJ)


def inscrire(conn, phone, role):
    parler(conn, phone, "bonjour")
    parler(conn, phone, role)
    parler(conn, phone, "oui")


def test_inscription_exige_consentement(conn):
    parler(conn, "+1", "bonjour")
    parler(conn, "+1", "acheteur")
    parler(conn, "+1", "non")
    assert conn.execute("SELECT COUNT(*) FROM actors").fetchone()[0] == 0


def test_demande_avec_clarification_et_confirmation(conn):
    inscrire(conn, "+1", "acheteur")
    assert "ville" in parler(conn, "+1", "80 poulets de chair samedi").lower()
    r = parler(conn, "+1", "Cocody")
    assert "OUI" in r and "80" in r
    # Rien n'est enregistré avant confirmation
    assert conn.execute("SELECT COUNT(*) FROM demands").fetchone()[0] == 0
    parler(conn, "+1", "oui")
    d = conn.execute("SELECT * FROM demands").fetchone()
    assert (d["quantite"], d["localite"], d["date_livraison"]) == (80, "cocody", "2026-10-24")


def test_annulation(conn):
    inscrire(conn, "+1", "acheteur")
    parler(conn, "+1", "80 poulets samedi Cocody")
    parler(conn, "+1", "non")
    assert conn.execute("SELECT COUNT(*) FROM demands").fetchone()[0] == 0


def test_correction_avant_confirmation(conn):
    inscrire(conn, "+1", "acheteur")
    parler(conn, "+1", "80 poulets samedi Cocody")
    parler(conn, "+1", "plutôt 100 poulets")
    parler(conn, "+1", "oui")
    assert conn.execute("SELECT quantite FROM demands").fetchone()[0] == 100


def test_offre_eleveur_declaree(conn):
    inscrire(conn, "+2", "eleveur")
    parler(conn, "+2", "J'ai 300 poulets le 15/11 à Bouaké")
    parler(conn, "+2", "oui")
    o = conn.execute("SELECT * FROM offers").fetchone()
    assert o["quantite"] == 300
    assert conn.execute("SELECT verification FROM actors WHERE phone='+2'").fetchone()[0] == "declare"
