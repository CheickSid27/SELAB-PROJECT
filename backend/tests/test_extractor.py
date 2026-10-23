from datetime import date

from app.agent.extractor import extraire_regles

# Mercredi 21 octobre 2026
AUJ = date(2026, 10, 21)


def test_demande_complete():
    e = extraire_regles("80 poulets de chair samedi à Cocody", AUJ)
    assert (e.produit, e.quantite, e.date, e.localite) == ("poulet_chair", 80, "2026-10-24", "cocody")
    assert e.manquants() == []


def test_offre_avec_prix_et_date_numerique():
    e = extraire_regles("J'ai 300 poulets prêts le 15/11 à Bouaké, 2500 FCFA", AUJ)
    assert (e.quantite, e.date, e.localite, e.prix_fcfa) == (300, "2026-11-15", "bouake", 2500)


def test_champs_manquants():
    e = extraire_regles("il me faut des poulets", AUJ)
    assert set(e.manquants()) == {"quantite", "date", "localite"}


def test_confirmation():
    assert extraire_regles("Oui", AUJ).intention == "confirmer"
    assert extraire_regles("non merci", AUJ).intention == "annuler"


def test_date_invalide_ignoree():
    assert extraire_regles("50 poulets le 31/02 à Man", AUJ).date is None


def test_demain_et_milliers():
    e = extraire_regles("1 000 oeufs demain à Daloa", AUJ)
    assert (e.quantite, e.date, e.produit) == (1000, "2026-10-22", "oeufs")
