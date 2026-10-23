# SELAB-PROJECT

Prototype du hackathon SELAB 2026 : la demande guide la production, via un agent IA sur WhatsApp.

- Concept : [docs/IVOIRE_ELEVAGE_360_v2.md](docs/IVOIRE_ELEVAGE_360_v2.md)
- Roadmap : [docs/ROADMAP.md](docs/ROADMAP.md)

## Lancer le prototype

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload   # simulateur de chat sur http://localhost:8000
python -m pytest                # tests
```

Sans `ANTHROPIC_API_KEY`, l'agent utilise l'extracteur à règles. Avec une clé, le LLM est essayé en premier,
et son résultat est validé avant usage. Toutes les données de démonstration sont simulées.
