# Aman API — tranche de développement

Cette API ajoute un plan de contrôle local au démonstrateur. Elle n’est pas un service de production et ne doit pas recevoir de données de clients ou d’une banque.

## Lancer

Depuis la racine du dépôt :

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r backend/requirements.txt
python backend/migrate_db.py
python backend/create_admin.py
uvicorn aman_api.main:app --app-dir backend --host 127.0.0.1 --port 8001 --no-access-log
```

Les changements de schéma SQLite sont versionnés dans `backend/aman_api/migrations/`. Exécuter `python backend/migrate_db.py` après chaque mise à jour de l’API et avant de démarrer le serveur. Le démarrage refuse une base non initialisée, en retard ou dont le schéma ne correspond pas au code. Les scripts locaux de création d’admin et de démonstration initialisent aussi les migrations pour faciliter le premier lancement.

Le stockage de développement est SQLite dans `~/.alamane/aman-dev.sqlite3` par défaut ; une nouvelle base est créée avec le mode `0600` et son répertoire dédié en `0700`. Le chemin peut être remplacé par `AMAN_DATABASE_PATH`, à condition de choisir un répertoire privé. Les permissions des bases existantes ne sont pas modifiées automatiquement : vérifiez-les et protégez également les fichiers WAL/SHM déjà présents. La doc interactive est à <http://127.0.0.1:8001/docs>.

Pour une préproduction isolée, `AMAN_DATABASE_URL` sélectionne l’adaptateur PostgreSQL et un pool borné par `AMAN_DB_POOL_MAX_SIZE` (1 à 50, 10 par défaut et par processus API). Injecter cette URL depuis le gestionnaire de secrets, jamais depuis le dépôt. Toute connexion distante exige `sslmode=verify-full`. Pour partager les limites de requêtes entre processus, fournir aussi `AMAN_RATE_LIMIT_HASH_KEY` (au moins 32 octets aléatoires, identiques dans chaque instance, via le gestionnaire de secrets). La clé n’est jamais journalisée ni stockée en base ; la remplacer invalide les empreintes des buckets actifs et réinitialise temporairement ces limites. La commande opérateur `python backend/migrate_db.py` et les scripts `create_admin.py` / `seed_demo.py` appliquent le schéma avec `AMAN_MIGRATION_DATABASE_URL`; pour un PostgreSQL distant, l’API et l’opérateur doivent nommer des rôles différents et cibler le même serveur et la même base. Le rôle opérateur doit pouvoir créer et modifier le schéma. L’API ne fait que vérifier `schema_migrations` au démarrage. Pour un serveur local, la même URL loopback peut servir aux deux rôles pour le développement.

Après la migration distante, accorder les droits applicatifs séparément, sans donner à l’API la propriété du schéma ni les droits DDL. Pour un schéma `public`, le DBA peut appliquer le minimum DML sur les tables métier (adapter les noms de rôles et base) :

```sql
GRANT CONNECT ON DATABASE aman TO aman_api;
GRANT USAGE ON SCHEMA public TO aman_api;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  users, organizations, memberships, invitations, ownership_transfers,
  properties, policies, sessions, audit_events, consent_events, scan_reports,
  rate_limit_buckets
  TO aman_api;
GRANT SELECT ON TABLE schema_migrations TO aman_api;
```

Cette voie n’a pas encore été éprouvée contre un service PostgreSQL géré par un acheteur et ne lève pas le refus du mode `production`.

La démo web utilise `http://localhost:8000`; l’API autorise cette origine pour les appels avec cookies. `admin.html` lit l’URL API depuis `<meta name="aman-api-base-url" content="https://api.exemple.ma">`; en l’absence de ce réglage, elle utilise le port 8001 en local et la même origine en hébergement distant. `AMAN_CORS_ORIGINS` doit contenir les origines exactes des consoles qui utilisent les cookies. Chaque origine de propriété Web est vérifiée à l’exécution et autorise seulement les routes publiques de lecture de politique et d’envoi d’événement de consentement, sans cookies. Une origine saisie dans Aman est une association de configuration, pas une preuve de contrôle du domaine. Le compte initial est créé par commande locale, pas par une route d’inscription publique.

## Fonctionnalités du socle

- Connexion par session opaque stockée sous forme de condensat ; cookie HTTP-only, SameSite strict ; jeton CSRF séparé pour les mutations.
- Limiteurs de connexion, de remontée de décisions et de tentatives d’invitation persistés en base et atomiques pour chaque bucket : 20 échecs de connexion par source sur 10 minutes, puis pause de 10 minutes ; 120 événements par source et 6 000 par propriété sur 60 secondes ; aperçus d’invitation limités à 120/minute et acceptations à 20/minute par source. Les fenêtres sont bornées en base et les buckets expirés sont purgés périodiquement. Les adresses IP et identifiants de propriété ne sont pas conservés en clair, seulement des HMAC calculés avec `AMAN_RATE_LIMIT_HASH_KEY`. Pour partager les limites entre plusieurs instances API, elles doivent viser la même base et utiliser la même clé HMAC. En PostgreSQL, cette clé explicite est obligatoire ; en SQLite local, la clé aléatoire par défaut est propre au processus et ne partage pas les quotas entre plusieurs processus. L’API ne fait confiance à aucun en-tête `X-Forwarded-*` ; derrière un proxy, il faudra définir le proxy de confiance ou limiter au niveau du reverse proxy.
- Les endpoints publics Web n’autorisent l’en-tête `Origin` que s’il correspond à l’origine configurée pour cette propriété, sans cookies et avec une liste réduite de méthodes et d’en-têtes. Les appels natifs n’envoient pas cet en-tête ; cette séparation et ces filtres ne prouvent ni l’identité d’un visiteur ni l’authenticité d’une application native.
- Comptes et appartenances par organisation avec rôles owner, admin, editor et viewer.
- Liste des membres et changements de rôle par owner/admin ; le rôle owner ne peut pas être modifié par le changement de rôle ordinaire.
- Transfert de propriété en deux étapes : le propriétaire actuel propose un admin existant, le destinataire accepte depuis son compte dans les 24 heures, puis les rôles changent atomiquement et l’action est auditée. Le jeton est transmis manuellement par un canal sécurisé ; le propriétaire peut révoquer le transfert en attente.
- Invitations à usage unique, expirant après 72 heures. Un nouvel utilisateur crée son compte ; un utilisateur existant prouve la possession du compte avec son mot de passe avant de rejoindre une autre organisation. La console fournit un lien d’acceptation dont le jeton est placé dans le fragment URL (non envoyé dans la requête initiale), le retire de l’adresse avant l’appel API et permet de le copier ou de préparer un brouillon `mailto:` à vérifier et envoyer par l’administrateur. Aucun service Aman n’envoie automatiquement les e-mails.
- Les aperçus d’invitation sont limités à 120 requêtes par minute et les acceptations à 20 par minute et adresse source, avec les mêmes buckets persistés et HMAC partagés que les autres limiteurs.
- Owner/admin peuvent consulter les invitations ouvertes ou expirées et révoquer un jeton non accepté ; la révocation est journalisée et invalide immédiatement le jeton. La livraison par e-mail reste à intégrer.
- Propriétés séparées par canal `web`, `ios` et `android` ; une propriété Web associe une origine HTTP(S) exacte (HTTP loopback seulement en développement), avec journalisation et mise à jour bloquée tant que ses rapports d’inventaire ne sont pas supprimés.
- Politiques validées contre `schemas/consent-policy.schema.json`, immuables après publication et livrées avec ETag. Les membres en lecture seule peuvent consulter chaque version et son historique de publication ; seuls owner/admin/editor préparent les brouillons, owner/admin les publient.
- Corps des requêtes API limités avant parsing JSON : 1 Mio par défaut, 512 Kio pour créer/modifier une politique et 16 Kio pour un événement public de consentement. Le schéma plafonne aussi une politique à 64 finalités, 32 fournisseurs par finalité et 32 entrées par liste de notice. Le reverse proxy de production devra appliquer ses propres limites et timeouts ; ces plafonds applicatifs ne remplacent pas une protection opérée.
- Les politiques peuvent contenir une notice française et arabe distincte sous `noticeTranslations`; le champ historique `notice` reste présent pour les intégrations qui ne lisent pas encore les traductions.
- L’éditeur peut créer et reprendre plusieurs finalités par propriété, avec identifiant stable, libellés et descriptions FR/AR, classification/règle d’activation configurées par le client et liste indicative de fournisseurs affichée dans l’interface de choix. Cette association n’applique aucune règle fournisseur : les scripts Web ne sont bloqués que lorsqu’ils sont explicitement raccordés au même identifiant de finalité dans le balisage du site.
- Publication à deux personnes activée par défaut pour chaque organisation : un owner/admin autre que la personne ayant effectué la dernière modification doit publier le brouillon.
- Révisions de brouillon avec contrôle optimiste : une sauvegarde basée sur une ancienne révision est refusée au lieu d’écraser silencieusement les modifications d’un collègue.
- Journal d’audit des actions administratives.
- Transmission facultative des décisions explicitement enregistrées : activable dans le SDK Web et appelable depuis les SDK natifs, mais jamais automatique sur mobile. Chaque événement comprend un identifiant aléatoire, les finalités booléennes, la politique/version et l’heure serveur. Aucun compte visiteur, courriel ou identifiant persistant d’appareil n’est accepté ou stocké.
- Agrégats de décisions par propriété et export CSV des événements SDK encore retenus accessibles aux membres ; ils ne contiennent pas d’identifiant de visiteur et ne prouvent pas son identité, l’affichage du choix ou l’action réelle.
- Expiration calculée selon la durée de rétention de la politique publiée ; les événements arrivés à échéance sont effacés au démarrage, à une nouvelle réception et par une tâche de purge périodique (intervalle maximal nominal : 60 secondes lorsque l’API tourne). Ce comportement local reste à remplacer par une politique d’effacement opérée, supervisée et vérifiée avant production.
- Export CSV UTF-8 du journal d’audit, accessible aux membres autorisés, filtrable par période et limité aux 10 000 événements les plus récents.
- Import manuel d’un inventaire `aman-local-inventory-v1` sur une propriété Web par owner/admin/editor ; l’origine exacte du rapport doit correspondre à celle configurée sur la propriété. Le rapport indique la présence d’un marqueur direct Aman sur les éléments script observés ; ce signal DOM ne prouve pas le contrôle complet des déclenchements et n’évalue pas les règles des gestionnaires de balises. Chaque rapport est borné à 1 Mio, les URL avec query, fragment ou identifiants sont refusées, et l’API recalcule les origines et les indicateurs first-party. Seuls les 20 imports les plus récents par propriété sont conservés. Les membres peuvent consulter les rapports ; les rôles d’édition peuvent les supprimer. L’import est journalisé sans conserver l’hôte dans le détail d’audit.

Pour préparer un jeu de démonstration fictif après avoir créé le premier admin, lancer `python backend/seed_demo.py`. Le script crée une organisation, une propriété Web de développement et un brouillon sans générer d’événements visiteurs. Il laisse la publication à deux personnes activée. Si plusieurs comptes existent, préciser `--owner-email`; toutes les données générées sont locales et fictives.

## Routes principales

| Route | Accès | Fonction |
| --- | --- | --- |
| `POST /v1/auth/login` | Public | Ouvre une session et retourne le jeton CSRF |
| `GET /v1/auth/me` | Session | Utilisateur et organisations accessibles |
| `GET /v1/dashboard` | Session | Comptes réels des organisations accessibles, états des propriétés/politiques et 12 dernières actions administratives |
| `POST /v1/organizations` | Session + CSRF | Crée une organisation |
| `POST /v1/organizations/{org}/invitations` | Owner/admin + CSRF | Crée une invitation à usage unique |
| `GET /v1/organizations/{org}/invitations` | Owner/admin | Liste les invitations non acceptées, leur rôle, date d’expiration et état |
| `DELETE /v1/organizations/{org}/invitations/{invitation}` | Owner/admin + CSRF | Révoque une invitation non acceptée et journalise l’action |
| `POST /v1/auth/invitations/preview` | Public + jeton | Vérifie une invitation et retourne le nom d’organisation, le rôle, une adresse partiellement masquée et l’expiration, sans cookie de session |
| `POST /v1/organizations/{org}/ownership-transfers` | Owner + CSRF | Propose le transfert à un admin existant et retourne un jeton à usage unique valable 24 heures |
| `GET /v1/organizations/{org}/ownership-transfers/pending` | Owner | Consulte le destinataire et l’expiration du transfert en attente, sans exposer le jeton |
| `DELETE /v1/organizations/{org}/ownership-transfers/pending` | Owner + CSRF | Révoque le transfert en attente |
| `POST /v1/auth/ownership-transfers/accept` | Session destinataire + CSRF + jeton | Le compte admin ciblé accepte ; l’ancien owner devient admin et le destinataire owner |
| `GET /v1/organizations/{org}/members` | Membre | Liste les membres et leurs rôles |
| `PUT /v1/organizations/{org}/members/{user}` | Owner/admin + CSRF | Change un rôle admin/editor/viewer ; refuse le rôle owner |
| `DELETE /v1/organizations/{org}/members/{user}` | Owner/admin + CSRF | Révoque une appartenance ; refuse de retirer le propriétaire actuel avant un transfert accepté |
| `POST /v1/auth/invitations/accept` | Public + jeton | Crée un compte ou ajoute le compte existant à une organisation après vérification du mot de passe |
| `POST /v1/organizations/{org}/properties` | Éditeur+ + CSRF | Crée une propriété web/iOS/Android |
| `GET /v1/organizations/{org}/properties` | Membre | Liste les propriétés, canaux et origines configurées |
| `PUT /v1/organizations/{org}/properties/{property}/origin` | Éditeur+ + CSRF | Configure l’origine exacte d’une propriété Web ; refuse un changement si des rapports sont attachés |
| `POST /v1/organizations/{org}/properties/{property}/scans` | Éditeur+ + CSRF | Importe explicitement un rapport JSON local sur une propriété Web |
| `GET /v1/organizations/{org}/properties/{property}/scans` | Membre | Liste jusqu’à 20 rapports récents et leurs métadonnées |
| `GET /v1/organizations/{org}/properties/{property}/scans/{report}` | Membre | Lit les éléments et classifications manuelles d’un rapport |
| `DELETE /v1/organizations/{org}/properties/{property}/scans/{report}` | Éditeur+ + CSRF | Supprime un rapport importé |
| `POST /v1/organizations/{org}/properties/{property}/policies` | Éditeur+ + CSRF | Crée un brouillon versionné |
| `GET /v1/organizations/{org}/policies/{policy}` | Membre | Lit le détail d’une version immuable et son historique ; les rôles d’édition peuvent reprendre un brouillon |
| `PUT /v1/organizations/{org}/policies/{policy}` | Éditeur+ + CSRF | Met à jour un brouillon avec `expectedRevision`; refuse les révisions périmées et toute version déjà publiée |
| `POST /v1/organizations/{org}/policies/{policy}/publish` | Owner/admin autre que le dernier éditeur + CSRF | Publie la politique |
| `GET /v1/public/properties/{property}/policy` | Public | SDK : dernière politique publiée, cacheable avec ETag |
| `POST /v1/public/properties/{property}/consent-events` | Public | Réception facultative d’un choix explicite du SDK Web ou d’un appel natif ; vérifie version, canal et finalités de la politique active, ignore les répétitions identiques et refuse les identifiants réutilisés avec d’autres valeurs |
| `GET /v1/organizations/{org}/properties/{property}/consent-metrics?days=30` | Membre | Agrégats par version de politique et finalité sur 1 à 180 jours ; aucun détail individuel |
| `GET /v1/organizations/{org}/properties/{property}/consent-events/export?days=30` | Membre | CSV des décisions déclarées encore conservées ; 1 à 3 650 jours, avec identifiant aléatoire, heure de réception, version, action et finalités. Aucun identifiant visiteur ; ce fichier ne prouve ni identité, affichage ni action réelle. |
| `GET /v1/organizations/{org}/audit` | Membre | Journal d’administration |
| `GET /v1/organizations/{org}/audit/export` | Membre | Export CSV ; accepte `from` et `to` en secondes Unix, limite `limit` de 1 à 10 000 |

Une lecture de brouillon retourne `revision`. Pour le modifier, le client doit renvoyer cette valeur dans `expectedRevision`; un conflit (HTTP 409) laisse la version enregistrée intacte. Après suppression d’une appartenance, les sessions de l’utilisateur subsistent, mais l’organisation disparaît de son espace.

Les routes de mutation nécessitent `X-Aman-CSRF` identique au cookie lisible `aman_csrf`. Le cookie de session reste HTTP-only. Pour les appels `fetch`, employer `credentials: "include"`.

La console `admin.html` utilise ces routes et permet de créer des organisations, d’inviter des membres, de consulter et révoquer leurs invitations non acceptées, de voir les membres actifs et de gérer leurs rôles, de transférer la propriété à un admin existant après acceptation par le destinataire, de créer des propriétés par canal et environnement (`development`, `staging`, `production`), de reprendre des brouillons, de les publier et d’importer des rapports JSON sur les propriétés Web. Les origines HTTP loopback ne sont acceptées qu’en développement ; les environnements recette et production exigent HTTPS. L’environnement est une métadonnée de gouvernance qui ne sépare pas les données, clés ou déploiements. Un même compte peut rejoindre plusieurs organisations ; l’acceptation d’une invitation pour un compte existant exige le mot de passe de ce compte. L’entrée `index.html` redirige vers la console connectée `admin.html`, qui charge les comptes multi-organisation et les agrégats de décisions récents lorsque la session est active ; elle propose aussi un CSV de 30 jours par propriété contenant les événements SDK déclarés encore retenus. L’ancienne maquette visuelle est isolée dans `maquette-dashboard.html` et affiche uniquement des données simulées ; les statistiques de scan intégrées de la console restent également simulées. Les contrôles de rédaction, d’invitation, de gestion d’équipe, de publication et d’import s’alignent sur le rôle actif. Dans le site fictif, ajouter `?property=<ID>` à l’URL pour charger sa politique web publiée depuis l’API.

## Limites connues à traiter avant une POC acheteur

- SQLite local ou adaptateur PostgreSQL de préproduction, migrations versionnées mais sans chiffrement de base configuré par Aman ni modèle de haute disponibilité.
- Pas de MFA, SSO, récupération de compte, alertes, service d’e-mail, supervision ni procédure d’incident. Les limites applicatives persistées ne remplacent pas un pare-feu applicatif ni une exploitation supervisée.
- Pas de rotation centralisée de secrets ni d’intégration à un coffre de secrets.
- La console entreprise, le SDK web et les clients SDK natifs savent lire la politique publique. Android a un module Gradle et une application exemple ; iOS a un package Swift ; React Native a un package TypeScript source. Aucun binaire ou package mobile n’a encore été publié, et les intégrations restent à compiler et valider sur les versions clientes visées.
- Les événements Web/iOS/Android sont des assertions des SDK client et ne constituent pas une preuve d’identité ni une preuve juridique complète. L’intégrateur doit activer l’envoi seulement après validation de l’information et du traitement par le client. Les appels natifs sont explicites ; ils ne sont pas activés par défaut.
- Les inventaires peuvent contenir des noms de cookies et des chemins de ressources internes. L’outil n’envoie rien automatiquement, mais un membre qui importe le JSON conserve explicitement ces éléments dans SQLite local ; vérifier manuellement l’hôte et le périmètre avant import. L’outil observe une seule page et n’accède pas aux cookies HttpOnly.
- L’association d’origine empêche les erreurs de rattachement ordinaires, mais n’atteste pas que le rapport a été réellement collecté sur cette page ni que l’organisation contrôle ce domaine ; l’import JSON est une action explicite d’un membre.
- L’en-tête Origin n’est pas un mécanisme d’authentification. Il n’y a pas de signature d’événement, détection de fraude, réconciliation navigateur/serveur, stockage inviolable, sauvegarde ou procédure d’effacement opérée. Ces événements restent des données de démonstration jusqu’à validation du modèle et de l’exploitation.
- Le serveur refuse `AMAN_ENVIRONMENT=production` tant que le stockage, l’exploitation et les contrôles de sécurité de production ne sont pas implémentés et audités.

La tranche locale relie déjà la console, l’API et le chargement des politiques par le SDK web et les sources natives. Restent à réaliser l’intégration chez un client, le packaging mobile, le modèle de preuve et l’ensemble des contrôles de production. Ce service démontre les frontières fonctionnelles et le contrôle de publication, pas l’aptitude d’Aman à traiter des données réelles.
