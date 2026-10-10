# Image conteneur de préproduction ALAMANE

Cette image fournit un runtime de préproduction pour l’API et sert les fichiers statiques de la console sous `/console/`. Elle refuse SQLite, exige PostgreSQL et une clé HMAC explicite, fonctionne avec l’utilisateur système `aman` et n’accepte que `AMAN_ENVIRONMENT=staging`. Le mode `production` reste refusé par l’application. Cette image n’est ni un déploiement hébergé ni une release approuvée pour des données réelles.

## Construire l’image

Depuis la racine du dépôt :

```sh
docker build -t alamane-api:staging .
```

L’image de base est épinglée par digest (index multi-architecture de `python:3.13-slim`) et les dépendances Python sont installées depuis `backend/requirements.lock` avec vérification des empreintes. Pour mettre à jour l’image de base : relever le nouveau digest avec `docker buildx imagetools inspect python:3.13-slim` (ligne `Digest` de l’index), remplacer la valeur dans le `Dockerfile`, reconstruire et relancer les contrôles, puis consigner le changement dans le commit.

Ne pas transmettre de mot de passe ou d’URL de base dans un argument `--build-arg` : les secrets ne doivent pas être intégrés à l’image. L’image contient l’API, ses exigences Python, le schéma de politique et les fichiers statiques de la console. Après démarrage, la console est disponible sur `/console/`, la maquette assurance sur `/console/demo-assurance.html`, le SDK Web sur `/aman-cmp.js` et l’API sur les routes `/v1/` et `/health/ready`. La maquette utilise des comptes et scripts fictifs ; elle ne constitue pas un portail client authentifié. En hébergement distant, la console utilise la même origine pour l’API ; place l’ensemble derrière un proxy TLS et configure une URL HTTPS côté intégration.

## Préparer une préproduction

Créer un service PostgreSQL de préproduction et des fichiers de secrets lisibles par le conteneur. Par exemple, un orchestrateur peut monter :

- `/run/secrets/AMAN_DATABASE_URL` : URL PostgreSQL du rôle d’exécution, avec `sslmode=verify-full` si l’hôte est distant ;
- `/run/secrets/AMAN_RATE_LIMIT_HASH_KEY` : clé HMAC commune d’au moins 32 octets pour toutes les instances ;
- `/run/secrets/AMAN_MIGRATION_DATABASE_URL` : URL du rôle opérateur, montée uniquement dans l’exécution ponctuelle de migration ou de création initiale du compte.

Copier [`staging.env.example`](./staging.env.example) et [`staging-migrate.env.example`](./staging-migrate.env.example) dans un répertoire d’exploitation hors du dépôt, puis remplacer les exemples par les hôtes et origines approuvés. Les fichiers `.env` ne contiennent que des chemins de montage, pas les valeurs secrètes. Monter `/run/secrets/AMAN_DATABASE_URL` et `/run/secrets/AMAN_RATE_LIMIT_HASH_KEY` dans l’API. Pour la migration, monter aussi `/run/secrets/AMAN_MIGRATION_DATABASE_URL` : son URL doit viser le même serveur, port et base que l’URL d’exécution, mais utiliser un rôle distinct. Les certificats nécessaires à `verify-full` doivent être fournis au runtime selon les règles du gestionnaire de secrets et de la plateforme choisie.

Depuis la racine du dépôt, créer le répertoire de secrets et y déposer les fichiers fournis par le gestionnaire choisi. À titre d’exemple local uniquement :

```sh
mkdir -p .local/secrets
chmod 700 .local/secrets
```

Lancer la migration avec le profil opérateur ponctuel, puis l’API avec le profil runtime qui n’inclut pas le secret opérateur :

```sh
docker run --rm --env-file ops/container/staging-migrate.env.example --mount "type=bind,src=$PWD/.local/secrets,dst=/run/secrets,readonly" alamane-api:staging migrate
docker run --rm --env-file ops/container/staging.env.example --mount "type=bind,src=$PWD/.local/secrets,dst=/run/secrets,readonly" -p 127.0.0.1:8000:8000 alamane-api:staging
```

Les commandes d’exemple ne contiennent aucun secret réel et l’API n’est exposée que sur l’interface loopback de la machine hôte. Les migrations ne s’exécutent pas au démarrage de l’API. Pour un environnement partagé, remplacer ces montages locaux par les secrets de l’orchestrateur et démarrer le conteneur derrière un reverse proxy TLS configuré et approuvé par l’organisation.

Pour créer le premier administrateur, lancer une commande ponctuelle `create-admin` avec les mêmes secrets de base et de HMAC, plus la connexion opérateur. Le terminal demande l’adresse et un mot de passe sans les afficher. N’exécuter cette opération qu’avec les personnes autorisées et dans l’environnement ciblé.

## Ce que ce paquet ne fournit pas

- Aucun choix de fournisseur cloud, région, résidence, transfert ou modèle dédié/mutualisé.
- Aucun certificat TLS, reverse proxy, pare-feu applicatif, chiffrement de stockage, sauvegarde, restauration, supervision, alerting, SLA ou réponse aux incidents.
- Aucun proxy TLS, SSO/MFA, release SDK signée ou validation PostgreSQL en conditions réelles. Le chemin `/console/` n’a pas encore été construit ou exercé dans un déploiement cible.
- Aucun feu vert pour enlever le refus `AMAN_ENVIRONMENT=production` ou traiter des données client.

Le contrôle `/health/ready` passe au vert seulement si PostgreSQL répond et que son schéma est à jour. Il ne prouve pas l’aptitude opérationnelle ou juridique du service. Revoir les rôles de base et appliquer le modèle de privilèges [`ops/postgres-runtime-privileges.sql`](../postgres-runtime-privileges.sql) avec le DBA avant toute préproduction.
