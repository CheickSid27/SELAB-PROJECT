import pytest

from app import orders
from app.agent.conversation import traiter_message
from app.matching import proposer


def dire(conn, phone, texte):
    return traiter_message(conn, phone, texte)


def inscrire(conn, phone, role):
    dire(conn, phone, "bonjour"); dire(conn, phone, role); dire(conn, phone, "oui")


def jeu(conn, prix=2500):
    for p, r in (("b1", "acheteur"), ("b2", "acheteur"), ("f1", "eleveur"), ("f2", "eleveur")):
        conn.execute("INSERT INTO actors(phone, role, consent) VALUES (?,?,1)", (p, r))
    for p, q in (("b1", 80), ("b2", 100)):
        conn.execute("INSERT INTO demands(buyer_phone, produit, quantite, date_livraison, localite) VALUES (?,?,?,?,?)",
                     (p, "poulet_chair", q, "2030-01-10", "cocody"))
    for p, q, loc in (("f1", 120, "dabou"), ("f2", 100, "bouake")):
        conn.execute("INSERT INTO offers(farmer_phone, produit, quantite, date_disponible, localite, prix_fcfa) VALUES (?,?,?,?,?,?)",
                     (p, "poulet_chair", q, "2030-01-05", loc, prix))
    conn.commit()
    return orders.proposer_commande(conn, "poulet_chair", "cocody", "2030-01-10")


def test_proposition_notifie_tout_le_monde(conn):
    c = jeu(conn)
    assert c["quantite"] == 180 and c["statut"] == "en_attente"
    assert {l["farmer_phone"]: l["quantite"] for l in c["eleveurs"]} == {"f1": 120, "f2": 60}
    assert {b["buyer_phone"]: b["quantite"] for b in c["acheteurs"]} == {"b1": 80, "b2": 100}
    for p in ("b1", "b2", "f1", "f2"):
        assert len(orders.recuperer_notifications(conn, p)) == 1
    assert orders.recuperer_notifications(conn, "f1") == []  # déjà livrées
    assert c["prix_rendu_livre_fcfa"] > 2500


def test_prix_non_declare_donne_pas_de_prix(conn):
    c = jeu(conn, prix=None)
    assert c["prix_rendu_livre_fcfa"] is None


def test_confirmation_par_toutes_les_parties(conn):
    c = jeu(conn)
    for p in ("b1", "b2", "f1"):
        assert "enregistré" in orders.repondre(conn, p, "oui", True)
    assert orders.detail(conn, c["id"])["statut"] == "en_attente"
    assert "confirmée" in orders.repondre(conn, "f2", f"oui {c['id']}", True)
    assert orders.detail(conn, c["id"])["statut"] == "confirmee"
    assert conn.execute("SELECT DISTINCT statut FROM demands").fetchall()[0][0] == "engagee"
    assert orders.repondre(conn, "f2", "oui", True) is None  # plus rien en attente


def test_un_refus_annule_et_libere(conn):
    c = jeu(conn)
    orders.repondre(conn, "b1", "oui", True)
    assert "refusée" in orders.repondre(conn, "f2", "non", False)
    assert orders.detail(conn, c["id"])["statut"] == "annulee"
    statuts = {r["farmer_phone"]: r["statut"] for r in conn.execute(
        "SELECT farmer_phone, statut FROM offers")}
    assert statuts == {"f1": "ouverte", "f2": "refusee"}
    assert {r[0] for r in conn.execute("SELECT statut FROM demands")} == {"ouverte"}
    assert any("annulée" in m for m in orders.recuperer_notifications(conn, "b2"))
    # Les demandes libérées peuvent recevoir une nouvelle proposition
    assert proposer(conn, "poulet_chair", "cocody", "2030-01-10")["propositions"]


def test_mauvais_numero(conn):
    jeu(conn)
    assert "Je ne trouve pas" in orders.repondre(conn, "f1", "oui 99", True)


def test_oui_via_la_conversation_ne_vole_pas_un_brouillon(conn):
    inscrire(conn, "+1", "acheteur")
    inscrire(conn, "+2", "eleveur")
    dire(conn, "+1", "80 poulets de chair le 2030-01-10 à Cocody"); dire(conn, "+1", "oui")
    dire(conn, "+2", "j'ai 100 poulets de chair le 2030-01-05 à Dabou 2500f"); dire(conn, "+2", "oui")
    c = orders.proposer_commande(conn, "poulet_chair", "cocody", "2030-01-10")
    assert "enregistré" in dire(conn, "+1", f"oui {c['id']}")
    assert "confirmée" in dire(conn, "+2", "oui")
    assert orders.detail(conn, c["id"])["statut"] == "confirmee"


def confirmer(conn, c):
    for p in ("b1", "b2", "f1", "f2"):
        orders.repondre(conn, p, "oui", True)


def test_transporteur_etapes_dans_l_ordre(conn):
    c = jeu(conn)
    conn.execute("INSERT INTO actors(phone, role, consent) VALUES ('t1','transporteur',1)"); conn.commit()
    with pytest.raises(ValueError):
        orders.assigner_transporteur(conn, c["id"], "t1")  # pas encore confirmée
    confirmer(conn, c)
    with pytest.raises(ValueError):
        orders.assigner_transporteur(conn, c["id"], "f1")  # pas un transporteur
    orders.assigner_transporteur(conn, c["id"], "t1")
    with pytest.raises(ValueError):
        orders.enregistrer_etape(conn, c["id"], "livre", "t1")  # saute des étapes
    with pytest.raises(ValueError):
        orders.enregistrer_etape(conn, c["id"], "collecte", "f1")  # pas le bon transporteur
    for e in ("collecte", "en_route", "livre"):
        orders.enregistrer_etape(conn, c["id"], e, "t1")
    assert orders.detail(conn, c["id"])["statut"] == "livree"
    s = orders.statistiques(conn)
    assert s["taux_livraison"] == 1.0 and s["volume_local_livre"] == 180


def test_transporteur_via_conversation(conn):
    c = jeu(conn)
    inscrire(conn, "+T", "transporteur")
    confirmer(conn, c)
    orders.assigner_transporteur(conn, c["id"], "+T")
    assert "Impossible" in dire(conn, "+T", "livré")
    assert "collectée" in dire(conn, "+T", "j'ai collecté")
    assert "en route" in dire(conn, "+T", "je suis en route")
    assert "livrée" in dire(conn, "+T", "livré")
    assert "pas de mission" in dire(conn, "+T", "livré")


def test_lot_public_sans_contact(conn):
    c = jeu(conn)
    assert orders.lot_public(conn, c["id"]) is None  # pas confirmé
    confirmer(conn, c)
    lot = orders.lot_public(conn, c["id"])
    assert lot["code"] == "LOT-0001" and "pas une certification" in lot["avertissement"]
    assert "f1" not in str(lot) and "b1" not in str(lot)


def test_stats_vides(conn):
    s = orders.statistiques(conn)
    assert s["taux_livraison"] is None and s["volume_local_livre"] == 0
