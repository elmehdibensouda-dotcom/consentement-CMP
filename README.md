# ALAMANE — plateforme de gestion du consentement

ALAMANE est un prototype B2B destiné aux banques et grandes entreprises marocaines. Il réunit une console multi-organisation, un format de politique versionné, une bannière Web et des SDK en cours de préparation pour iOS, Android et React Native. La plateforme vise à aider chaque responsable de traitement à configurer et appliquer ses choix de consentement. Elle ne garantit pas la conformité et ne remplace ni l’analyse juridique ni les formalités du client.

## Démarrer la démo connectée

Pré-requis : Python 3.11+.

Sur macOS, lance le parcours de démonstration complet avec une seule commande :

```sh
bash scripts/start-demo.sh
```

Le script vérifie d’abord que les ports locaux 8000 et 8001 sont libres, utilise une base SQLite distincte dans `.local/`, crée le premier compte si nécessaire en demandant l’adresse et un mot de passe saisi sans affichage, prépare l’organisation et la propriété fictives, démarre l’API et le site, attend leurs réponses de disponibilité, puis ouvre la console. Les deux serveurs restent dans le terminal jusqu’à `Ctrl+C`. Si plusieurs comptes sont présents, le script demande lequel détiendra l’organisation fictive. Aucune donnée réelle de banque ou de visiteur ne doit être saisie.

### Démarrage manuel

Pour lancer chaque composant séparément :

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

   Si tu dois rétablir l’accès à un compte local, arrête l’API et lance `.venv/bin/python backend/reset_password.py`. Cette commande réservée au développement demande un nouveau mot de passe sans affichage et révoque les sessions de ce compte ; ce n’est pas un parcours de récupération en libre-service ni une procédure de production.

   Préparer le jeu de démonstration fictif après la création du compte :

   ```sh
   .venv/bin/python backend/seed_demo.py
   ```

   Le script crée une organisation, une propriété Web de développement et un brouillon de politique. Il ne crée aucun compte visiteur ni événement de consentement. Il laisse l’approbation à deux personnes activée ; invite un second compte depuis la console pour publier. Si plusieurs comptes ALAMANE existent, précise le propriétaire avec `--owner-email adresse@example.ma`.

4. Démarrer le serveur des fichiers statiques dans un troisième terminal :

   ```sh
   python3 -m http.server 8000
   ```

5. Ouvrir [ALAMANE](http://localhost:8000/index.html) et se connecter à la console entreprise. L’adresse historique [admin.html](http://localhost:8000/admin.html) reste disponible. Si `seed_demo.py` a été lancé, l’organisation, la propriété et le brouillon fictifs sont déjà là ; sinon, crée une organisation et une propriété Web avec son origine exacte. L’origine de chaque propriété autorise le SDK Web à appeler uniquement ses deux routes publiques, sans cookies ; `AMAN_CORS_ORIGINS` reste réservé à la console et aux appels avec cookies. L’origine associée ne prouve pas le contrôle du domaine. Pour les environnements développement et recette, le réglage à deux personnes exige un owner/admin différent de la personne qui a fait la dernière modification ; il est toujours imposé pour une propriété étiquetée production. Le site fictif [demo-site.html](http://localhost:8000/demo-site.html) charge la politique publiée de la propriété si on lui ajoute `?property=ID_DE_LA_PROPRIETE`.

La page [commercialisation.html](./commercialisation.html) présente ALAMANE aux prospects banques et grands comptes en français et en arabe standard, avec une mise en page RTL et un discours aligné sur l’état réel du prototype. Sa [fiche de cadrage pilote](./FICHE_CADRAGE_PILOTE.html) peut être imprimée ou enregistrée en PDF ; faire relire les textes arabes avant toute diffusion externe.

L’entrée [index.html](http://localhost:8000/index.html) redirige vers la console connectée [admin.html](http://localhost:8000/admin.html), qui s’ouvre sur une vue d’ensemble multi-organisation avec les comptes réels de la session, puis permet de gérer les organisations, propriétés et leurs environnements (développement, recette, production), politiques, brouillons et actions administratives par organisation. La publication d’une politique sur une propriété de production exige toujours qu’une personne différente de la dernière personne ayant modifié le brouillon la publie, même si l’organisation a désactivé cette option pour ses autres environnements. L’ancienne maquette à statistiques simulées est isolée dans [maquette-dashboard.html](./maquette-dashboard.html) et ne sert pas de tableau de bord opérationnel. La console peut aussi afficher les décisions reçues dans les 30 derniers jours, leurs compteurs agrégés par finalité et la date de la dernière décision encore conservée par propriété ; elle permet d’exporter les événements retenus en CSV lorsqu’un intégrateur a activé leur transmission. Une absence d’événement n’établit pas une panne d’intégration, et ces événements ne prouvent pas l’affichage de l’interface ou l’application effective du choix. Le scanner intégré et les intégrations illustratives du tableau de bord restent des exemples ; un [outil local d’inventaire de page](http://localhost:8000/scanner-tool.html) relève les ressources visibles dans l’onglet où son code est lancé, signale les marqueurs directs observés sur les scripts, permet un classement manuel et exporte un JSON sans envoyer les résultats automatiquement. Ce signal ne prouve pas le contrôle effectif ni les règles appliquées par un gestionnaire comme GTM. Un membre peut ensuite importer explicitement le rapport sur une propriété Web dans la console ; seuls les 20 derniers rapports y sont conservés et ils restent supprimables. L’outil ne parcourt pas plusieurs pages automatiquement. La console `admin.html` est le parcours connecté du prototype. L’environnement est une étiquette de gouvernance par propriété, pas un cloisonnement technique des données ou des déploiements. L’API et son stockage sont locaux ; n’y place aucune donnée réelle de banque ou de client.

## Architecture et intégrations

- [Guide d’intégration pilote](./GUIDE_INTEGRATION_PILOTE.md) : choix du SDK, préparation de propriété, distribution actuelle par plateforme et règles communes d’intégration.

- [`backend/`](./backend/README.md) : API FastAPI locale, organisations, rôles, propriétés et politiques publiques versionnées. La console permet de définir plusieurs finalités FR/AR et d’associer des fournisseurs indicatifs à chacune ; ces noms sont affichés au visiteur et les tags Web doivent toujours être raccordés explicitement à l’identifiant de finalité.
- [`schemas/consent-policy.schema.json`](./schemas/consent-policy.schema.json) : contrat de politique commun.
- [`aman-cmp.js`](./aman-cmp.js) : bannière Web, synchronisation du choix entre onglets et blocage des scripts balisés — y compris ceux ajoutés dynamiquement — jusqu’au choix applicable.
- [`aman-scanner.js`](./aman-scanner.js) : inventaire local à lancer manuellement dans DevTools sur une page autorisée ; noms de cookies uniquement, signal de marqueur ALAMANE direct (non attestant) et aucun upload.
- [`mobile/ios/`](./mobile/ios/) : package Swift et [guide d’intégration iOS](./mobile/ios/README.md) ; [`mobile/android/`](./mobile/android/) : projet bibliothèque Gradle et app exemple ; [`mobile/react-native/`](./mobile/react-native/) : source TypeScript/TSX, compilation Babel et [guide React Native](./mobile/react-native/README.md). Ces SDK mobiles restent des bases de pilote : aucun n’a encore été intégré dans une application cliente ni publié comme release signée.
- [Validation produit](./.github/workflows/product-validation.yml) : vérifie l’API et le SDK Web, compile la bibliothèque et l’exemple Android, compile le package Swift pour le simulateur iOS et compile/emballe le paquet React Native à chaque pull request et push. Sur cette version du workflow, un lancement manuel est configuré pour joindre l’AAR Android, l’APK de démonstration, le tarball React Native et un SBOM CycloneDX limité aux dépendances npm React Native, comme artefacts privés téléchargeables pendant 14 jours ; cette configuration n’a pas encore été exécutée. Ces fichiers ne sont ni signés ni publiés comme releases. Le SBOM ne couvre pas les plateformes natives ni l’environnement de build. Les compilations des SDK ne valident ni l’intégration dans une application cliente ni l’aptitude à la production.
- [Mises à jour des dépendances](./.github/dependabot.yml) : Dependabot surveille chaque semaine les actions GitHub, les dépendances Python et Gradle, puis ouvre des pull requests à examiner ; aucune mise à jour n’est fusionnée automatiquement.
- La console génère pour chaque propriété un extrait de démarrage Web, iOS ou Android avec son identifiant réel. Le SDK React Native a un guide d’intégration séparé. Les URL sont des exemples, et les packages mobiles ne sont pas encore publiés.
- [`PLAN_COMMERCIALISATION.md`](./PLAN_COMMERCIALISATION.md) : segment pilote, découverte client et conditions de préparation commerciale.
- [`PROSPECTION_BANQUES_MAROC.md`](./PROSPECTION_BANQUES_MAROC.md) : première liste interne de comptes à qualifier, basée sur des signaux publics ; aucun établissement n’a été contacté.
- [`SEQUENCE_PROSPECTION.md`](./SEQUENCE_PROSPECTION.md) : brouillons d’introduction par compte et suivi de qualification, à personnaliser ; aucun message n’a été envoyé.
- [`DOSSIER_SECURITE_FOURNISSEUR.md`](./DOSSIER_SECURITE_FOURNISSEUR.md) : état factuel du prototype pour préparer la qualification sécurité d’un prospect ; document interne de travail, pas une attestation fournisseur.
- [`SUPPORT_DECOUVERTE_PILOTE.md`](./SUPPORT_DECOUVERTE_PILOTE.md) : pitch de découverte, déroulé de démo, questions de qualification et hypothèse de pilote, avec l’état réel du produit.
- [`ARCHITECTURE.md`](./ARCHITECTURE.md) : frontières techniques et séquence de réalisation.

### Intégration Web minimale

Héberger le fichier SDK depuis un domaine approuvé par l’équipe cliente, puis déclarer la propriété publiée et ses scripts balisés. L’exemple ci-dessous montre l’ordre de configuration ; les traceurs doivent être remplacés par ceux inventoriés et approuvés par le client.

```html
<script src="/assets/aman-cmp.js"
        data-aman-api-base-url="https://cmp.example.ma"
        data-aman-property-id="PROPERTY_ID"
        data-aman-channel="web"
        data-aman-collect-decision-events="false"
        data-aman-title="Vos préférences"
        data-aman-message="Choisissez les usages que vous autorisez."></script>
<script type="text/plain" data-aman-category="analytics"
        data-aman-src="/assets/analytics.js"></script>
```

La politique utilise les codes de langue `fr` et `ar`. Sans `data-aman-locale`, le SDK Web applique `defaultLanguage` de la politique publiée ; une application hôte peut le remplacer explicitement par cet attribut. Le SDK normalise une locale régionale comme `ar-MA` vers l’arabe standard `ar` pour choisir les textes et appliquer le sens RTL ; cela n’ajoute pas de traduction en darija. L’éditeur de politiques recueille séparément les notices française et arabe via `noticeTranslations`, et le SDK choisit celle de la langue affichée. Les clients qui ignorent ce champ peuvent continuer à lire le champ historique `notice`.

La configuration par attributs évite un bloc JavaScript en ligne. Pour une CSP à nonce, l’application hôte ajoute le nonce de la réponse HTTP à l’élément `<script src="…aman-cmp.js">` et l’autorise dans ses directives `script-src` et `style-src`. ALAMANE propage ce nonce à sa feuille de style et aux scripts balisés qu’il crée. Il faut garder la politique CSP du site et ses hôtes de scripts sous le contrôle de l’équipe sécurité du client.

La politique est récupérée avant le rendu de la bannière. Le SDK vérifie aussi les politiques téléchargées et celles relues depuis son cache : version de schéma, propriété, langues, notice, finalités, canaux et durées. Une politique invalide n’est pas mise en cache ni appliquée ; pour le Web, une durée supérieure à 180 jours est refusée. Une fois initialisé, le SDK revalide la politique toutes les cinq minutes et au retour de l’onglet au premier plan, avec au moins une minute entre deux vérifications. Une nouvelle version invalide le choix associé à l’ancienne et émet `aman:policy-updated`; si aucune politique valide ne peut être obtenue, les finalités optionnelles restent fermées et le SDK émet `aman:policy-unavailable`. En cas de panne réseau ou de réponse temporaire (`408`, `425`, `429` ou `5xx`), il peut appliquer sa dernière politique valide en cache ou encore disponible en mémoire. Une réponse non temporaire (dont `404`, aucune politique publiée) ou une politique invalide efface le cache et le choix. Les appels de lecture et d’envoi omettent les identifiants navigateur et refusent les redirections HTTP. Le SDK observe les balises `type="text/plain"` avec `data-aman-src` qui sont ajoutées ou complétées après son initialisation, puis les charge seulement si leur finalité est active. Un choix enregistré dans un autre onglet est réappliqué, et le choix courant est réévalué à son expiration pendant que la page reste ouverte. Si la politique est indisponible et qu’aucune version valide n’est en cache ou en mémoire, le SDK affiche un message accessible en français ou en arabe avec un bouton « Réessayer » ; les balises gérées restent désactivées. Le choix est d’abord conservé dans `localStorage`; si l’écriture échoue, le SDK tente `sessionStorage` puis garde le choix en mémoire pour l’onglet courant. Dans ces deux derniers cas, il affiche que le choix ne sera pas conservé durablement et `aman:consent-saved` indique `storedDurably: false`. Il faudra le redemander après la fermeture de l’onglet si aucun stockage persistant n’a fonctionné. L’état avant réponse est piloté par `initiallyEnabled`, une valeur explicite de politique distincte de `consentRequired` ; les politiques historiques sans ce champ démarrent les finalités optionnelles désactivées. Le responsable et son conseil doivent valider le classement et le réglage avant publication. Un script déjà exécuté n’est pas déchargé automatiquement : la révocation doit aussi être raccordée au mécanisme d’arrêt propre de chaque fournisseur. Le site [demo-site.html](http://localhost:8000/demo-site.html) montre ce parcours avec des scripts locaux sans tiers.

### Google Tag Manager

À l’initialisation puis après chaque mise à jour du choix, le SDK ajoute à `window.dataLayer` un événement `aman_consent_update` avec la propriété, la version de politique, le canal, l’indicateur `hasUserChoice` et l’état booléen effectif de chaque finalité sous `aman.purposes`. Dans GTM, crée un déclencheur **Événement personnalisé** nommé `aman_consent_update`, puis une variable de couche de données pour `aman.purposes.analytics` (et une par finalité utile). Filtre chaque balise sur l’événement et la valeur `true` de la finalité concernée. Google décrit le contrat `dataLayer.push({event: ...})` et ce type de déclencheur dans sa [documentation de la couche de données](https://developers.google.com/tag-platform/tag-manager/datalayer) et son [aide sur les déclencheurs personnalisés](https://support.google.com/tagmanager/answer/7679219?hl=fr).

Ce pont ne crée ni ne publie le conteneur GTM et n’intercepte pas ses déclencheurs Page View. Configure les balises de façon qu’elles ne partent pas avant l’événement et le consentement applicable. Un `false` ultérieur ne décharge pas un script déjà exécuté : la révocation doit appeler l’API d’arrêt/réinitialisation du fournisseur. Pour les balises Google, configure également les API Consent Mode de GTM ; l’événement ALAMANE seul ne remplace pas les mises à jour de consentement natives de Google.

Le centre de préférences Web est utilisable au clavier : `Tab` reste dans le dialogue, `Échap` le ferme et le focus retourne à son point d’ouverture. L’intégrateur reste responsable de vérifier l’accessibilité du site hôte et de ses contenus.

La transmission des décisions au tableau de bord est désactivée par défaut. Après validation du traitement et de l’information visiteur par le client, l’intégrateur Web peut activer `collectDecisionEvents: true` ; les applications natives doivent appeler explicitement `AmanConsentAPIClient.recordDecision`. Seuls les choix explicitement enregistrés sont envoyés, avec un identifiant aléatoire par décision, la version de politique et les booléens par finalité ; aucun identifiant de compte ou d’appareil n’est ajouté. Le serveur utilise son heure de réception ; les événements expirés sont exclus des agrégats, supprimés au démarrage ou à la réception d’un nouvel événement, et purgés lors d’une passe périodique d’environ 60 secondes lorsque l’API tourne. Ces événements déclarés par le client SDK alimentent des compteurs, mais ne prouvent pas seuls l’identité, l’affichage ou l’action réelle d’un visiteur. Les choix natifs restent locaux tant que l’application hôte n’active pas cet appel.

Les trois clients SDK refusent une API distante en HTTP : configure une URL HTTPS en intégration réelle. HTTP reste permis uniquement pour `localhost`, `127.0.0.1` et `::1` dans les démonstrations locales.

## État et limites

Cette version est un démonstrateur pour cadrer un pilote, pas une offre exploitable en banque. L’API refuse le mode production et utilise SQLite local par défaut ; un adaptateur PostgreSQL de préproduction est disponible derrière `AMAN_DATABASE_URL`, mais il reste à valider contre une instance PostgreSQL cible. Les limiteurs sont stockés en base ; le partage multi-instance en PostgreSQL exige une clé HMAC commune et n’a pas encore été validé sur une infrastructure cible. Il manque notamment le déploiement et l’exploitation durcis, MFA/SSO, l’envoi des invitations, la supervision, le SLA, une revue de sécurité indépendante, des intégrations testées sur les systèmes du client et des versions signées / publiées des SDK mobiles. Le modèle de preuve visiteur reste à valider avant toute centralisation.

Les politiques doivent être renseignées et approuvées par le client. Le schéma exige une notice configurée, mais ne détermine pas la base légale, la qualification d’une finalité ou les formalités applicables. La limite de 180 jours appliquée au canal Web est une garde de produit pour les cookies dans le périmètre D-939-2025 ; la portée du texte et les règles mobiles nécessitent une validation juridique au cas par cas. Voir les sources citées dans le plan commercial.
