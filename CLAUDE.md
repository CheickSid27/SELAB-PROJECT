# IVOIRE ÉLEVAGE 360 — contexte pour Claude Code

Prototype pour le hackathon SELAB 2026 (Côte d'Ivoire) : **la demande groupée des acheteurs professionnels guide la production des éleveurs, via un agent sur WhatsApp.** Langue du projet : français (code, messages, docs).

## Commandes
```bash
cd backend
pip install -r requirements.txt
python -m pytest -q                  # 40 tests, doivent tous passer
uvicorn app.main:app --reload        # démo : http://localhost:8000/demo
```
Ne pas lancer `pkill -f uvicorn` ni `pgrep -f` depuis un shell qui contient ce motif : cela tue le shell. Utiliser `fuser -k <port>/tcp`.

## Architecture (`backend/app/`)
- `agent/extractor.py` : extraction d'une demande ou offre depuis un message libre. Règles hors ligne (jours, dates, mois, nombres en lettres, localités) ; LLM optionnel si `ANTHROPIC_API_KEY`, sortie validée par pydantic, repli sur les règles.
- `agent/conversation.py` : machine à états par numéro. Inscription (rôle + consentement) → collecte des champs manquants → résumé → **confirmation explicite** avant tout enregistrement.
- `matching.py` : agrégation des demandes et répartition entre offres. Moteur de règles **déterministe et explicable** (vérification, puis distance, puis volume).
- `orders.py` : commande en attente → accord de **toutes** les parties → confirmée ; un NON annule et libère. Transporteur, étapes dans l'ordre (collecte → en route → livré), fiche de lot publique, statistiques.
- `pricing.py` + `config.py` : prix rendu livré. `TRANSPORT_FCFA_PAR_KM` (600) et `PERTE_ESTIMEE_PCT` (3) sont des **hypothèses inventées**, à remplacer par de vrais devis.
- `whatsapp.py` : webhook Meta (signature, déduplication, envoi, notifications). Inactif sans les 4 variables `WHATSAPP_*`.
- `main.py` : API FastAPI, fiche de lot HTML, QR (segno), routes `/demo/*`. `static/demo.html` : démo à 3 téléphones.
- `db.py` : SQLite (schéma créé au démarrage, pas de migrations : supprimer le fichier `.db` si le schéma change).

## Règles à respecter
- **L'agent ne confirme jamais** un prix, une commande ou un engagement à la place d'une personne.
- **Aucun prix inventé** : sans prix déclaré, ne rien afficher. Les prix officiels exigent source et date.
- Confiance graduée : `declare` / `verifie` / `certifie`. La traçabilité est **déclarative**, jamais une certification sanitaire.
- Fiche de lot publique : **aucun numéro de téléphone**.
- Données de démonstration toujours étiquetées « simulé ». Ne pas présenter l'indicateur de souveraineté comme un effet mesuré.
- Ne pas promettre : IA de prévision, partenaires non signés, paiements réels.

## État (tout est testé en local ; rien n'est déployé)
Fait : agent, correspondance, commandes, accord multi-parties, transporteur, lot + QR, tableau de bord, démo, pont WhatsApp (testé uniquement avec des charges simulées).

## À faire pour « mettre sur pied » (par priorité)
1. **Déploiement** : héberger en HTTPS (le webhook Meta l'exige), variables d'environnement, base persistante.
2. **Essai WhatsApp réel** avec un numéro de test Meta ; ajuster le pont aux écarts constatés.
3. **Modèles de message WhatsApp approuvés** pour notifier hors de la fenêtre de 24 h (aujourd'hui : 5 tentatives puis abandon).
4. **Concurrence d'accès** : une connexion SQLite partagée entre fils convient à une démo ; passer à PostgreSQL ou sérialiser les accès avant toute charge réelle.
5. **Sécurité des routes** : `/demo/*`, `/admin/verification/*`, `/orders/propose` et `/orders/*/assign` sont **sans authentification**. À protéger ou à désactiver hors démo.
6. Déclenchement automatique de la proposition de commande quand une demande compatible arrive (aujourd'hui manuel).
7. Vocaux (transcription), langues locales, SMS/USSD : non faits.
8. Brancher de vrais devis de transport et mesurer les pertes.

## Docs
`docs/IVOIRE_ELEVAGE_360_v2.md` (concept), `docs/ROADMAP.md`, `docs/PITCH.md`, `docs/WHATSAPP.md`, `docs/VERIFICATION_SOURCES.md` (les sources du dossier n'ont **pas** toutes été vérifiées : accès bloqué).
