"""Extraction d'une demande ou d'une offre à partir d'un message libre.

L'extracteur à règles fonctionne hors ligne et sert de plan B. Si une clé API est
configurée, `extraire_llm` est utilisé en premier ; sa sortie est validée de la
même façon que celle des règles et ne remplace jamais une confirmation humaine.
"""
import json
import re
from datetime import date, timedelta

from pydantic import BaseModel, Field, ValidationError

from .. import config
from ..geo import normalise, trouver_localite

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


class Extraction(BaseModel):
    intention: str = "inconnue"  # annonce | confirmer | annuler | statut | inconnue
    produit: str | None = None
    quantite: int | None = Field(default=None, gt=0)
    date: str | None = None  # ISO AAAA-MM-JJ
    localite: str | None = None
    prix_fcfa: int | None = Field(default=None, gt=0)

    def manquants(self) -> list[str]:
        return [c for c in ("produit", "quantite", "date", "localite") if getattr(self, c) is None]


def _intention(t: str) -> str:
    mots = set(re.findall(r"[a-z']+", t))
    if mots & {"oui", "ok", "confirme", "confirmer", "d'accord", "daccord", "valide"}:
        return "confirmer"
    if mots & {"non", "annule", "annuler", "stop"}:
        return "annuler"
    if re.search(r"\b(ou en est|statut|suivi)\b", t):
        return "statut"
    return "annonce"


def _produit(t: str) -> str | None:
    if re.search(r"\b(oeufs?|plateaux?)\b", t):
        return "oeufs"
    if re.search(r"\b(poulets?|poulet de chair|poulets de chair)\b", t):
        return "poulet_chair"
    if re.search(r"\b(pondeuses?)\b", t):
        return "pondeuse"
    return None


def _quantite(t: str) -> int | None:
    t = re.sub(r"(?<=\d)[ .](?=\d{3}\b)", "", t)  # 1 000 -> 1000
    m = re.search(r"\b(\d{1,6})\s*(?:x\s*)?(?:poulets?|oeufs?|plateaux?|pondeuses?|sujets?|tetes?|unites?)\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(?:il me faut|besoin de|j'ai|jai|dispose de)\s+(\d{1,6})\b", t)
    return int(m.group(1)) if m else None


def _prix(t: str) -> int | None:
    m = re.search(r"(\d[\d ]{2,7})\s*(?:fcfa|f cfa|cfa|f)\b", t)
    return int(m.group(1).replace(" ", "")) if m else None


def _date(t: str, aujourdhui: date) -> str | None:
    m = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", t)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            return None
    m = re.search(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b", t)
    if m:
        annee = int(m[3]) if m[3] else aujourdhui.year
        annee += 2000 if annee < 100 else 0
        try:
            d = date(annee, int(m[2]), int(m[1]))
        except ValueError:
            return None
        if not m[3] and d < aujourdhui:
            d = d.replace(year=d.year + 1)
        return d.isoformat()
    if "apres-demain" in t or "apres demain" in t:
        return (aujourdhui + timedelta(days=2)).isoformat()
    if re.search(r"\bdemain\b", t):
        return (aujourdhui + timedelta(days=1)).isoformat()
    if re.search(r"\baujourd'?hui\b", t):
        return aujourdhui.isoformat()
    for i, jour in enumerate(JOURS):
        if re.search(rf"\b{jour}\b", t):
            delta = (i - aujourdhui.weekday()) % 7 or 7
            return (aujourdhui + timedelta(days=delta)).isoformat()
    m = re.search(r"\ble (\d{1,2})\b", t)
    if m:
        jour = int(m[1])
        for decalage in (0, 1):
            mois = aujourdhui.month + decalage
            annee = aujourdhui.year + (mois - 1) // 12
            mois = (mois - 1) % 12 + 1
            try:
                d = date(annee, mois, jour)
            except ValueError:
                continue
            if d >= aujourdhui:
                return d.isoformat()
    return None


def extraire_regles(texte: str, aujourdhui: date | None = None) -> Extraction:
    aujourdhui = aujourdhui or date.today()
    t = normalise(texte)
    return Extraction(
        intention=_intention(t),
        produit=_produit(t),
        quantite=_quantite(t),
        date=_date(t, aujourdhui),
        localite=trouver_localite(t),
        prix_fcfa=_prix(t),
    )


_CONSIGNE = (
    "Tu extrais des champs d'un message WhatsApp d'un éleveur ou d'un acheteur ivoirien. "
    "N'invente rien : mets null si l'information est absente. Réponds uniquement par un objet JSON "
    "avec les clés intention (annonce|confirmer|annuler|statut|inconnue), produit "
    "(poulet_chair|oeufs|pondeuse), quantite (entier), date (AAAA-MM-JJ), localite, prix_fcfa (entier). "
    "Date du jour : {jour}."
)


def extraire_llm(texte: str, aujourdhui: date) -> Extraction | None:
    """Retourne None si le LLM est indisponible ou si sa sortie est invalide."""
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        rep = client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=300,
            system=_CONSIGNE.format(jour=aujourdhui.isoformat()),
            messages=[{"role": "user", "content": texte}],
        )
        brut = "".join(b.text for b in rep.content if b.type == "text")
        brut = brut[brut.index("{"): brut.rindex("}") + 1]
        ext = Extraction.model_validate(json.loads(brut))
    except (ImportError, ValueError, ValidationError, Exception):
        return None
    if ext.localite:
        ext.localite = trouver_localite(ext.localite)
    return ext


def extraire(texte: str, aujourdhui: date | None = None) -> Extraction:
    aujourdhui = aujourdhui or date.today()
    # Les mots de confirmation courts ne justifient pas un appel LLM.
    regles = extraire_regles(texte, aujourdhui)
    if regles.intention in ("confirmer", "annuler", "statut"):
        return regles
    return extraire_llm(texte, aujourdhui) or regles
