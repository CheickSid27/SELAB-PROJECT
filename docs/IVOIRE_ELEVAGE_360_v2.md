# IVOIRE ÉLEVAGE 360 — Version 2 (ajustée)

> Version de travail du 23/10/2026, qui remplace l'angle « plateforme complète » du dossier v1 par un angle plus net : **la demande guide la production, via un agent IA sur WhatsApp.**

## 1. Pitch en une phrase

> Aujourd'hui, les éleveurs produisent puis cherchent preneur. Nous inversons : la demande groupée des restaurants et hôtels guide la production locale, et tout passe par WhatsApp, sans application à installer.

## 2. Ce qui change par rapport à la v1

| v1 | v2 |
|---|---|
| 11 modules (A à K) | 1 parcours central, 4 briques |
| PWA comme point d'entrée | **WhatsApp comme point d'entrée** (la PWA devient un tableau de bord) |
| « IA » = moteur de règles + prévisions futures | **Agent IA conversationnel** qui comprend les messages libres et les transforme en données structurées |
| Fil social, gestion de ferme, achats groupés d'intrants, finance | Mis en « vision / feuille de route », hors prototype |
| Argument : toute la filière connectée | Argument : **inverser la logique** (demande → production) + souveraineté alimentaire mesurable |

## 3. L'innovation défendable

1. **Production tirée par la demande.** La demande des acheteurs professionnels est agrégée *avant* que l'éleveur lance son cycle.
2. **Zéro friction côté éleveur.** Un message texte ou vocal WhatsApp suffit : pas d'application, pas de formulaire. L'agent IA structure l'information.
3. **Confiance graduée.** Chaque donnée est étiquetée *déclarée / vérifiée / certifiée*, avec source et date.
4. **Prix rendu livré transparent** (produit + transport + pertes estimées), pour comparer des offres réellement équivalentes.
5. **Indicateur de souveraineté.** Chaque commande affiche le volume de produit local mobilisé face aux importations (méthode et hypothèses affichées).

## 4. Le rôle de l'agent IA (et ses limites)

**Ce que l'agent fait**
- Comprend un message libre (« j'ai 300 poulets prêts vers le 15, Bouaké ») et en extrait : espèce, quantité, date, lieu, prix demandé.
- Pose des questions de clarification quand il manque une information (unité, date, localisation).
- Côté acheteur : transforme « il me faut 80 poulets pour samedi à Cocody » en demande structurée.
- Notifie les éleveurs compatibles et collecte leur réponse (oui / non / contre-proposition).
- Répond aux questions de suivi (« où en est ma commande ? »).
- Accepte les notes vocales (transcription), en français d'abord.

**Ce que l'agent ne fait pas**
- Il ne confirme jamais une commande, un prix ni un engagement à la place d'une personne : toute confirmation est explicite, par l'éleveur et par l'acheteur.
- Il ne donne pas de diagnostic vétérinaire.
- Il n'invente ni prix ni disponibilité : si une donnée manque, il le dit.
- Le classement des producteurs reste un **moteur de règles déterministe et explicable** (volume, date, distance, statut de vérification). Le LLM comprend et reformule, il ne décide pas.

## 5. Parcours de démonstration (3 minutes)

1. Un restaurateur écrit sur WhatsApp : « 80 poulets de chair samedi, Cocody ».
2. L'agent structure la demande et la consolide avec deux autres demandes : **240 poulets au total**.
3. Trois éleveurs reçoivent un message ; deux répondent (un par vocal). L'agent extrait leurs capacités.
4. Le moteur propose une répartition et explique pourquoi (volume, date, distance, statut).
5. Les deux parties confirment sur WhatsApp. Un transporteur est assigné.
6. Un lot reçoit un QR code avec l'historique autorisé.
7. Le tableau de bord montre : taux de livraison, délai, prix rendu livré, et **volume de poulet local mobilisé**.

Toutes les données de la démo sont **clairement étiquetées comme simulées**.

## 6. Architecture du prototype

| Couche | Choix | Remarque |
|---|---|---|
| Canal | WhatsApp Business Cloud API, ou **simulateur de chat web** pour la démo | L'accès à l'API demande un compte Business ; prévoir le simulateur dès le jour 1 |
| Agent | LLM avec appel d'outils (sortie JSON structurée, validée côté serveur) | Extraction, clarification, reformulation |
| Voix | Transcription de notes vocales | Français d'abord ; langues locales hors périmètre du prototype |
| Backend | FastAPI | Webhooks WhatsApp, API demandes/offres/lots |
| Moteur | Règles explicables en Python | Pas de modèle prédictif sans données |
| Base | PostgreSQL (SQLite pour le prototype) | |
| Tableau de bord | Page web légère | Commandes, délais, prix rendu livré, indicateur de souveraineté |
| Traçabilité | Identifiant de lot + QR code | Déclaratif, jamais présenté comme une certification |

## 7. Plan 3 jours

**Jour 1 — Socle**
- Modèle de données : acteur, demande, offre, lot, commande.
- Simulateur de chat + webhook WhatsApp (si l'accès est disponible).
- Agent : extraction demande acheteur et capacité éleveur, avec questions de clarification.
- Jeu de données de démonstration étiqueté « simulé ».

**Jour 2 — Coordination**
- Agrégation des demandes compatibles.
- Moteur de correspondance explicable.
- Confirmation des deux parties par message.
- Calcul du prix rendu livré (composantes datées).

**Jour 3 — Livraison et démo**
- Affectation transporteur et suivi des étapes.
- QR code de lot et fiche d'historique.
- Tableau de bord et indicateur de souveraineté.
- Répétition du pitch ; plan B si WhatsApp réel indisponible (simulateur).

## 8. Indicateur de souveraineté : méthode

Volume de produit local mobilisé par les commandes confirmées, rapporté à une référence d'importation. Les chiffres de référence viennent du portail d'information économique de Côte d'Ivoire (rubrique Élevage, mise à jour 21/10/2025) : couverture nationale des besoins en viandes et abats d'environ 48–49 % sur 2019–2024, 164 269 tonnes équivalent carcasse importées en 2024. **Ce sont des indicateurs globaux (toutes espèces) : afficher la source, la période et les hypothèses, et ne pas les présenter comme un effet mesuré de la plateforme.** Pour la démo, l'indicateur se limite au volume réellement mobilisé dans le scénario simulé.

## 9. Risques et réponses

| Risque | Réponse |
|---|---|
| Accès à l'API WhatsApp non obtenu à temps | Simulateur de chat identique côté logique ; l'API réelle devient un bonus |
| L'agent comprend mal un message | Reformulation systématique + confirmation explicite avant toute action |
| Hallucination de prix ou de disponibilité | L'agent n'écrit que des valeurs issues de la base, avec source et date |
| Coût et consentement des messages | Opt-in explicite, modèles de messages autorisés, volumes limités au pilote |
| Données personnelles | Minimisation, accès par rôle, consentement dès la première conversation |
| Concurrence (AKOGOUA, e-fermier) | À analyser avant le hackathon : vérifier s'ils proposent déjà des demandes agrégées ou un canal WhatsApp |
| Périmètre trop vaste | Une filière (volaille), une zone, un parcours |

## 10. Avant le hackathon

- [ ] Appeler 3 à 5 éleveurs et 2 à 3 restaurateurs : comment commandent-ils aujourd'hui ? Utilisent-ils WhatsApp ? Notes vocales ?
- [ ] Noter une citation et un chiffre terrain pour le pitch.
- [ ] Analyser les fonctionnalités réelles d'AKOGOUA et d'e-fermier.
- [ ] Demander l'accès WhatsApp Business (ou valider le plan B simulateur).
- [ ] Répartir les rôles : agent/IA, backend, tableau de bord, pitch.

## 11. Ce qu'il ne faut pas promettre

- Une IA de prévision entraînée sur des données nationales.
- Des prix fictifs présentés comme des cours réels.
- Des partenaires engagés sans accord écrit.
- Un paiement réel sans prestataire agréé.
- Une traçabilité déclarative présentée comme une certification sanitaire.
