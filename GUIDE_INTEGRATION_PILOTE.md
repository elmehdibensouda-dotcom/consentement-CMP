# ALAMANE — guide d’intégration pour un pilote

**État :** guide d’un prototype local, pas une procédure de déploiement en production. Les exemples utilisent des identifiants et des domaines fictifs. Ne pas y saisir de donnée bancaire, de secret ou de donnée réelle de visiteur.

## Choisir son intégration

| Application à raccorder | SDK | État de distribution |
| --- | --- | --- |
| Site Web | `aman-cmp.js` | Fichier présent dans le dépôt ; un lancement manuel du workflow CI est configuré pour joindre un aperçu temporaire vérifiable. À héberger par l’équipe cliente sur un domaine qu’elle contrôle. |
| Application React Native | `mobile/react-native` | Source installable depuis un checkout, ou tarball privé issu d’une exécution manuelle GitHub Actions (conservé 14 jours). Pas de publication npm. |
| Application iOS native | `mobile/ios` | Package Swift depuis le dépôt privé ou un checkout local ; un lancement manuel du workflow CI est configuré pour joindre une archive source temporaire vérifiable. Pas de release signée ou publiée. |
| Application Android native | `mobile/android` | Module Gradle depuis un checkout local ; l’AAR de prévisualisation vient d’une exécution manuelle GitHub Actions. Pas de release signée ou publiée dans Maven. |

Les trois aperçus destinés à une évaluation sont disponibles dans le [lancement manuel GitHub Actions du 8 octobre 2026](https://github.com/elmehdibensouda-dotcom/alamane-consent/actions/runs/37755115197), jusqu’au 22 octobre 2026 : sources Web, sources Swift Package iOS, AAR Android, APK de démonstration, tarball React Native et SBOM CycloneDX React Native. Les SHA-256 des manifestes ont été vérifiés. Le manifeste protège l’intégrité des fichiers après téléchargement, pas leur origine ; l’APK utilise une clé debug et aucun artefact n’est une release signée ou de production.

Les SDK mobiles sont des bases de pilote. Aucun n’a encore été intégré et validé dans une application cliente. La compilation ou l’emballage en CI ne constitue pas une validation sur les appareils et versions du client.

### Distribution envisagée pour un pilote entreprise

Hypothèse à confirmer avec l’acheteur : après revue et gel d’une version, remettre un bundle horodaté avec commit source, manifeste d’empreintes et inventaire de composants pour import dans le dépôt d’artefacts approuvé par le client. Ce dépôt GitHub est privé et les aperçus CI actuels expirent après 14 jours ; ils ne constituent pas une distribution client durable. Aucun accès client au dépôt ALAMANE, aucune release publique et aucune publication npm/Maven n’ont été mis en place. Les empreintes détectent une altération après création du bundle, mais ne remplacent ni une signature de release ni une attestation de provenance. Les exigences de signature, SBOM, approbation et conservation sont à convenir avec la sécurité du client avant transfert.

## Préparer la propriété dans la console

1. Créer ou sélectionner l’organisation du pilote, puis une propriété avec le canal correspondant (`web`, `ios` ou `android`). Pour une application React Native multiplateforme, créer une propriété iOS et une propriété Android ; le SDK choisit l’identifiant et la politique du canal natif correspondant. L’étiquette d’environnement sert à la gouvernance ; elle ne sépare pas les données ni les déploiements.
2. Renseigner les finalités, leur classification, la règle de choix préalable (`consentRequired`), l’état avant le premier choix (`initiallyEnabled`) et les textes français/arabe. Faire valider ces paramètres, les traductions, les durées et le traitement par les responsables du client et leurs conseils.
3. Publier une politique pour cette propriété. Une propriété étiquetée production exige une publication par une autre personne que celle ayant modifié le brouillon.
4. Copier l’identifiant de propriété généré par la console. Il sert à sélectionner une configuration publique et n’est pas un secret.
5. Utiliser une URL d’API HTTPS pour tout hôte distant. HTTP est accepté seulement pour `localhost`, `127.0.0.1` et `::1` dans les démonstrations locales.

L’origine déclarée pour une propriété Web autorise uniquement les routes publiques de cette propriété ; elle ne prouve pas le contrôle du domaine. `AMAN_CORS_ORIGINS` sert à la console et aux appels avec cookies. Pour les détails de configuration, voir le [guide de démarrage](./README.md#démarrer-la-démo-connectée) et le [contrat de politique](./schemas/consent-policy.schema.json).

## Intégrer la plateforme choisie

### Web

Héberger `aman-cmp.js` sur un domaine contrôlé par le client, puis ajouter le script avec l’URL d’API et l’identifiant de propriété. Le code complet, la configuration CSP, le raccordement des balises et les limites GTM figurent dans [README.md — intégration Web](./README.md#intégration-web-minimale). Les scripts facultatifs doivent être balisés et ne démarrer qu’après l’état applicable. Un script déjà exécuté n’est pas déchargé automatiquement lors d’un retrait.

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
- Le SDK Web charge la politique à l’initialisation, puis la revalide toutes les cinq minutes et au retour de l’onglet au premier plan (avec au moins une minute entre deux vérifications). Une nouvelle version invalide le choix associé à l’ancienne version, affiche à nouveau le panneau et émet `aman:policy-updated`. Si aucune politique valide ne peut être obtenue, les finalités optionnelles restent fermées et `aman:policy-unavailable` est émis. Cette mise à jour ne peut pas décharger un script tiers déjà exécuté ; l’application doit raccorder son mécanisme d’arrêt. React Native recharge la politique au retour de l’application au premier plan ; pour iOS et Android natifs, l’application hôte doit reprendre le chargement et transmettre la politique avec `updatePolicy(...)` au retour au premier plan.
- L’application Web doit raccorder l’état effectif à son propre cycle de vie. `aman:consent-update` transmet les états des finalités ; `aman:policy-unavailable` demande de fermer les finalités optionnelles. Remplacer ces fonctions d’exemple par les appels documentés par les fournisseurs réellement utilisés ; l’événement seul ne décharge pas leurs bibliothèques déjà initialisées.

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

## Périmètre recommandé pour le pilote

Commencer sur un domaine Web public non authentifié, dans un environnement isolé, avec une politique et des technologies convenues avec le client. Utiliser des données fictives ou explicitement approuvées. Ne pas intégrer à une application bancaire ou transmettre des événements réels tant que l’architecture, la sécurité, le traitement, l’hébergement, les formalités et les responsabilités contractuelles n’ont pas été examinés par les parties concernées.

La version actuelle utilise SQLite local par défaut, refuse le mode production et ne fournit pas encore de service hébergé durci, de SLA, de revue indépendante, de SSO/MFA ni de releases mobiles signées. ALAMANE aide à configurer des choix ; il ne garantit pas la conformité juridique. L’état fournisseur détaillé est dans [DOSSIER_SECURITE_FOURNISSEUR.md](./DOSSIER_SECURITE_FOURNISSEUR.md), et les conditions commerciales dans [PLAN_COMMERCIALISATION.md](./PLAN_COMMERCIALISATION.md).
