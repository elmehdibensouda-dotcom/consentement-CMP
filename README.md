Warning: truncated output (original token count: 3744)
Total output lines: 102

# Aman — plateforme de gestion du consentement

Aman est un prototype B2B destiné aux banques et grandes entreprises marocaines. Il réunit une console d’organisation, un format de politique versionné, une bannière web et des SDK natifs en cours de préparation pour iOS / Android. La plateforme vise à aider chaque responsable de traitement à configurer et appliquer ses choix de consentement. Elle ne garantit pas la conformité et ne remplace ni l’analyse juridique ni les formalités du client.

## Démarrer la démo connectée

Pré-requis : Python 3.11+.

1. Installer l’environnement et les dépendances depuis la racine :

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install -r backend/requirements.txt
   ```

2. Démarrer l’API dans un terminal :

   ```sh
   .venv/bin/uvicorn backend.aman_api.main:app --host 127.0.0.1 --port 8001 --no-access-log
   ```

3. Créer le premier administrateur dans un autre terminal. Saisir le courriel et le mot de passe localement à l’invite :

   ```sh
   .venv/bin/python backend/create_admin.py
   ```

   Préparer le jeu de démonstration fictif après la création du compte :

   ```sh
   .venv/bin/python backend/seed_demo.py
   ```

   Le script crée une organisation, une propriété Web de développement et un brouillon de politique. Il ne crée aucun compte visiteur ni événement de consentement. Il laisse l’approbation à deux personnes activée ; invite un second compte depuis la console pour publier. Si plusieurs comptes Aman existent, précise le propriétaire avec `--owner-email adresse@example.ma`.

4. Démarrer le serveur des fichiers statiques dans un troisième terminal :

   ```sh
   python3 -m http.server 8000
   ```

5. Ouvrir [Aman](http://localhost:8000/index.html) et se connecter à la console entreprise. L’adresse historique [admin.html](http://localhost:8000/admin.html) reste disponible. Si `seed_demo.py` a été lancé, l’organisation, la propriété et le brouillon fictifs sont déjà là ; sinon, crée une organisation et une propriété Web avec son origine exacte. L’origine de chaque propriété autorise le SDK Web à appeler uniquement ses deux routes publiques, sans cookies ; `AMAN_CORS_ORIGINS` reste réservé à la console et aux appels avec cookies. L’origine associée ne prouve pas le contrôle du domaine. Pour publier une politique, le réglage à deux personnes exige un owner/admin différent de la personne qui a fait la dernière modification. Le site fictif [demo-site.html](http://localhost:8000/demo-site.html) charge la politique publiée de la propriété si on lui ajoute `?property=ID_DE_LA_PROPRIETE`.

La page [commercialisation.html](./commercialisation.html) présente Aman aux prospects banques et grands comptes en français et en arabe standard, avec une mise en page RTL et un discours aligné sur l’état réel du prototype. Faire relire le texte arabe avant toute campagne publique.

L’entrée [index.html]…2244 tokens truncated…cheurs Page View. Configure les balises de façon qu’elles ne partent pas avant l’événement et le consentement applicable. Un `false` ultérieur ne décharge pas un script déjà exécuté : la révocation doit appeler l’API d’arrêt/réinitialisation du fournisseur. Pour les balises Google, configure également les API Consent Mode de GTM ; l’événement Aman seul ne remplace pas les mises à jour de consentement natives de Google.

Le centre de préférences Web est utilisable au clavier : `Tab` reste dans le dialogue, `Échap` le ferme et le focus retourne à son point d’ouverture. L’intégrateur reste responsable de vérifier l’accessibilité du site hôte et de ses contenus.

La transmission des décisions au tableau de bord est désactivée par défaut. Après validation du traitement et de l’information visiteur par le client, l’intégrateur Web peut activer `collectDecisionEvents: true` ; les applications natives doivent appeler explicitement `AmanConsentAPIClient.recordDecision`. Seuls les choix explicitement enregistrés sont envoyés, avec un identifiant aléatoire par décision, la version de politique et les booléens par finalité ; aucun identifiant de compte ou d’appareil n’est ajouté. Le serveur utilise son heure de réception ; les événements expirés sont exclus des agrégats, supprimés au démarrage ou à la réception d’un nouvel événement, et purgés lors d’une passe périodique d’environ 60 secondes lorsque l’API tourne. Ces événements déclarés par le client SDK alimentent des compteurs, mais ne prouvent pas seuls l’identité, l’affichage ou l’action réelle d’un visiteur. Les choix natifs restent locaux tant que l’application hôte n’active pas cet appel.

Les trois clients SDK refusent une API distante en HTTP : configure une URL HTTPS en intégration réelle. HTTP reste permis uniquement pour `localhost`, `127.0.0.1` et `::1` dans les démonstrations locales.

## État et limites

Cette version est un démonstrateur pour cadrer un pilote, pas une offre exploitable en banque. L’API refuse le mode production et utilise SQLite local. Il manque notamment le déploiement et l’exploitation durcis, PostgreSQL et migrations, MFA/SSO, limitation de débit, envoi des invitations, supervision, SLA, revue de sécurité, intégrations testées sur les systèmes du client et versions signées / publiées des SDK mobiles. Le modèle de preuve visiteur reste à valider avant toute centralisation.

Les politiques doivent être renseignées et approuvées par le client. Le schéma exige une notice configurée, mais ne détermine pas la base légale, la qualification d’une finalité ou les formalités applicables. La limite de 180 jours appliquée au canal Web est une garde de produit pour les cookies dans le périmètre D-939-2025 ; la portée du texte et les règles mobiles nécessitent une validation juridique au cas par cas. Voir les sources citées dans le plan commercial.
