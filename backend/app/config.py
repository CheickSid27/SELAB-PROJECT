import os

DB_PATH = os.environ.get("IE360_DB", "ie360.db")
LLM_MODEL = os.environ.get("IE360_LLM_MODEL", "claude-sonnet-5-5")
# Sans clé, l'agent utilise uniquement l'extracteur à règles.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Hypothèses de calcul du prix rendu livré : à remplacer par des devis réels (transporteurs, pertes observées).
TRANSPORT_FCFA_PAR_KM = int(os.environ.get("IE360_TRANSPORT_FCFA_PAR_KM", "600"))
PERTE_ESTIMEE_PCT = float(os.environ.get("IE360_PERTE_PCT", "3"))

# WhatsApp Business Cloud API (Meta). Sans ces variables, seul le simulateur de chat est actif.
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
WHATSAPP_PHONE_ID = os.environ.get("WHATSAPP_PHONE_ID")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET")
WHATSAPP_API_VERSION = os.environ.get("WHATSAPP_API_VERSION", "v21.0")
