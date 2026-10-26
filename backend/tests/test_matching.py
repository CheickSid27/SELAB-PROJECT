import pytest

from app.matching import agreger_demandes, proposer
from app.pricing import ComposantesPrix


def acteur(conn, phone, role, verif="declare"):
    conn.execute("INSERT INTO actors(phone, role, verification, consent) VALUES (?,?,?,1)", (phone, role, verif))


def demande(conn, phone, qte, loc="cocody", d="2026-10-24"):
    conn.execute(
        "INSERT INTO demands(buyer_phone, produit, quantite, date_livraison, localite) VALUES (?,?,?,?,?)",
        (phone, "poulet_chair", qte, d, loc),
    )


def offre(conn, phone, qte, loc, d="2026-10-23", prix=2500):
    conn.execute(
        "INSERT INTO offers(farmer_phone, produit, quantite, date_disponible, localite, prix_fcfa) VALUES (?,?,?,?,?,?)",
        (phone, "poulet_chair", qte, d, loc, prix),
    )


def test_agregation(conn):
    for p in ("b1", "b2", "b3"):
        acteur(conn, p, "acheteur")
    demande(conn, "b1", 80); demande(conn, "b2", 100); demande(conn, "b3", 60)
    demande(conn, "b3", 999, loc="bouake")  # autre localité : exclue
    g = agreger_demandes(conn, "poulet_chair", "cocody", "2026-10-24")
    assert g["quantite_totale"] == 240 and len(g["demandes"]) == 3


def test_repartition_priorite_verification_puis_distance(conn):
    acteur(conn, "b1", "acheteur"); demande(conn, "b1", 240)
    acteur(conn, "f1", "eleveur", "declare"); offre(conn, "f1", 200, "dabou")
    acteur(conn, "f2", "eleveur", "verifie"); offre(conn, "f2", 150, "bouake")
    r = proposer(conn, "poulet_chair", "cocody", "2026-10-24")
    assert [p["eleveur"] for p in r["propositions"]] == ["f2", "f1"]
    assert r["quantite_couverte"] == 240 and r["manque"] == 0
    assert "km" in r["propositions"][0]["explication"]


def test_offre_trop_tardive_exclue(conn):
    acteur(conn, "b1", "acheteur"); demande(conn, "b1", 50)
    acteur(conn, "f1", "eleveur"); offre(conn, "f1", 100, "dabou", d="2026-10-30")
    r = proposer(conn, "poulet_chair", "cocody", "2026-10-24")
    assert r["propositions"] == [] and r["manque"] == 50


def test_prix_rendu_livre():
    c = ComposantesPrix(prix_produit_fcfa=2500, transport_total_fcfa=20000, perte_estimee_pct=5)
    assert c.prix_rendu_livre(100) == pytest.approx(2842.1, abs=0.1)
    with pytest.raises(ValueError):
        c.prix_rendu_livre(0)
