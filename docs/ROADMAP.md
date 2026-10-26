# Roadmap — IVOIRE ÉLEVAGE 360

Les dates du hackathon ne sont pas encore connues : les phases sont donc exprimées par rapport à celui-ci (J-x). À ajuster dès que le calendrier SELAB 2026 est confirmé.

## Phase 0 — Candidature (maintenant)
- [ ] Remplir le formulaire d'inscription SELAB 2026.
- [ ] Constituer l'équipe (2 à 5 personnes) et répartir les rôles : agent/IA, backend, tableau de bord/UX, pitch/terrain.
- [ ] Valider le pitch : « la demande guide la production, via WhatsApp ».

## Phase 1 — Préparation (avant le hackathon)
**Terrain**
- [ ] 3 à 5 appels d'éleveurs et 2 à 3 de restaurateurs : mode de commande actuel, usage de WhatsApp et des vocaux.
- [ ] Noter une citation et un chiffre pour le pitch.
- [ ] Analyser AKOGOUA et e-fermier : demandes agrégées ? canal WhatsApp ?

**Technique**
- [ ] Demander l'accès WhatsApp Business (plan B : simulateur de chat).
- [ ] Créer le squelette du dépôt : backend FastAPI, base, structure du simulateur.
- [ ] Préparer le jeu de données de démonstration, étiqueté « simulé ».
- [ ] Tester l'extraction par LLM sur 20 à 30 messages réalistes (texte, fautes, abréviations).

**Pitch**
- [ ] Premier jet du pitch de 3 minutes et du scénario de démo.

## Phase 2 — Hackathon (3 jours)
| Jour | Objectifs | Livrable |
|---|---|---|
| 1 | Modèle de données, simulateur de chat, agent d'extraction (demande acheteur, capacité éleveur), clarifications | Un message libre devient une demande structurée |
| 2 | Agrégation des demandes, moteur de correspondance explicable, confirmation des deux parties, prix rendu livré | Une commande confirmée de bout en bout |
| 3 | Transporteur, QR code de lot, tableau de bord, indicateur de souveraineté, répétition | Démo de 3 minutes et pitch |

**Règle de coupe :** si le jour 2 prend du retard, on supprime le QR code et le transporteur, jamais l'agent ni la correspondance.

## Phase 3 — Après le hackathon (si retenu ou soutenu)
**Mois 1 — Validation**
- Entretiens approfondis (15 à 25) avec éleveurs, acheteurs, transporteurs.
- Relevés de prix datés auprès de fournisseurs et de marchés.
- Échanges avec MIRAH, interprofessions et organisations d'éleveurs.

**Mois 2–3 — Pilote limité**
- Une filière (volaille), une zone, transactions volontaires.
- Vrai canal WhatsApp avec consentement et modèles de messages approuvés.
- Suivi manuel des opérations et procédure de réclamation.

**Mois 4–6 — Mesure et décision**
- Indicateurs : commandes servies, livraison à temps, écart prévu/réel, coût logistique, réclamations, rétention.
- Test du modèle économique (commission, services B2B).
- Décision d'élargir uniquement si fiabilité, réutilisation et économie unitaire sont démontrées.

## Phase 4 — Extension (feuille de route, non engagée)
- Achats groupés d'intrants.
- Logistique mutualisée.
- Prévision de demande, quand les données le permettent.
- Passeport de lot plus complet, avec validation par des partenaires habilités.
- Notes vocales en langues locales.
- Autres filières (œufs, bovins, porcins).
- Services financiers et assurances, uniquement via des partenaires agréés.

## Jalons de décision
| Jalon | Question | Si non |
|---|---|---|
| Fin phase 1 | Les utilisateurs veulent-ils commander par WhatsApp ? | Revoir le canal (SMS, appel, app légère) |
| Fin phase 1 | Un concurrent fait-il déjà la demande agrégée ? | Recentrer sur l'agent et la souveraineté |
| Fin phase 3 | Des transactions réelles ont-elles eu lieu sans contournement ? | Revoir la valeur ajoutée après la mise en relation |
| Fin phase 3 | Le coût par transaction est-il inférieur à la valeur créée ? | Revoir le modèle économique |
