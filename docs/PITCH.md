# Pitch et script de démo — IVOIRE ÉLEVAGE 360

## Pitch de 3 minutes

**0:00 — Accroche (20 s)**
« En Côte d'Ivoire, la couverture nationale des besoins en viandes et abats tourne autour de 48–49 %, selon le portail d'information économique (2019–2024, indicateur global). Le reste est importé. Pourtant, un restaurateur d'Abidjan qui cherche 80 poulets pour samedi passe des appels, et un éleveur de Bouaké qui a 100 poulets prêts ne sait pas à qui les proposer. »

*[À remplacer par votre histoire réelle, après vos appels terrain : « Awa, restauratrice à Cocody… ». Une citation vraie vaut plus que ce paragraphe.]*

**0:20 — Idée (30 s)**
« Aujourd'hui, l'éleveur produit, puis cherche preneur. Nous inversons : la demande groupée des restaurants et hôtels guide la production locale. Et tout passe par WhatsApp : pas d'application à installer, pas de formulaire. »

**0:50 — Démo en direct (90 s)** — voir le script ci-dessous.

**2:20 — Ce qui nous différencie (30 s)**
« D'autres plateformes mettent en relation. Nous agrégeons la demande avant la production, nous expliquons chaque répartition, et nous distinguons ce qui est déclaré, vérifié ou certifié. Le prix affiché est un prix rendu livré avec ses composantes, jamais un prix inventé. »

**2:50 — Clôture (10 s)**
« IVOIRE ÉLEVAGE 360 : nous ne voulons pas seulement vendre des produits d'élevage en ligne, nous voulons mieux organiser le chemin qui les mène de la ferme au marché. »

## Script de démo (90 s) — page `/demo`

Avant de monter sur scène : cliquer **1. Préparer la démo**. Les acheteurs et éleveurs simulés existent déjà ; vous jouez l'acheteur (téléphone 1), l'éleveur (téléphone 2) et le transporteur (téléphone 3).

| # | Action | Ce que le jury voit |
|---|---|---|
| 1 | Téléphone acheteur : « 80 poulets de chair samedi à Cocody » → « oui » | L'agent comprend un message libre et demande confirmation avant d'enregistrer |
| 2 | Téléphone éleveur : « j'ai cent poulets de chair prêts demain à Dabou 2500f » → « oui » | Nombre en lettres, prix, lieu compris |
| 3 | Bouton **2. Proposer la commande** | La demande des trois acheteurs est regroupée ; chacun reçoit sa part, avec le prix rendu livré détaillé |
| 4 | Bouton **3. Acteurs simulés : OUI**, puis « oui » sur les téléphones acheteur et éleveur | Commande confirmée seulement quand toutes les parties ont dit oui |
| 5 | Bouton **4. Assigner le transporteur**, puis « collecté », « en route », « livré » | Chaque partie est notifiée à chaque étape |
| 6 | Montrer le QR code de la commande, ouvrir la fiche du lot | Provenance déclarée, niveaux de vérification, historique, avertissement « pas une certification » |
| 7 | Tableau de bord | Unités locales livrées, taux de livraison, prix rendu livré estimé |

**Si WhatsApp réel n'est pas disponible :** la démo marche telle quelle avec le simulateur. Dites-le franchement : « c'est le simulateur du canal WhatsApp, l'API se branche par un webhook déjà écrit. »

## Questions probables du jury

| Question | Réponse honnête |
|---|---|
| « Qu'est-ce qui vous différencie d'AKOGOUA ou d'AgriStore ? » | *À préparer après avoir ouvert leurs sites* (voir `VERIFICATION_SOURCES.md`). Ne pas répondre de mémoire. |
| « D'où viennent les prix ? » | Les prix d'offre sont déclarés par les éleveurs. Le transport et les pertes sont des hypothèses paramétrables, à remplacer par des devis réels. Aucun prix officiel n'est affiché sans source. |
| « Et si un éleveur ment sur sa disponibilité ? » | Statut « déclaré » par défaut ; « vérifié » seulement après contrôle par un partenaire ; l'historique des commandes servies s'ajoute avec le temps. Ce n'est pas encore automatisé. |
| « L'IA, c'est quoi exactement ? » | Un agent qui comprend les messages libres et les transforme en données structurées. La répartition est un moteur de règles explicable, et rien n'est confirmé sans accord humain. |
| « Ça marche sans smartphone ? » | Aujourd'hui non : il faut WhatsApp. Le SMS/USSD est une piste, pas faite. |
| « Et les langues locales ? » | Français uniquement. Les vocaux ne sont pas encore pris en charge. |
| « Avez-vous des utilisateurs ? » | Non, les données sont simulées. Un pilote est prévu (voir `ROADMAP.md`). Ne pas prétendre le contraire. |

## À ne pas dire
- Que des partenaires sont engagés, si ce n'est pas écrit et signé.
- Que la souveraineté alimentaire est « mesurée » : l'indicateur compte des unités dans un scénario simulé.
- Que la traçabilité est une certification sanitaire.
