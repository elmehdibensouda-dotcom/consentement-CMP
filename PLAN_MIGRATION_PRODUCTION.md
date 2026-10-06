# Plan de transition vers un service hébergeable

**État :** plan d’ingénierie interne, 6 octobre 2026  
**But :** préparer un pilote entreprise sans présenter le prototype local comme apte à recevoir des données réelles.

## Décision d’architecture proposée

Conserver SQLite pour le développement local et retenir PostgreSQL comme cible de persistance du service hébergé. Ne pas choisir dans ce document un fournisseur cloud, une région d’hébergement, un modèle SaaS mutualisé ou dédié : ces choix dépendent des exigences de sécurité, d’hébergement, de transfert et d’achat des premiers clients.

Le serveur continuera de refuser `AMAN_ENVIRONMENT=production` jusqu’à ce que les critères de mise en service ci-dessous soient satisfaits et qu’une revue sécurité distincte ait été effectuée.

## État source vérifié

- `backend/aman_api/main.py` ouvre actuellement une base SQLite locale, active les clés étrangères, le mode WAL et un `row_factory` SQLite.
- `init_db()` crée les tables et applique les évolutions du schéma au démarrage à l’aide de `CREATE TABLE IF NOT EXISTS`, `PRAGMA table_info` et `ALTER TABLE`. Il n’existe pas de journal de migrations versionné.
- Les routes utilisent directement `conn.execute(...)` avec des paramètres `?`. Les transactions d’écriture commencent par `BEGIN IMMEDIATE`, propre à SQLite.
- Les données sont réparties entre utilisateurs, organisations, appartenances, invitations, transferts de propriété, propriétés, politiques, sessions, événements d’audit, événements de consentement et rapports d’inventaire.
- Plusieurs invariants reposent sur SQLite et le code applicatif : version suivante calculée par `MAX(version)+1`, une seule politique publiée par propriété, contrôle d’accès à chaque route et limite de débit stockée en mémoire du processus.
- Le mode production déclenche une erreur explicite au chargement du module. L’API n’est pas déployable en banque dans son état courant.

## Tranches de migration

### 1. Introduire un contrat de persistance

Extraire les fonctions d’accès aux données et leurs transactions de `main.py`. Conserver le comportement SQLite actuel derrière ce contrat avant d’ajouter un deuxième moteur. Éliminer les références au type `sqlite3.Connection` des fonctions métier et centraliser la traduction des erreurs d’intégrité.

**Critères de sortie :** aucun SQL métier ni détail de transaction spécifique à SQLite hors de l’adaptateur SQLite; les flux de console et SDK restent identiques.

### 2. Versionner le schéma

Créer des migrations ordonnées et reproductibles, utilisables depuis une commande opérateur séparée du démarrage HTTP. Représenter explicitement contraintes, clés étrangères, index, valeurs par défaut et évolution des politiques. Prévoir une migration de sauvegarde et une procédure de restauration de la base SQLite locale.

**Critères de sortie :** migration d’une base vide et d’une base locale existante vers le dernier schéma; échec sûr en cas de version inconnue ou migration partielle.

### 3. Ajouter PostgreSQL pour l’environnement de préproduction

Ajouter un pool de connexions borné, TLS vérifié pour les connexions distantes et une configuration injectée depuis un gestionnaire de secrets. Séparer l’identité d’exécution de l’identité de migration. Ne jamais journaliser l’URL de connexion. Garder SQLite comme valeur par défaut en développement.

Pour PostgreSQL, remplacer le calcul concurrent `MAX(version)+1` par une allocation transactionnelle. Garantir l’unicité d’une politique publiée par propriété en base, et utiliser les niveaux de verrouillage requis pour la publication, le transfert de propriété et l’acceptation d’invitations. Vérifier que les limites de taille, le nettoyage des événements et les exports gardent le même comportement.

**Critères de sortie :** les migrations s’exécutent sur PostgreSQL vierge et depuis une version précédente; les parcours console et API fonctionnent avec deux organisations concurrentes; les conflits de publication et de version ne créent aucun état partiel.

### 4. Renforcer l’isolation et l’exploitation

Conserver les prédicats `org_id` dans chaque requête et ajouter une défense en profondeur au niveau de la base après avoir conçu correctement la propagation et la remise à zéro du contexte de tenant dans le pool. Externaliser les limiteurs de débit et les tâches de purge. Ajouter supervision, alertes, sauvegardes chiffrées, restauration périodiquement démontrée, rotation des secrets et journalisation sans choix de consentement ni identifiant inutile.

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
