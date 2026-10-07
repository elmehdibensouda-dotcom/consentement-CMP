# ALAMANE — dossier de sécurité fournisseur (document de travail)

**État au 7 octobre 2026 · Usage interne pour préparer les échanges de qualification**

Ce document décrit l’état du prototype dans ce dépôt. Ce n’est ni une attestation de sécurité, ni une réponse approuvée à un questionnaire bancaire, ni un engagement contractuel. Il doit être actualisé et revu avec les responsables techniques, sécurité, juridiques et hébergement avant toute transmission à un prospect. Aucune donnée réelle de banque, d’employé ou de client ne doit être introduite dans cette version.

## Synthèse honnête

ALAMANE démontre localement une console multi-organisation, le contrôle d’accès par rôle, des politiques versionnées, une validation de publication à deux personnes, des SDK de démarrage et un journal d’administration. SQLite reste le choix local par défaut ; un adaptateur PostgreSQL de préproduction existe dans le code, mais n’a pas été validé sur une instance cible. Le projet bloque explicitement son démarrage avec `AMAN_ENVIRONMENT=production`. Cette version n’est pas apte à héberger une preuve de concept avec des données ou systèmes réels d’un établissement.

| Domaine évalué | État démontré dans le dépôt | Ce qu’un acheteur devra encore obtenir |
| --- | --- | --- |
| Isolation des organisations | Contrôles d’appartenance appliqués aux routes d’administration | Revue indépendante des contrôles d’accès, essais multi-tenant et modèle d’hébergement approuvé |
| Authentification | Mot de passe haché avec scrypt, session opaque, cookie HTTP-only, contrôle CSRF ; invitation à usage unique | MFA/SSO, récupération et désactivation opérées, politique d’accès privilégié et revue indépendante |
| Gouvernance | Rôles, transfert de propriété en deux étapes, audit administratif, révisions de brouillon, publication à deux personnes, révocation journalisée d’invitations et de transferts non acceptés | Centralisation et intégrité renforcée des journaux, alertes et procédures de revue |
| Données | Les événements de choix n’acceptent pas de compte visiteur ni d’identifiant persistant d’appareil ; purge locale selon la politique configurée | Analyse de traitement, suppression vérifiée, sauvegarde/restauration et cycle de vie contractuel |
| Plateforme | SQLite local par défaut ; adaptateur PostgreSQL de préproduction dans le code ; limiteurs persistés en base et CORS configuré par origine | Validation PostgreSQL sur une instance cible, clé HMAC commune pour plusieurs instances, proxy/WAF, déploiement, TLS, secrets, sauvegardes, supervision et reprise |
| Assurance | Aucun rapport de test indépendant ou certificat n’est fourni | Modèle de menace, analyse de risques, test d’intrusion, gestion des vulnérabilités et preuves de remédiation |
| SDK | Le workflow configuré compile la bibliothèque et l’exemple Android, le package Swift pour simulateur iOS, et emballe le paquet React Native ; le contrôle du SDK Web est syntaxique. Une compilation Babel locale du React Native a réussi sur l’arbre de travail actuel. | Aucune intégration dans une application cliente, matrice de compatibilité ou validation sur appareil cible ; l’APK de prévisualisation est signé avec une clé debug, les packages ne sont pas signés/publiés comme releases et aucune revue indépendante n’est fournie. La modification Android locale actuelle n’a pas été compilée ici. |

## Inventaire des traitements du prototype

| Flux | Données visibles dans le code | Limite à présenter |
| --- | --- | --- |
| Compte de console | Adresse e-mail, condensat de mot de passe, état du compte | Comptes de démonstration uniquement ; aucune fédération d’identité ou MFA |
| Invitation de membre | E-mail visé, rôle, condensat SHA-256 du jeton à usage unique, expiration de 72 heures ; lors de l’aperçu, organisation, rôle et e-mail partiellement masqué sont retournés au détenteur du jeton | Le jeton brut est remis à la console à la création puis transmis manuellement ; il n’est pas enregistré en clair en base. Le lien l’emporte dans le fragment, retiré de la barre d’adresse avant les appels API. Les aperçus (120/min) et acceptations (20/min) sont limités par source au moyen de compteurs en base et de clés HMAC, sous réserve d’une clé cohérente entre instances. Aucun service e-mail, accusé de remise, preuve d’identité de l’invité ni journalisation de livraison n’est configuré. |
| Administration | Identifiants organisation/propriété/politique, rôles, événements de configuration et publication | Journal conservé dans SQLite local ; pas d’export vers SIEM ni de stockage inviolable |
| Environnements de propriété | Étiquette développement, recette ou production ; HTTP loopback permis uniquement en développement | Métadonnée de pilotage, sans séparation des données, clés, politiques ou déploiements |
| Configuration d’origine Web | Origine scheme/hôte/port associée à une propriété Web | Contrôle de cohérence d’un import et autorisation CORS limitée aux routes publiques de cette propriété, sans cookies ; pas une preuve de propriété ou de contrôle du domaine |
| Politique publique | Informations que le client configure sur le responsable, contacts, finalités, catégories, destinataires, transferts et références | Ces contenus peuvent être des données confidentielles du client ; ne pas saisir de valeurs réelles dans la démo |
| Choix visiteur facultatif | Identifiant aléatoire d’événement, version de politique, canal, décision par finalité, heure de réception | Événement déclaré par le client SDK ; les membres peuvent exporter un CSV des événements retenus. Le Web est filtré par `Origin`/propriété et les appels natifs ne portent pas d’`Origin`, mais il n’existe pas de preuve d’identité, de rendu de l’écran, d’authenticité de l’application ou de consentement juridiquement valide |
| Inventaire Web manuel | Page et origine, chemins de ressources sans paramètres, noms de cookies accessibles, catégories attribuées manuellement, date du scan et membre importateur | Aucun envoi automatique depuis le scanner ; l’import explicite conserve jusqu’à 20 rapports par propriété dans SQLite local. L’API compare l’origine déclarée au paramétrage, sans attester la provenance réelle du scan. Les valeurs de cookies ne sont pas lues ; les cookies HttpOnly restent invisibles. Suppression manuelle disponible, mais aucun cycle d’effacement opératoire des sauvegardes n’existe. |
| Limitation de débit | Compteurs transactionnels en base. Le code limite les connexions à 20 échecs par source sur 10 minutes, les événements à 120 par source et 6 000 par propriété sur 60 secondes, les aperçus d’invitation à 120/minute et les acceptations à 20/minute par source. Les identifiants source/propriété sont HMACés, pas stockés en clair. | En PostgreSQL, `AMAN_RATE_LIMIT_HASH_KEY` d’au moins 32 octets est obligatoire et doit être identique entre instances. En SQLite, la clé par défaut est propre au processus ; aucune garantie multi-instance n’est démontrée. Les limites du reverse proxy/WAF et les essais sur déploiement cible restent à définir. |

La durée de conservation des événements reçus est dérivée de la politique publiée et une tâche locale effectue la purge périodique. Les imports d’inventaire gardent au plus 20 rapports par propriété jusqu’à leur suppression ou dépassement de cette limite. Ce code ne démontre pas une suppression opérationnelle de sauvegardes, de journaux d’infrastructure ou de systèmes futurs.

## Éléments de preuve disponibles

- Architecture locale et limites : [ARCHITECTURE.md](./ARCHITECTURE.md) et [backend/README.md](./backend/README.md).
- Contrôles d’accès, sessions, CSRF, politiques, journal et stockage : `backend/aman_api/main.py`.
- Format de politique partagé : [schemas/consent-policy.schema.json](./schemas/consent-policy.schema.json).
- Capacités et limites des canaux : [guide iOS](./mobile/ios/README.md), [guide Android](./mobile/android/README.md) et `aman-cmp.js`.
- Le workflow [Product validation](./.github/workflows/product-validation.yml) configure la compilation Android/iOS et l’emballage React Native ; sa définition n’est pas une preuve qu’une exécution a validé le code local actuel.
- La [CI privée du 6 octobre 2026](https://github.com/elmehdibensouda-dotcom/alamane-consent/actions/runs/37501530814) a réussi sur la révision distante de cette date la compilation Android/iOS ; elle ne constitue pas une validation de sécurité, d’intégration client ou de release signée, et ne couvre pas les changements SDK locaux non poussés.
- La [prévisualisation mobile manuelle](https://github.com/elmehdibensouda-dotcom/alamane-consent/actions/runs/37487329772) a joint un AAR Android, un APK debug et le tarball React Native au commit indiqué dans son manifeste ; ces artefacts temporaires ne sont pas des releases de production.
- Le commit local `ebdc5e9` corrige le finding de limitation de débit du scan historique du 7 octobre ; la suite backend locale a passé 17 tests. Le rapport de scan original reste attaché à la révision pré-correction `0066e2a` et ne décrit pas l’état post-correction.
- Les vérifications locales de compilation et de syntaxe ne sont pas des tests de sécurité, une homologation ou un test d’intrusion. Les modifications mobiles non commitées de ce dossier ne sont pas présentes sur GitHub.

## Questions auxquelles ne pas répondre par supposition

Avant de proposer un environnement de pilote, obtenir du prospect ses exigences écrites sur :

1. Hébergement autorisé, résidence des données, transferts, sous-traitants et modèle SaaS / cloud privé / installation dédiée.
2. Identité : SSO/SAML/OIDC, MFA, provisionnement, rôles, durée de session et exigences de comptes administrateurs.
3. Sécurité : chiffrement en transit/au repos, gestion et rotation des secrets, segmentation, pare-feu applicatif, limites de débit et scans de vulnérabilités.
4. Exploitation : sauvegardes, restauration, RPO/RTO, disponibilité, supervision, alertes, réponse aux incidents et notification.
5. Assurance : questionnaire fournisseur, test d’intrusion, SBOM, gestion CVE, preuves d’audit et certificats attendus.
6. Données : catégories à traiter, durée de conservation, demandes de droits, export, effacement, sous-traitance et critères de fin de contrat.
7. SDK : domaines et applications autorisés, mécanisme d’approbation, CSP, compatibilité, signature, inventaire des SDK tiers et procédure de retrait.

Un domaine public non authentifié peut réduire le périmètre fonctionnel d’un pilote, mais ne supprime pas les exigences de sécurité ou de traitement des données du fournisseur.

## Conditions minimales avant un pilote réel

- Décision écrite sur le modèle d’hébergement et les responsabilités de traitement, revue par le prospect et conseil compétent.
- Architecture cible et flux de données approuvés ; secrets hors du code et des variables non protégées.
- Base de données et migrations opérables, chiffrement conforme au besoin, sauvegarde/restauration éprouvée et suppression documentée.
- Authentification et autorisations conformes aux exigences du prospect ; limitation de débit, alertes, journalisation et procédure d’incident opérées.
- Revue de code et dépendances, tests de sécurité indépendants, gestion des constats et preuves disponibles.
- SDK compilés, signés et livrés depuis un dépôt approuvé ; intégration sur un environnement de test contrôlé, avec révocation et retrait testés.
- Contrats, notice et durées relus par les responsables compétents ; critères de succès et de sortie de POC convenus par écrit.

Tant que ces conditions ne sont pas remplies et vérifiées pour le déploiement retenu, la démo locale reste synthétique et le serveur de développement ne doit pas recevoir de données réelles.
