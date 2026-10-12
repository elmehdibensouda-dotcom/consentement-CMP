# ALAMANE — kit de test Web dans l’environnement du client

**Candidat de pilote isolé · canal Web · version source identifiée par commit**

Ce kit est destiné à une recette technique avec des comptes et données fictifs. Il permet au client d’héberger l’API/console dans son environnement de préproduction et d’intégrer le SDK Web dans une seule route de test autorisée. Ce n’est ni une release de production, ni un service exploité par ALAMANE, ni une garantie de conformité.

## État de remise

Ne remettre le paquet qu’après revue du correctif sécurité en cours, revue du contenu exact et accord sur le périmètre avec le client. Le paquet final doit être produit depuis un commit examiné, sans modification locale, et porter son SHA Git ainsi qu’un manifeste SHA-256. Le manifeste détecte une altération après empaquetage ; il ne signe pas la release et n’atteste pas sa provenance.

La version actuelle est une préproduction limitée à `AMAN_ENVIRONMENT=staging`. Le serveur refuse volontairement `production`. Le client héberge et administre tous les composants dans son environnement ; ALAMANE ne reçoit pas les données de test.

## Ce que contient le transfert Web

- Le SDK Web `aman-cmp.js` et ses scripts fictifs de démonstration.
- La console/API et leur contexte de build Docker.
- Les fichiers de configuration d’exemple pour la préproduction et la migration PostgreSQL.
- Les guides d’intégration, de sécurité fournisseur et de retrait.
- `BUILD-INFO.txt` avec le commit source et `SHA256SUMS` avec les empreintes des fichiers.

Le transfert n’inclut aucun mot de passe, clé HMAC, URL de base, compte client ou donnée de visiteur. Il n’inclut pas les SDK mobiles, les services cloud, un certificat TLS, une configuration de pare-feu, une sauvegarde, une supervision, un SLA ou une release signée.

## Conditions d’entrée obligatoires

Avant l’installation, le client désigne les propriétaires et approuve par écrit :

1. Une seule route et une seule origine de recette, la fenêtre de test, les testeurs et les critères d’arrêt.
2. Une infrastructure isolée de production, une URL API HTTPS, un reverse proxy/TLS et des règles réseau sous le contrôle du client.
3. Une base PostgreSQL dédiée, les rôles DBA/migration/runtime et le mécanisme de sauvegarde/restauration correspondant à son processus de recette.
4. Les personnes qui administreront la console et les exigences sécurité, DPO/juridique, architecture et achats applicables au test.
5. Des comptes et données synthétiques. Ne pas utiliser d’identifiant assuré, contrat, sinistre, donnée de santé, cookie de production ou secret client.
6. Le texte de notice, les finalités et les états initiaux fictifs de la politique de test. Aucun contenu d’exemple ne doit être présenté comme une validation juridique.

Si l’environnement ne peut pas respecter ces conditions, garder la démonstration sur la maquette locale et ne pas brancher l’origine du client.

## Déployer le service de préproduction

Les commandes suivantes sont un modèle à adapter par l’équipe plateforme du client. Elles ne remplacent pas sa revue d’architecture ni son processus de changement. Ne démarrer le service qu’après approbation de l’environnement et des secrets.

1. Vérifier `BUILD-INFO.txt` et `SHA256SUMS`. Conserver le paquet dans le dépôt d’artefacts approuvé par le client.
2. Construire l’image depuis le répertoire `source/` du kit :

   ```sh
   docker build -t alamane-api:pilot-<commit-court> source/
   ```

3. Créer les secrets dans le coffre du client et les monter au runtime sous les chemins référencés par `ops/container/staging.env.example` et `ops/container/staging-migrate.env.example`. Les secrets requis sont :
   - URL de base PostgreSQL pour le rôle API ;
   - URL de la même base pour le rôle migration/opérateur ;
   - clé HMAC aléatoire d’au moins 32 octets, identique pour toutes les instances de cette préproduction.

   Pour PostgreSQL distant, utiliser TLS avec vérification complète du certificat (`sslmode=verify-full`). Ne pas mettre les valeurs secrètes dans le dépôt, l’image, une commande shell copiée dans un ticket ou un fichier d’exemple.

4. Depuis un poste opérateur autorisé, exécuter les migrations avec le profil migration et le rôle opérateur, puis appliquer après revue DBA le modèle de privilèges `ops/postgres-runtime-privileges.sql` au rôle API. La commande `migrate` utilise les deux URL fournies par les secrets. Ne monter le secret opérateur que pour cette opération ponctuelle.
5. Créer le premier administrateur avec la commande ponctuelle `create-admin`, depuis une session contrôlée. Le mot de passe est saisi de façon interactive ; ne pas le placer dans une variable shell ou dans un ticket.
6. Démarrer l’image avec `ops/container/staging.env.example`, qui ne monte que les secrets runtime, derrière le reverse proxy TLS approuvé. Le port applicatif ne doit pas être exposé directement à Internet. Vérifier `/health/ready` depuis le réseau de supervision convenu ; cette route confirme la disponibilité de PostgreSQL et du schéma, pas l’aptitude de production.
7. Dans la console, créer une organisation fictive, une propriété Web de recette et un brouillon de politique. Les migrations de démo/seed ne sont autorisées qu’en développement ; ne pas les contourner en préproduction. Faire relire et publier la politique selon le processus à deux personnes convenu.

Les profils d’environnement sont des exemples : le client doit les copier hors du dépôt, remplacer les origines d’exemple et les chemins de secrets selon sa plateforme, puis vérifier les valeurs effectives avant démarrage. Le guide détaillé du conteneur et ses limites se trouve dans `documentation/container/README.md`.

## Intégrer dans une route Web de recette

1. Héberger `source/aman-cmp.js` sur le domaine choisi par le client, idéalement sur le même site que la route de test. L’équipe cliente contrôle les fichiers et le déploiement.
2. Déclarer dans ALAMANE l’origine exacte autorisée pour la propriété Web (schéma, hôte et port, sans chemin). Déclarer séparément l’origine de la console dans `AMAN_CORS_ORIGINS` si l’organisation l’héberge sur une autre origine. Une origine enregistrée n’est pas une preuve du contrôle du domaine.
3. Copier l’extrait produit pour la propriété et remplacer l’URL d’API par l’URL HTTPS de recette du client. Garder la collecte d’événements désactivée. Ajouter les directives CSP minimales revues par la sécurité cliente, dont `connect-src` pour l’API et le nonce par réponse si la politique du site l’exige.
4. Désactiver l’auto-initialisation des technologies optionnelles de la route et configurer leurs déclencheurs pour attendre le choix applicable. N’utiliser que des scripts de test autorisés. Le client relie chaque finalité à l’API de démarrage et d’arrêt de ses technologies ; ALAMANE ne peut pas annuler une requête déjà envoyée.
5. Ajouter le script ALAMANE uniquement sur cette route. Ne pas déployer une balise globale au niveau du site ou du gestionnaire de tags pour ce pilote.

Les détails d’extrait, de CSP et de retrait sont dans `documentation/SDK_WEB.md`. L’équipe cliente doit relire puis appliquer le changement par son propre mécanisme de livraison.

## Scénarios d’acceptation proposés

Convenir avec le client des versions de navigateur, appareils, technologies et preuves avant le test. Exécuter uniquement sur la route autorisée avec des comptes fictifs.

| Scénario | Résultat à observer |
| --- | --- |
| Première visite sans choix | Le panneau correspond à la politique approuvée ; aucune technologie facultative testée ne démarre avant l’état applicable. |
| Tout accepter, tout refuser, personnaliser | L’interface et les états effectifs par finalité suivent la décision ; les scripts fictifs ou intégrations expressément retenues reflètent ces états. |
| Rouvrir puis retirer un choix | Les préférences restent modifiables ; les mécanismes d’arrêt du fournisseur sont observés côté client. |
| Changer la langue | Français, arabe RTL et textes de notice sont lisibles dans la route intégrée. |
| Publier une nouvelle version | L’ancien choix n’est pas présenté comme valable pour la nouvelle version ; le visiteur est invité à revoir ses préférences selon le comportement convenu. |
| Politique absente ou erreur réseau | Sans politique valide, les technologies optionnelles restent arrêtées ; documenter séparément la politique valide en cache et une erreur temporaire. |
| Retirer l’intégration | Après retour arrière, la balise et les déclencheurs ajoutés pour le pilote sont absents de la route et les requêtes optionnelles ne partent plus. |

Les preuves recueillies par le client peuvent inclure les versions logicielles, captures expurgées, observations réseau et résultat du retour arrière. Ne pas collecter de contenu de session ou d’identifiant individuel. Les événements de décision centralisés restent désactivés, sauf accord distinct et écrit du client après revue du modèle de collecte.

Un événement remonté par le SDK est une déclaration technique du client ; il ne prouve ni l’identité du visiteur, ni l’affichage de l’interface, ni l’application réelle du choix. La console ne doit pas être présentée comme un registre de preuve inviolable.

## Retour arrière et clôture

Le client retire le script et les appels ajoutés uniquement sur la route de recette, annule les modifications de balises/CSP devenues inutiles, restaure la route précédente et vérifie les requêtes réseau. La procédure détaillée est dans `documentation/SDK_WEB.md`, section « Retour arrière ».

À la clôture, le client décide selon son processus de conserver ou supprimer la base et les secrets de la préproduction, révoque les comptes de test devenus inutiles et consigne les écarts, limites fournisseurs, résultats et décision de suite. Aucune donnée réelle ne doit être conservée dans ce kit.

## Éléments non fournis / non démontrés

- Aucune instance ALAMANE hébergée, adresse publique ou compte client n’est inclus.
- Aucun déploiement multi-tenant ou de production n’est autorisé par ce paquet ; le serveur refuse le mode `production`.
- SSO/MFA, sauvegarde/restauration testée, observabilité/alertes, réponse aux incidents, SLA, test d’intrusion indépendant et release signée ne sont pas fournis par le kit.
- L’intégration dans le site client, l’accessibilité du parcours dans ses composants, les APIs d’arrêt de ses fournisseurs et l’acceptation de ses équipes restent à valider dans son environnement.
- ALAMANE est un outil de configuration ; il ne certifie pas la conformité de l’organisation.
