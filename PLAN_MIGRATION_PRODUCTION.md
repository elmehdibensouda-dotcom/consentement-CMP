# Plan de transition vers un service hébergeable

**État :** plan d’ingénierie interne, 8 octobre 2026
**But :** préparer un pilote entreprise sans présenter le prototype local comme apte à recevoir des données réelles.

## Décision d’architecture proposée

Conserver SQLite pour le développement local et retenir PostgreSQL comme cible de persistance du service hébergé. Ne pas choisir dans ce document un fournisseur cloud, une région d’hébergement, un modèle SaaS mutualisé ou dédié : ces choix dépendent des exigences de sécurité, d’hébergement, de transfert et d’achat des premiers clients.

Le serveur continuera de refuser `AMAN_ENVIRONMENT=production` jusqu’à ce que les critères de mise en service ci-dessous soient satisfaits et qu’une revue sécurité distincte ait été effectuée.

## État source vérifié au 8 octobre 2026

- `backend/aman_api/main.py` conserve SQLite comme moteur local, mais reçoit maintenant une interface `Connection` et délègue l’ouverture, la fermeture, les transactions et les erreurs d’intégrité au module `backend/aman_api/database.py`.
- L’adaptateur SQLite garde le mode WAL, les clés étrangères, le mode d’accès aux lignes, les vérifications de permissions et `BEGIN IMMEDIATE`. Le SQL métier reste dans les routes et utilise le marqueur `?` ; l’extraction en dépôts métier et la définition du paramétrage portable ne sont donc pas terminées.
- Première extraction ciblée : les requêtes sources et les libellés historiques des agrégats de consentement résident dans `backend/aman_api/consent_metrics_repository.py`. Les routes continuent d’exécuter directement la majorité du SQL métier ; cette tranche ne démontre pas encore la portabilité complète.
- Le chargement des organisations, propriétés, activités et volumes du tableau de bord est maintenant regroupé dans `backend/aman_api/dashboard_repository.py`. La route garde la composition de la réponse et ses agrégats par organisation ; les autres routes restent à extraire.
- Les écritures, lectures et l’export borné du journal d’audit sont isolés dans `backend/aman_api/audit_repository.py` ; la création des identifiants, l’horodatage, les contrôles d’appartenance, l’encodage CSV et les en-têtes de réponse restent dans les routes/helpers applicatifs.
- Les migrations locales sont ordonnées et vérifiées par empreinte. `v0001` crée le schéma, `v0002` ajoute les colonnes des anciennes bases, `v0003` crée les buckets des limiteurs et `v0004` impose une seule politique publiée par propriété ; `backend/migrate_db.py` est la commande opérateur. Le démarrage HTTP vérifie le schéma et refuse une base non migrée. La CI actuelle couvre les parcours de régression sur sa base de test, mais n’a pas encore de fixtures dédiées pour chaque version historique de schéma.
- Les données sont réparties entre utilisateurs, organisations, appartenances, invitations, transferts de propriété, propriétés, politiques, sessions, événements d’audit, événements de consentement, rapports d’inventaire et buckets de limitation de débit.
- L’analyse statique interne du 8 octobre 2026 a confirmé que l’ingestion publique des événements de consentement n’a pas de quota cumulatif par propriété ou global. Les limites de débit et la purge à échéance ne bornent pas le volume conservé avant expiration ; ajouter des quotas, une réponse de saturation bornée, des alertes et une validation sous charge avant tout pilote exposé.
- Le numéro de version est calculé par `MAX(version)+1` sous verrou transactionnel de la propriété (`BEGIN IMMEDIATE` SQLite, verrou de ligne PostgreSQL) et chaque propriété a une unicité `(property_id, version)`. La publication verrouille la même propriété ; PostgreSQL l’adosse à un index unique partiel, maintenant aussi présent dans SQLite. Restent les contrôles multi-organisation au niveau applicatif et la validation des parcours contre une instance PostgreSQL réelle.
- Le mode production déclenche toujours une erreur explicite au chargement du module. L’API n’est pas déployable en banque dans son état courant.
- La tête de branche publiée est `4da0bba` sur `codex/alamane-b2b-readiness`. Elle comprend les évolutions du SDK Web et de la persistance des choix React Native ; aucun résultat CI ni test local n’a été vérifié sur cette révision. La CI réussie référencée dans le dossier fournisseur porte sur `08eb815` et ne doit pas être présentée comme une validation de `4da0bba`.
- Les cookies de session et CSRF portent `Secure` dans tous les environnements hors `development`. La démo locale HTTP reste possible ; une préproduction HTTPS ne dépend pas du nom de l’environnement pour protéger ses cookies.
- Une propriété étiquetée `production` impose désormais la publication à deux personnes, même si l’organisation a désactivé cette option ailleurs : l’auteur de la dernière modification du brouillon ne peut pas le publier. Cette règle protège le workflow; elle ne fournit ni isolation d’environnement, ni approbation juridique, ni aptitude de production.
- Un adaptateur PostgreSQL de préproduction est maintenant sélectionné par `AMAN_DATABASE_URL`, avec pool borné, exigence `sslmode=verify-full` pour les hôtes distants, migrations versionnées et index unique de politique publiée. Les limites de connexion, événements et invitations utilisent des buckets transactionnels partagés ; PostgreSQL exige un `AMAN_RATE_LIMIT_HASH_KEY` commun entre instances. `AMAN_MIGRATION_DATABASE_URL` permet une connexion opérateur directe distincte ; sur un hôte distant, les rôles explicites doivent différer et cibler la même base. Aucun service PostgreSQL externe n’a encore été configuré ou validé.
- La console multi-organisation affiche maintenant les décisions reçues sur 30 jours, la dernière décision encore retenue, les agrégats par finalité et version avec libellés FR/AR, et le CSV par propriété. L’export est un `POST` avec CSRF ; une demande et le nombre d’événements présents à cet instant sont inscrits au journal, sans prétendre confirmer la fin du téléchargement. Ces décisions sont déclarées par les SDK et ne démontrent pas l’affichage, l’identité du visiteur ou l’application effective du choix.
- `GET /v1/auth/me` renvoie le jeton CSRF après validation du cookie et de son condensat de session pour permettre à une console servie sur une origine distincte de l’API de reprendre ses mutations après rechargement. CORS doit toujours autoriser l’origine exacte et la console doit rester sur le même site que l’API pour que les cookies `SameSite=Strict` soient envoyés. Ce parcours n’a pas encore été validé sur un déploiement multi-origine réel.
- Les ajouts du tableau de bord, l’audit de demande d’export et l’initialisation CSRF multi-origine sont présents dans le checkout de développement ; ils n’ont pas encore été validés par la suite de tests ou contre PostgreSQL.

## Tranches de migration

### 1. Introduire un contrat de persistance — en cours

Un contrat `Connection` commun, le cycle de vie des transactions et la traduction des erreurs d’intégrité sont en place dans `backend/aman_api/database.py`. Continuer en extrayant les opérations SQL des routes vers des modules de persistance, définir la conversion des paramètres et lignes sans supposer SQLite, puis garder SQLite comme première implémentation.

**Critères de sortie :** aucun SQL métier ni détail de transaction spécifique à SQLite dans les routes; adaptateurs explicites et erreurs métier centralisées; les flux de console et SDK restent identiques.

### 2. Versionner le schéma — première tranche SQLite réalisée

Les migrations SQLite locales ordonnées et reproductibles sont ajoutées avec une commande opérateur séparée du serveur HTTP. Compléter les fixtures de migration depuis les anciennes versions supportées, formaliser la politique de compatibilité et prévoir une sauvegarde et une procédure de restauration de la base SQLite locale. Les migrations PostgreSQL resteront des migrations dédiées, testées indépendamment.

**Critères de sortie :** migration validée d’une base vide et de chaque schéma local supporté vers la dernière version; échec sûr en cas de version inconnue ou migration partielle; restauration documentée et vérifiée.

### 3. Ajouter PostgreSQL pour l’environnement de préproduction — adaptateur initial, validation en cours

Un pool de connexions borné pour l’API, TLS `verify-full` pour les connexions distantes, migrations versionnées, verrouillage de ligne de propriété, index unique des publications et limiteurs transactionnels partagés sont ajoutés. `AMAN_MIGRATION_DATABASE_URL` permet des migrations avec un compte opérateur direct distinct ; la sélection distante refuse les identifiants de rôle identiques. `AMAN_DATABASE_URL`, `AMAN_MIGRATION_DATABASE_URL` et `AMAN_RATE_LIMIT_HASH_KEY` doivent venir d’un gestionnaire de secrets à déployer ; aucun secret ni fournisseur n’est choisi dans le dépôt. Il reste à appliquer les droits DML minimaux en environnement, vérifier toutes les opérations sur un PostgreSQL réel et poursuivre les garanties des transferts/invitations. Garder SQLite comme valeur par défaut en développement.

Conserver l’allocation de version sous verrou de propriété et les contraintes uniques `(property_id, version)` et une politique publiée par propriété. Vérifier les niveaux de verrouillage requis pour la publication, le transfert de propriété et l’acceptation d’invitations. Vérifier que les limites de taille, le nettoyage des événements et les exports gardent le même comportement.

**Critères de sortie :** les migrations s’exécutent sur PostgreSQL vierge et depuis une version précédente; les parcours console et API fonctionnent avec deux organisations concurrentes; les conflits de publication et de version ne créent aucun état partiel.

### 4. Renforcer l’isolation et l’exploitation

Conserver les prédicats `org_id` dans chaque requête et ajouter une défense en profondeur au niveau de la base après avoir conçu correctement la propagation et la remise à zéro du contexte de tenant dans le pool. Ajouter supervision, alertes, sauvegardes chiffrées, restauration périodiquement démontrée, rotation des secrets et journalisation sans choix de consentement ni identifiant inutile.

**Critères de sortie :** tests d’isolation couvrant les lectures, mutations, exports, invitations et tâches asynchrones; restauration démontrée; limites et alertes supervisées.

### 5. Autoriser un pilote hébergé limité

Décider avec le client du mode dédié ou mutualisé, des connexions sortantes, de l’hébergement, des transferts, de la rétention et du modèle de preuve. Compléter MFA/SSO selon les exigences, livraison d’invitations, réponse aux incidents, SLA, revue contractuelle et pentest indépendant. Démarrer sur un domaine public non authentifié avec données synthétiques ou approuvées explicitement.

**Critères de sortie :** approbations sécurité, juridique, DPO, achats et opérations du client; procédure de retour arrière et de suppression vérifiée; aucune promesse générale de conformité ou de résidence avant validation documentée.

## Conditions CI et release à ajouter avec la migration

- Exécuter la suite sur SQLite et sur une version PostgreSQL déclarée, sans remplacer l’une par l’autre.
- Vérifier les migrations depuis le schéma vide et depuis chaque version encore supportée.
- Couvrir les invariants multi-organisation, publication à deux personnes, conflits de révision, unicité des événements et effacement à échéance.
- Lancer une vérification des permissions de base, TLS et présence des variables requises sans afficher leur valeur.
- Produire un artefact de release versionné et vérifiable séparément des APK debug et artefacts de prévisualisation actuels.

Les seuils de performance, disponibilité, région, sauvegarde et rétention restent à fixer avec un premier acheteur. Ce document est une proposition technique interne, pas une offre d’hébergement ni une attestation fournisseur.
