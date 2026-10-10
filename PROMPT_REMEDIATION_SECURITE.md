# ALAMANE — remédiation sécurité du prototype

## Rôle et objectif

Tu es un ingénieur sécurité applicative senior. Tu interviens sur ALAMANE, un prototype B2B de gestion du consentement destiné aux entreprises, assureurs et banques marocains.

Objectif : vérifier les constats ci-dessous dans le code, corriger ceux qui sont confirmés sans affaiblir les protections existantes, ajouter des tests de régression et laisser un résultat local, révisable et documenté. Le prototype n’est pas autorisé à traiter des données client réelles ni à être déployé en production dans le cadre de cette tâche.

## Isolation et Git — obligatoire

Le checkout principal est utilisé par Codex. Ne modifie pas ses fichiers de travail.

- Le dépôt se trouve sous `CMP consentment`.
- La branche locale actuelle est `codex/alamane-b2b-readiness`, à `69bca09`.
- Elle contient deux commits locaux non poussés, absents du remote GitHub.
- Travaille dans un worktree ou une copie séparée créée depuis le HEAD local `69bca09`, et non depuis une branche GitHub plus ancienne.
- Vérifie le chemin, la branche et `git rev-parse --short HEAD` avant de commencer.
- Tu peux créer des commits locaux séparés par remédiation.
- Ne pousse rien, ne crée pas de PR et ne modifie aucun remote.
- N’ouvre pas et ne change pas de données locales de démonstration.
- Ne demande, ne lis et ne stocke aucun secret ou identifiant de production.

Si le HEAD local n’est pas disponible dans le worktree, arrête-toi avant toute modification et explique l’écart.

## Règles d’implémentation

1. Lis les fichiers concernés avant de modifier le code et vérifie chaque constat ; ne suppose pas que l’audit est exact.
2. Commence chaque correction par un test de régression qui échoue avant le correctif. Puis implémente le changement et vérifie que ce test passe.
3. Conserve le style du dépôt : repositories SQL séparés, requêtes paramétrées, erreurs `HTTPException` en anglais, migrations versionnées pour SQLite et PostgreSQL quand le schéma change.
4. N’ajoute aucune dépendance à l’application sans la justifier. Pour une dépendance de test ou CI, explique son coût et son usage.
5. Documente toute nouvelle variable d’environnement dans `backend/README.md` et dans l’exemple de staging pertinent.
6. Ne dis pas qu’un test, une migration, une CSP, un fournisseur ou un environnement est validé s’il n’a pas réellement été vérifié.
7. Si une exigence produit est ambiguë, décris les options et leurs conséquences avant de choisir une règle de sécurité irréversible.
8. Après chaque point : lance son test ciblé et la suite `python -m unittest discover backend/tests -v`, vérifie `git diff --check`, puis fais un commit local séparé si les contrôles passent.

## Constats à vérifier et traiter

### P1 — Limitation de débit derrière un reverse proxy

À vérifier dans `backend/aman_api/main.py` et `ops/container/entrypoint.sh` :

- `login_client_key`, `enforce_consent_event_rate_limit` et `enforce_invitation_rate_limit` utilisent actuellement `request.client.host`.
- Derrière certains reverse proxies, les requêtes peuvent alors partager la même adresse du proxy.
- Ne lis jamais directement `X-Forwarded-For` depuis la requête pour décider de l’IP.

Remédiation attendue :

- Ajouter `AMAN_TRUSTED_PROXY_IPS`, vide par défaut.
- Valider chaque valeur en IP/CIDR et refuser explicitement `*`, les valeurs vides mal formées et les entrées invalides.
- Ne passer les paramètres Uvicorn de traitement des en-têtes proxy que si la configuration est valide. Le socket peer doit appartenir à une IP/CIDR explicitement approuvée.
- Centraliser la source IP dans `client_ip(request)` ; l’application doit utiliser la valeur de `request.client.host` après la configuration de confiance Uvicorn.
- Normaliser les adresses IPv6 en préfixes `/64` pour les clés de débit. Définir et tester le comportement des adresses IPv4 mappées IPv6.
- Garder deux limites indépendantes à la connexion : une par IP et une par identifiant de compte normalisé, stockée sous forme HMAC.
- Ne pas transformer la limite par compte en verrouillage permanent facile à provoquer contre un tiers. Utilise une temporisation temporaire/progressive ou un mécanisme équivalent, avec durée bornée et procédure de reprise.
- Les réponses d’échec doivent rester génériques et ne pas révéler si l’adresse correspond à un compte.

Tests minimaux :

- Des erreurs depuis l’IP A ne bloquent pas un utilisateur qui se connecte depuis l’IP B.
- Des tentatives distribuées contre un même identifiant déclenchent sa limite sans affecter un autre identifiant.
- Les comptes existants et inexistants ne sont pas distinguables par le code ou le message d’erreur lorsque la limite par compte intervient.
- Deux IPv6 qui ne diffèrent que dans leurs 64 bits de poids faible partagent le même bucket.
- Sans proxy déclaré, un `X-Forwarded-For` forgé est ignoré.
- Avec une IP/CIDR de proxy explicitement autorisée, l’adresse client propagée est traitée conformément à la configuration Uvicorn.

Référence de configuration : documentation officielle [Uvicorn — Settings](https://www.uvicorn.org/settings/).

### P2 — Saturation globale du stockage des décisions

À vérifier dans `record_consent_event` et les limites associées de `backend/aman_api/main.py` :

- Il existe actuellement un plafond global de 100 000 événements actifs et un plafond par propriété de 25 000 ; l’atteinte d’un plafond peut produire un `503`.
- `Origin` et CORS ne sont pas une authentification d’un client hors navigateur.

Remédiation attendue :

- Ne supprime pas toute borne globale : elle protège contre une croissance sans limite du stockage.
- Ajoute ou clarifie des quotas d’admission par organisation ou propriété, avec des limites documentées et configurables.
- Ajoute une alerte de capacité avant le plafond global et un état opérationnel approprié.
- Garde un plafond global d’urgence pour borner les ressources, et explique ce qui se passe lorsqu’il est atteint.
- Réutilise la normalisation IPv6 de P1 dans les limites par client.
- Documente qu’une limite au niveau reverse proxy/WAF reste nécessaire pour l’endpoint public.

Tests minimaux :

- Le dépassement du quota de l’organisation A n’empêche pas l’organisation B, encore sous son quota, d’enregistrer un événement.
- Un test distinct couvre le plafond global d’urgence et sa réponse.
- La déduplication reste inchangée : même `eventId` et même contenu donne `duplicate: true` ; même `eventId` avec contenu différent donne `409`.
- Vérifie que les événements expirés sont exclus et purgés comme prévu.

### P3 — Désactivation de la publication à deux personnes

À vérifier dans `update_organization_approval_settings`, `publish_policy` et leurs repositories.

Le code actuel permet à un owner/admin de modifier le réglage. Vérifie aussi que les propriétés `production` imposent déjà une seconde personne, même si le réglage organisationnel est désactivé.

Avant de coder, clarifie l’invariant :

- Si la séparation est obligatoire pour toutes les politiques protégées, une seule personne ne doit pas pouvoir désactiver la protection puis publier seule.
- Une simple comparaison d’horodatages ou de l’auteur de la dernière modification n’est pas suffisante si un changement de réglage peut avoir lieu entre deux modifications.
- Préfère un changement de réglage protégé par une approbation distincte et auditée, ou un invariant serveur équivalent lié à la révision de politique.
- Préserve le comportement attendu des environnements de développement/recette s’ils doivent rester configurables.
- Toute évolution de schéma nécessite une migration SQLite et PostgreSQL.

Tests minimaux :

- Un admin ne peut pas affaiblir un réglage protégé si telle est la politique choisie.
- Le scénario « modifier le brouillon, affaiblir la règle, publier seul » échoue dans les environnements protégés, y compris si l’auteur est owner.
- Un second approbateur qui n’a pas modifié le brouillon peut publier.
- Production reste protégée même si le réglage organisationnel est désactivé.
- Les changements sensibles restent inscrits dans l’audit avec les bonnes identités.

### P4 — Nonce CSP propagé aux scripts gérés

À vérifier dans `aman-cmp.js`, notamment `applyTags`, `observeManagedTags` et `SDK_SCRIPT.nonce`.

Le SDK copie actuellement son nonce sur les scripts créés depuis les placeholders `script[type="text/plain"][data-aman-src]`. Vérifie si un placeholder injecté dynamiquement peut ainsi faire charger un script que le serveur n’avait pas autorisé.

Remédiation attendue :

- Si le SDK est lancé avec un nonce, n’activer un placeholder que s’il porte le même nonce via sa propriété DOM `placeholder.nonce`.
- Ne copie pas le nonce à un placeholder sans nonce ou portant un nonce différent.
- Résous `data-aman-src` en URL absolue et refuse les identifiants, les protocoles dangereux et les hôtes non autorisés.
- Pour le pilote, privilégie une liste explicite d’origines autorisées. Définis une règle sûre par défaut et documente comment autoriser les hôtes réellement utilisés.
- Préserve le fonctionnement des intégrations existantes sans nonce, mais valide toujours le protocole et la source.
- Mets à jour `SDK_WEB.md` avec le contrat exact du nonce et les limites de la protection.
- Le nonce ne remplace pas l’assainissement HTML ; ne prétends pas qu’il corrige toute vulnérabilité XSS.

Tests minimaux :

- Un placeholder sans nonce ajouté dynamiquement ne démarre pas avec un SDK à nonce.
- Un placeholder avec le nonce correspondant démarre seulement après consentement effectif.
- Un nonce différent, un protocole dangereux, une URL avec identifiants et une origine non autorisée sont refusés.
- Vérifie le comportement sur une page de test navigateur ou un harness fiable. `node --check` seul ne valide pas ce comportement.
- Évite d’ajouter `jsdom` ou Playwright sans justification ; si tu ajoutes un nouvel outil, explique son coût et son rôle.

Référence : [W3C CSP Level 3](https://www.w3.org/TR/CSP/).

### P5 — MFA console : conception d’abord

Ajoute à `PLAN_MIGRATION_PRODUCTION.md` une proposition courte couvrant :

- WebAuthn et TOTP, avec comparaison de leurs coûts et contraintes ;
- enrôlement et vérification ;
- codes de secours stockés sous forme protégée, à usage unique ;
- exigence MFA pour owner/admin ;
- récupération ou réinitialisation par opérateur, avec audit ;
- sessions existantes, réauthentification des opérations sensibles, CSRF et limitation de débit.

N’implémente pas un système MFA maison dans ce lot. Toute implémentation devra faire l’objet d’une décision de conception distincte et ne devra pas introduire de dépendance non validée.

### P6 — HSTS et CSP de la console

À vérifier dans `security_headers` et les fichiers `/console`.

- Le démarrage en environnement `production` est actuellement refusé ; vérifie donc si la condition qui ajoute HSTS peut réellement être atteinte.
- Ne lie pas HSTS uniquement à `COOKIE_SECURE`. Émets-le seulement quand le transport HTTPS est confirmé par une configuration fiable ou géré par le proxy TLS.
- N’utilise `includeSubDomains` que si tous les sous-domaines concernés sont HTTPS.
- La console contient des scripts/styles inline : n’impose pas directement une CSP stricte qui casse l’interface.
- Commence par une politique `Content-Security-Policy-Report-Only`, mesure les violations, puis externalise ou protège les scripts/styles avec nonces ou hashes avant d’appliquer une politique d’exécution.
- Cible les routes utiles sans casser le SDK Web ou la page fictive.

Tests minimaux : HSTS absent quand le transport est HTTP ; présence seulement quand HTTPS est explicitement reconnu ; rendu console vérifié sous la CSP retenue ; aucune régression sur la démo.

### P7 — Mot de passe lors de l’acceptation d’invitation

À vérifier dans `accept_invitation` :

- Le endpoint a déjà une limite par IP, mais le mot de passe d’un compte existant est vérifié dans ce parcours.
- Ajoute une limite par compte pour cette vérification sans permettre un verrouillage durable déclenché par un tiers.
- Ne confonds pas invitation invalide, compte existant et mot de passe incorrect dans les réponses observables au-delà des exigences métier.
- Garde la limite par IP et les protections actuelles du jeton d’invitation.
- Réutilise le mécanisme HMAC et la normalisation introduits en P1 si approprié.

Ajoute un test avec tentatives distribuées sur le même compte et un test qui confirme qu’un autre compte reste utilisable.

### P8 — Injection de formule dans l’export CSV

À vérifier dans `audit_csv_cell`.

- Teste les cellules commençant par `=`, `+`, `-`, `@`, tabulation, retour chariot, saut de ligne, ainsi que des espaces suivis d’une formule.
- Choisis un encodage qui neutralise effectivement les formules dans les tableurs visés sans modifier les valeurs inoffensives.
- Vérifie les cellules après lecture par le parseur CSV et documente les limites propres aux tableurs.

Ne change pas seulement le code sans tests couvrant les caractères de contrôle et les préfixes précédant une formule.

### P9 — Chaîne d’approvisionnement Python

- Épingle l’image `python:3.13-slim` sur un digest vérifié, et documente comment la mettre à jour.
- Crée un fichier de dépendances résolues avec hashes et fais-le utiliser par le Dockerfile et la CI.
- Ajoute `pip-audit` à la CI avec une version/action maîtrisée, sans l’ajouter aux dépendances runtime.
- Respecte le plan gratuit GitHub : préfère intégrer le contrôle au workflow existant et évite de multiplier les jobs coûteux.
- Distingue vulnérabilités trouvées, faux positifs documentés et vulnérabilités effectivement corrigées ; ne masque pas un échec pour faire passer la CI.
- Ne prétends pas qu’un audit a été exécuté si l’outil n’était pas disponible.

### P10 — Valeur probante des événements

Vérifie `DOSSIER_SECURITE_FOURNISSEUR.md` et `PLAN_MIGRATION_PRODUCTION.md`. La limite indiquant que les décisions reçues sont déclarées par le SDK, non authentifiées et ne prouvent ni l’identité ni le rendu est déjà décrite dans ces documents. Maintiens une formulation cohérente ; ne crée pas de paragraphes redondants.

## Protections à préserver

Ne les affaiblis pas :

- requêtes SQL paramétrées ;
- scrypt, comparaison en temps constant et faux hash pour les comptes inexistants ;
- double contrôle CSRF et cookies `HttpOnly` / `SameSite=Strict` ;
- absence de `innerHTML` dans la console et le SDK ;
- limites de taille avant parsing des requêtes ;
- conteneur non-root et secrets via `*_FILE` ;
- permissions CI en lecture seule ;
- mode production toujours refusé tant que l’architecture n’est pas validée.

## Vérification finale

Lance, selon les outils disponibles :

- `python -m unittest discover backend/tests -v`
- `node --check aman-cmp.js`
- `node --check aman-scanner.js`
- `bash -n ops/container/entrypoint.sh`
- `bash -n scripts/start-demo.sh`
- tests de migration SQLite ; teste PostgreSQL seulement si une instance de test est déjà disponible, sans utiliser de base réelle ;
- `pip-audit` sur les dépendances lockées et vérification du build Docker si Docker est disponible ;
- `git diff --check`.

N’utilise ni la base locale de démonstration ni le serveur `localhost:8000` pour des tests destructifs. N’exécute pas le seed et ne démarre pas un second serveur sur le port 8000.

## Compte rendu attendu

À la fin, fournis :

1. Un tableau P1–P10 : confirmé / corrigé / partiel / non traité.
2. Les fichiers touchés et les migrations créées.
3. Les tests ajoutés, ceux exécutés et leurs résultats.
4. Les contrôles qui n’ont pas pu être exécutés, avec la raison.
5. Les risques résiduels et les décisions encore nécessaires.
6. Les commits locaux créés, sans push ni PR.
