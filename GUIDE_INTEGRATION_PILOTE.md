# ALAMANE — guide d’intégration pour un pilote

**État :** guide d’un prototype local, pas une procédure de déploiement en production. Les exemples utilisent des identifiants et des domaines fictifs. Ne pas y saisir de donnée bancaire, de secret ou de donnée réelle de visiteur.

## Choisir son intégration

| Application à raccorder | SDK | État de distribution |
| --- | --- | --- |
| Site Web | `aman-cmp.js` | Fichier présent dans le dépôt ; un lancement manuel du workflow CI est configuré pour joindre un aperçu temporaire vérifiable. À héberger par l’équipe cliente sur un domaine qu’elle contrôle. |
| Application React Native | `mobile/react-native` | Source installable depuis un checkout, ou tarball privé issu d’une exécution manuelle GitHub Actions (conservé 14 jours). Pas de publication npm. |
| Application iOS native | `mobile/ios` | Package Swift depuis le dépôt privé ou un checkout local ; un lancement manuel du workflow CI est configuré pour joindre une archive source temporaire vérifiable. Pas de release signée ou publiée. |
| Application Android native | `mobile/android` | Module Gradle depuis un checkout local ; un aperçu avec dépôt Maven local (AAR, POM, métadonnées et sources) est disponible temporairement. Pas de release signée ni de dépôt Maven distant. |

Les trois aperçus destinés à une évaluation ont été générés par le [lancement manuel GitHub Actions du 8 octobre 2026](https://github.com/elmehdibensouda-dotcom/alamane-consent/actions/runs/37767815026) et sont conservés jusqu’au 22 octobre 2026 : sources Web, sources Swift Package iOS, dépôt Maven Android avec AAR/POM/métadonnées/sources, APK de démonstration, tarball React Native et SBOM CycloneDX React Native. Les SHA-256 des manifestes des aperçus ont été vérifiés et un bundle de transfert commun a été préparé localement pour le commit `d8523b7da5ce15d984a74bfeb4023634047e5055`. Le manifeste protège l’intégrité des fichiers après téléchargement, pas leur origine ; l’APK utilise une clé debug et aucun artefact n’est une release signée ou de production.

Les SDK mobiles sont des bases de pilote. Aucun n’a encore été intégré et validé dans une application cliente. La compilation ou l’emballage en CI ne constitue pas une validation sur les appareils et versions du client.

### Distribution envisagée pour un pilote entreprise

Hypothèse à confirmer avec l’acheteur : après revue et gel d’une version, remettre un bundle horodaté avec commit source, manifeste d’empreintes et inventaire de composants pour import dans le dépôt d’artefacts approuvé par le client. Ce dépôt GitHub est privé et les aperçus CI actuels expirent après 14 jours ; ils ne constituent pas une distribution client durable. Aucun accès client au dépôt ALAMANE, aucune release publique et aucune publication npm/Maven n’ont été mis en place. Les empreintes détectent une altération après création du bundle, mais ne remplacent ni une signature de release ni une attestation de provenance. Les exigences de signature, SBOM, approbation et conservation sont à convenir avec la sécurité du client avant transfert.

Quand les trois artefacts temporaires d’un même commit sont disponibles localement, `scripts/prepare-sdk-handoff.sh` les vérifie puis crée un seul paquet de transfert identifié. Il exige un checkout propre du même commit, refuse les commits différents, les fichiers requis absents et l’écrasement d’une archive existante, et inclut les guides de chaque plateforme. Le bundle Android contient le dépôt Maven local (AAR, POM, métadonnées Gradle et sources) ainsi que l’APK d’exemple debug ; seul le dépôt Maven est destiné à une éventuelle importation cliente après revue. Le libellé fourni identifie le transfert ; il ne change pas la version des SDK et ne constitue pas une release. Le script ne compile ni ne signe les SDK ; le paquet conserve les limites listées dans `HANDOFF.md`. Utiliser uniquement les artefacts d’un commit examiné et transmettre le paquet selon le processus approuvé par le client.

Exemple après avoir téléchargé et extrait les trois artefacts dans des dossiers distincts :

```sh
scripts/prepare-sdk-handoff.sh pilote-banque-01 \
  /chemin/alamane-web-preview-COMMIT \
  /chemin/alamane-mobile-preview-COMMIT \
  /chemin/alamane-ios-preview-COMMIT \
  .local/sdk-handoffs
```

L’archive `alamane-sdk-pilot-pilote-banque-01-COMMIT.tar.gz` et son fichier `.sha256` sont créés dans `.local/sdk-handoffs`. Vérifier le téléchargement depuis ce dossier avec `shasum -a 256 -c alamane-sdk-pilot-pilote-banque-01-COMMIT.tar.gz.sha256` sur macOS ou `sha256sum -c alamane-sdk-pilot-pilote-banque-01-COMMIT.tar.gz.sha256` sur Linux. Après extraction, vérifier également le manifeste `SHA256SUMS` à la racine du paquet. Ce dossier est ignoré par Git ; ne déposer le paquet que dans un stockage approuvé par l’acheteur.

## Préparer la propriété dans la console

1. Créer ou sélectionner l’organisation du pilote, puis une propriété avec le canal correspondant (`web`, `ios` ou `android`). Pour une application React Native multiplateforme, créer une propriété iOS et une propriété Android ; le SDK choisit l’identifiant et la politique du canal natif correspondant. L’étiquette d’environnement sert à la gouvernance ; elle ne sépare pas les données ni les déploiements.
2. Renseigner les finalités, leur classification, la règle de choix préalable (`consentRequired`), l’état avant le premier choix (`initiallyEnabled`) et les textes français/arabe. Faire valider ces paramètres, les traductions, les durées et le traitement par les responsables du client et leurs conseils.
3. Publier une politique pour cette propriété. Une propriété étiquetée production exige une publication par une autre personne que celle ayant modifié le brouillon.
4. Copier l’identifiant de propriété généré par la console. Il sert à sélectionner une configuration publique et n’est pas un secret.
5. Utiliser une URL d’API HTTPS pour tout hôte distant. HTTP est accepté seulement pour `localhost`, `127.0.0.1` et `::1` dans les démonstrations locales.

L’origine déclarée pour une propriété Web autorise uniquement les routes publiques de cette propriété ; elle ne prouve pas le contrôle du domaine. `AMAN_CORS_ORIGINS` sert à la console et aux appels avec cookies. Pour les détails de configuration, voir le [guide de démarrage](./README.md#démarrer-la-démo-connectée) et le [contrat de politique](./schemas/consent-policy.schema.json).

## Intégrer la plateforme choisie

### Web

Héberger `aman-cmp.js` sur un domaine contrôlé par le client, puis ajouter le script avec l’URL d’API et l’identifiant de propriété. Le [guide d’intégration Web](./SDK_WEB.md) contient l’extrait complet, un exemple CSP avec nonce et une procédure de retour arrière. Les scripts facultatifs doivent être balisés et ne démarrer qu’après l’état applicable. `AmanCMP.registerPurposeHandler` permet de raccorder l’arrêt prévu par un fournisseur. Un script déjà exécuté ne peut pas être universellement déchargé ; le comportement dépend de l’API fournisseur. La CSP et le retour arrière doivent être relus puis testés par l’équipe cliente dans la route autorisée avant la fenêtre d’intervention.

### React Native

Prérequis documentés : React 18+, React Native 0.72+ et un adaptateur de stockage fourni par l’application (le guide utilise AsyncStorage). Installer le dossier source depuis un checkout local, ou demander l’accès à l’artefact privé d’une exécution manuelle du workflow ; vérifier `SHA256SUMS` et `BUILD-INFO.txt` après téléchargement. Le paquet n’est pas sur npm. Le guide contient les réglages Metro, le composant et le raccordement des finalités : [mobile/react-native/README.md](./mobile/react-native/README.md).

### iOS natif

Prérequis documentés : iOS 16+ et Swift 5.9+. Ajouter le package Swift depuis le dépôt privé ou utiliser le chemin local `mobile/ios`, puis sélectionner le produit `AmanConsent`. L’application doit garder les SDK facultatifs désactivés jusqu’à une politique valide et relier chaque finalité à ses propres appels de démarrage/arrêt. Exemple SwiftUI et détails du cycle de vie : [mobile/ios/README.md](./mobile/ios/README.md).

### Android natif

Prérequis documentés : Android API 23+, JDK 17, Android SDK 36 et Gradle 9.6 installé/configuré. Le dépôt ne contient pas de Gradle Wrapper. Intégrer le module `aman-consent` depuis le checkout ; l’AAR d’aperçu est disponible uniquement via le workflow manuel. Exemple Kotlin, règles de cycle de vie et détails de build : [mobile/android/README.md](./mobile/android/README.md).

## Règles communes côté application

- `required` signifie que la finalité est classée nécessaire par le responsable et reste active ; `consentRequired` indique séparément si un choix positif doit précéder son activation ; `initiallyEnabled` détermine explicitement son état avant un choix valide. ALAMANE ne déduit pas un état activé de `consentRequired: false`. Les anciennes politiques sans `initiallyEnabled` démarrent leurs finalités optionnelles désactivées ; une finalité `required` reste active. Le responsable et son conseil doivent valider la classification et le comportement applicable avant publication.
- Configurer les SDK tiers facultatifs sans auto-initialisation ni auto-collecte. L’application hôte les démarre seulement si la finalité concernée est effective ; un rappel après le démarrage de l’application ne prévient pas un envoi initial.
- En l’absence de politique valide, laisser les finalités optionnelles désactivées et proposer une reprise. Les SDK utilisent leur dernière politique valide en cache ou en mémoire seulement pour une erreur réseau ou une réponse temporaire ; une politique absente ou invalide invalide le choix applicable.
- Le SDK Web charge la politique à l’initialisation, puis la revalide toutes les cinq minutes et au retour de l’onglet au premier plan (avec au moins une minute entre deux vérifications). Une nouvelle version invalide le choix associé à l’ancienne version, affiche à nouveau le panneau et émet `aman:policy-updated`. Si aucune politique valide ne peut être obtenue, les finalités optionnelles restent fermées et `aman:policy-unavailable` est émis. `AmanCMP.registerPurposeHandler` permet de raccorder ces changements à l’arrêt fournisseur, sans pouvoir annuler une donnée déjà transmise. React Native recharge la politique au retour de l’application au premier plan ; pour iOS et Android natifs, l’application hôte doit reprendre le chargement et transmettre la politique avec `updatePolicy(...)` au retour au premier plan.
- L’application Web doit raccorder l’état effectif à son propre cycle de vie. `AmanCMP.registerPurposeHandler(id, start)` appelle le démarrage lors de l’activation et la fonction de nettoyage renvoyée lors du retrait ; `aman:consent-update` reste disponible pour les intégrations GTM ou événementielles. Choisir une seule voie de démarrage par finalité et appeler les fonctions d’arrêt documentées par les fournisseurs réellement utilisés.
- En React Native, iOS et Android, `registerPurposeHandler` fournit un raccordement par finalité avec démarrage, nettoyage et signalement facultatif d’erreur ; l’application doit toujours désactiver l’auto-initialisation des SDK facultatifs et retirer l’inscription quand elle n’en a plus la charge. iOS et Android conservent aussi leurs listeners d’état effectif pour une orchestration personnalisée. Utiliser une seule voie de raccordement pour chaque SDK tiers.

  ```js
  document.addEventListener('aman:consent-update', ({ detail }) => {
    if (detail.propertyId === 'PROPERTY_ID') reconcileOptionalSdks(detail.purposes);
  });

  document.addEventListener('aman:policy-unavailable', ({ detail }) => {
    if (detail.propertyId === 'PROPERTY_ID') stopOptionalSdks();
  });
  ```
- Conserver le choix localement selon le stockage de la plateforme. Les SDK mobiles ne synchronisent pas automatiquement les décisions entre appareils.
- La transmission centrale des décisions est distincte de l’affichage et désactivée par défaut sur le Web. Les applications natives doivent appeler explicitement la méthode d’envoi. Ne l’activer qu’après validation du texte d’information et du modèle de collecte par le client.
- Un événement transmis est une déclaration du SDK : il ne prouve pas l’identité du visiteur, l’affichage de l’interface ou l’application effective de son choix. L’application hôte reste responsable des SDK tiers déjà initialisés et de leur capacité de retrait.

## Matrice de validation avec l’équipe cliente

Utiliser cette matrice pour convenir des scénarios et des preuves avant une POC. Les comportements ci-dessous décrivent les attentes produit ; ils ne signifient pas qu’une version a déjà été validée dans l’application ou l’infrastructure du client.

| Scénario | Web | iOS / Android / React Native | Preuve à recueillir avec le client |
| --- | --- | --- | --- |
| Première visite sans choix | Afficher le parcours selon `initiallyEnabled` validé ; garder bloquées les balises optionnelles qui sont raccordées. | Afficher le panneau ; désactiver l’auto-initialisation des SDK tiers et appliquer l’état de départ par finalité. | Captures d’écran et observation des requêtes réseau avant toute action. |
| Accepter, refuser, personnaliser | Enregistrer le choix local, mettre à jour les balises gérées et ouvrir à nouveau le centre de préférences. | Enregistrer le choix dans le stockage privé de l’app, notifier les gestionnaires et permettre de rouvrir le panneau. | Cas d’acceptation, de refus et de sélection partielle ; état effectif par finalité. |
| Retirer un choix | Rappeler le nettoyage fournisseur raccordé ; vérifier l’absence de nouvelles requêtes optionnelles. | Exécuter le nettoyage retourné par `registerPurposeHandler` et vérifier le comportement réel du fournisseur. | Résultat observé après retrait ; noter toute API fournisseur incapable d’arrêter un SDK déjà initialisé. |
| Nouvelle version de politique | Invalider le choix de l’ancienne version et demander un nouveau choix ; les gestionnaires actifs sont réconciliés avec le nouveau contexte. | Recharger la politique selon le cycle de vie du canal, réinitialiser le choix devenu obsolète et rappeler les gestionnaires actifs avec le nouveau contexte. | Numéro de version avant/après, parcours affiché, démarrages et nettoyages observés. |
| Politique absente ou réseau indisponible | Une politique absente/invalide ferme les finalités optionnelles ; une erreur temporaire peut utiliser une politique valide en cache. | Garder les finalités optionnelles fermées si aucune politique valide n’est disponible ; une politique valide en cache peut servir lors d’une erreur temporaire. | Résultats séparés pour `404`, erreur temporaire, cache valide et cache absent ; confirmer les SDK qui restent actifs/arrêtés. |
| Expiration et stockage indisponible | Réévaluer le choix à l’expiration ; signaler si le stockage durable n’a pas fonctionné. | Réévaluer à l’expiration et montrer l’avertissement si le choix ne peut rester qu’en mémoire. | Durée configurée, état après expiration, redémarrage de l’appareil et comportement après échec d’écriture. |
| Langue, accessibilité et canal | Vérifier FR/AR, RTL, clavier et lecteurs d’écran dans les navigateurs retenus. | Vérifier FR/AR, RTL, VoiceOver/TalkBack et tailles d’écran sur les appareils retenus ; pour React Native, vérifier les deux propriétés natives. | Versions appareil/OS/navigateur, résultats d’accessibilité, identifiants de propriété et écarts consignés. |
| Transmission facultative | Vérifier que `collectDecisionEvents` reste désactivé tant qu’il n’est pas explicitement approuvé. | Vérifier qu’aucun `recordDecision` n’est appelé sans décision explicite du client d’activer cette collecte. | Configuration observée, requête uniquement si approuvée, et rappel que l’événement ne prouve ni identité ni affichage. |

Ne pas considérer un callback de cycle de vie comme preuve que le SDK tiers a cessé toute collecte. Confirmer le résultat dans les outils réseau, journaux ou mécanismes du fournisseur, sur une application de test et un périmètre autorisés. Conserver les résultats, versions et limites observées dans le compte rendu du pilote.

## Périmètre recommandé pour le pilote

Pour le premier assureur, privilégier une seule route de recette de l’espace assuré, derrière l’authentification de test du client, avec des comptes et données synthétiques. Le client autorise par écrit l’origine, la route, les testeurs et la fenêtre d’intervention. Si cette recette n’est pas disponible, répéter la démonstration sur `demo-assurance.html` et présenter explicitement cette page comme une maquette locale. Ne pas intégrer au portail réel ni transmettre des événements visiteurs tant que l’architecture, la sécurité, le traitement, l’hébergement, les formalités et les responsabilités contractuelles n’ont pas été examinés par les parties concernées.

La version actuelle utilise SQLite local par défaut, refuse le mode production et ne fournit pas encore de service hébergé durci, de SLA, de revue indépendante, de SSO/MFA ni de releases mobiles signées. ALAMANE aide à configurer des choix ; il ne garantit pas la conformité juridique. L’état fournisseur détaillé est dans [DOSSIER_SECURITE_FOURNISSEUR.md](./DOSSIER_SECURITE_FOURNISSEUR.md), et les conditions commerciales dans [PLAN_COMMERCIALISATION.md](./PLAN_COMMERCIALISATION.md).
