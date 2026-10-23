# Brancher WhatsApp (Business Cloud API)

Le code du pont est dans `backend/app/whatsapp.py` et les routes `/whatsapp/webhook` dans `backend/app/main.py`.
**Il n'a pas été essayé avec l'API réelle de Meta** : les tests simulent des charges utiles de forme documentée.
Prévoyez du temps pour le premier essai.

## Mise en place
1. Créer une application sur Meta for Developers, y ajouter le produit **WhatsApp**.
2. Utiliser le numéro de test fourni par Meta et y enregistrer vos numéros de test (obligatoire tant que l'application n'est pas validée).
3. Récupérer : jeton d'accès (idéalement permanent, via un utilisateur système), identifiant du numéro de téléphone, secret de l'application.
4. Choisir un jeton de vérification de votre choix.
5. Lancer le serveur avec les variables d'environnement :
   ```
   WHATSAPP_TOKEN=...  WHATSAPP_PHONE_ID=...  WHATSAPP_VERIFY_TOKEN=...  WHATSAPP_APP_SECRET=...
   ```
6. Exposer le serveur en HTTPS (hébergement ou tunnel) et déclarer dans Meta l'URL de rappel `https://votre-domaine/whatsapp/webhook` avec le jeton de vérification, puis s'abonner au champ **messages**.

Sans ces quatre variables, le pont est inactif et seul le simulateur fonctionne.

## Ce que le pont fait
- Vérifie la signature `X-Hub-Signature-256` de chaque requête ; refuse sinon.
- Traite chaque message une seule fois (Meta peut renvoyer).
- Répond aux textes via l'agent ; demande un message écrit pour les vocaux, photos et documents.
- Envoie les notifications (propositions, confirmations, étapes de livraison) aux contacts qui ont écrit au moins une fois.

## Limites à connaître
- **Fenêtre de 24 h** : Meta n'accepte les messages libres que dans les 24 h suivant le dernier message de la personne. Au-delà, il faut un **modèle de message approuvé**, non géré ici. Les notifications refusées sont réessayées 5 fois puis abandonnées.
- **Vocaux** : non transcrits.
- **Coût et consentement** : l'inscription demande déjà un consentement ; vérifiez les tarifs par conversation de Meta avant un pilote.
- **Production** : la base SQLite partagée entre fils d'exécution convient à une démo, pas à une charge réelle.
