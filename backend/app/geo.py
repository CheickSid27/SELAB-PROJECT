"""Localités connues (coordonnées approximatives) pour le calcul de distance."""
import math
import unicodedata

LOCALITES = {
    "abidjan": (5.36, -4.01),
    "cocody": (5.35, -3.98),
    "yopougon": (5.34, -4.09),
    "marcory": (5.30, -3.98),
    "plateau": (5.32, -4.02),
    "abobo": (5.42, -4.02),
    "bouake": (7.69, -5.03),
    "yamoussoukro": (6.82, -5.28),
    "korhogo": (9.46, -5.63),
    "san-pedro": (4.75, -6.64),
    "daloa": (6.88, -6.45),
    "man": (7.41, -7.55),
    "anyama": (5.49, -4.05),
    "dabou": (5.33, -4.38),
}


def normalise(texte: str) -> str:
    sans_accents = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in sans_accents if unicodedata.category(c) != "Mn")
    return sans_accents.lower().replace("san pedro", "san-pedro")


def trouver_localite(texte: str) -> str | None:
    t = normalise(texte)
    for nom in sorted(LOCALITES, key=len, reverse=True):
        if nom in t:
            return nom
    return None


def distance_km(a: str, b: str) -> float | None:
    if a not in LOCALITES or b not in LOCALITES:
        return None
    lat1, lon1 = map(math.radians, LOCALITES[a])
    lat2, lon2 = map(math.radians, LOCALITES[b])
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return round(6371 * 2 * math.asin(math.sqrt(h)), 1)
