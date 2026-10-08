# ALAMANE Consent — React Native SDK starter

Ce SDK fournit un panneau natif React Native FR/AR, le chargement d’une politique publiée, la conservation locale d’un choix par propriété dans le stockage privé choisi par l’application, et une méthode d’envoi facultative appelée explicitement. Si le stockage refuse une lecture, le SDK essaie quand même de charger la politique depuis le serveur ; un choix dont l’écriture échoue reste appliqué en mémoire pendant la session et le panneau avertit qu’il pourra être redemandé après fermeture. Le panneau recharge la politique lorsque l’application revient au premier plan ; une nouvelle version invalide le choix local précédent, puis le visiteur est invité à choisir selon cette version. Après le choix, il expose un bouton accessible « Gérer mes préférences » pour rouvrir le panneau ; placer le composant dans une zone durable de l’application, comme ses paramètres de confidentialité. Il vise React Native 0.72+ et React 18+. Le code TypeScript/TSX est compilé en JavaScript CommonJS par Babel pour le paquet. Il n’est pas publié sur un registre npm ; un tarball privé est joint aux exécutions manuelles du workflow GitHub Actions pendant 14 jours.

Si la politique publiée change pendant que le visiteur personnalise ses préférences, le panneau remplace les cases conservées par les états de départ de la nouvelle version avant l’enregistrement.

`initiallyEnabled` configure explicitement l’état de chaque finalité optionnelle avant un choix valide. `consentRequired` indique séparément si un choix positif doit précéder l’activation ; ALAMANE ne déduit pas l’un de l’autre. Les politiques historiques sans `initiallyEnabled` démarrent les finalités optionnelles désactivées, tandis qu’une finalité marquée `required` reste toujours active. Le responsable et son équipe juridique / DPO doivent valider ces réglages avant publication ; ils ne constituent pas une qualification juridique par ALAMANE.

Le SDK revalide le cache avec l’ETag de la politique ; une réponse `304` réutilise la politique locale sans la retélécharger. Les requêtes réseau expirent après 10 secondes par défaut ; `requestTimeoutMs` permet de régler ce délai entre 1 et 60 secondes. Le SDK annule la requête à l’expiration lorsque l’implémentation réseau le permet. Il peut utiliser la dernière politique valide en cache lors d’une erreur, d’un délai dépassé ou d’une réponse temporaire du service (`408`, `425`, `429` ou `5xx`). Un envoi de décision qui expire remonte une erreur à l’application ; celle-ci peut réessayer explicitement avec la même décision et le même identifiant d’événement. Il lit les entrées de cache de politique seule produites par les versions précédentes du package. Une réponse non temporaire (dont `404`, qui signifie qu’aucune politique n’est publiée) ou une réponse de politique invalide efface la politique et le choix locaux ; `isAllowed()` renvoie alors `false` jusqu’au chargement d’une politique valide.

## Installation du paquet pilote privé

Pour une exécution manuelle lancée depuis un commit contenant cette configuration, télécharger l’artefact `alamane-mobile-preview-<commit>`, vérifier `SHA256SUMS` avec `shasum -a 256 -c SHA256SUMS` sur macOS ou `sha256sum -c SHA256SUMS` sur Linux, puis vérifier `BUILD-INFO.txt` pour confirmer le commit source, l’exécution attendue et le périmètre limité du SBOM CycloneDX fourni (`alamane-react-native.sbom.cdx.json`). Ce SBOM décrit le graphe de dépendances npm du package React Native ; il ne couvre ni les dépendances Android/iOS, ni l’image de build, ni l’ensemble du dépôt. Le manifeste protège l’intégrité après téléchargement; il ne signe pas le package et ne certifie pas son origine. Extraire `aman-consent-react-native-0.1.0.tgz`. Dans l’application cliente, installer le tarball avec l’adaptateur de stockage choisi par l’application :

```sh
npm install ./aman-consent-react-native-0.1.0.tgz @react-native-async-storage/async-storage
```

Le tarball inclut le guide, le code source TypeScript et le JavaScript compilé utilisé par les applications. La CI construit et emballe ce paquet sur chaque exécution; l’artefact téléchargeable est joint aux exécutions manuelles. Il n’est pas signé ni publié sur un registre; vérifiez son origine et intégrez-le d’abord dans une application pilote.

## Installation locale pour un pilote

Pour travailler depuis le checkout plutôt que d’utiliser le tarball, cloner le dépôt à côté de l’application cliente, puis installer le dossier source avec un adaptateur de stockage choisi par l’application :

```sh
# Depuis la racine de l’application React Native ; adapter le chemin au checkout.
npm install ../alamane-consent/mobile/react-native @react-native-async-storage/async-storage
```

Le nom technique importé, `@aman-consent/react-native`, est provisoire et n’est pas publié. Sa disponibilité et ses droits d’usage doivent être vérifiés avant toute publication sur un registre.

Le dossier source se trouve hors de l’arborescence de l’application. Metro doit donc surveiller ce dossier et résoudre `react-native` depuis les dépendances de l’application. Fusionner ces valeurs avec le `metro.config.js` déjà présent, sans remplacer ses réglages propres :

```js
const path = require('path');
const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

const libraryPath = path.resolve(__dirname, '../alamane-consent/mobile/react-native');
const appReactNativePath = path.resolve(__dirname, 'node_modules/react-native');

module.exports = mergeConfig(getDefaultConfig(__dirname), {
  watchFolders: [libraryPath],
  resolver: {
    extraNodeModules: {
      'react-native': appReactNativePath,
    },
  },
});
```

Si l’application utilise Expo ou une configuration Metro personnalisée, reprendre les mêmes chemins dans son fichier de configuration et vérifier le bundling sur ses versions React Native prises en charge. L’équipe cliente doit conserver une seule copie effective de `react` et `react-native`.

```tsx
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';
import { AmanConsentBanner, AmanConsentClient } from '@aman-consent/react-native';

// Créer une propriété ALAMANE pour iOS et une autre pour Android.
// Chaque propriété porte sa propre politique publiée et son propre identifiant.
const platformConfig = Platform.select({
  ios: { propertyId: 'PROPERTY_ID_IOS', channel: 'ios' as const },
  android: { propertyId: 'PROPERTY_ID_ANDROID', channel: 'android' as const },
});

if (!platformConfig) {
  throw new Error('ALAMANE React Native prend en charge iOS et Android.');
}

const aman = new AmanConsentClient({
  baseUrl: 'https://cmp.example.ma',
  ...platformConfig,
  storage: AsyncStorage,
  requestTimeoutMs: 10000, // Facultatif : de 1000 à 60000 ms ; valeur par défaut 10000.
});

export function AppConsent() {
  return <AmanConsentBanner client={aman} language="fr" />;
}
```

Dans la console, choisis « React Native » dans le sélecteur de type d’intégration pour obtenir un extrait adapté à la propriété courante. Répète l’opération pour les propriétés iOS et Android et remplace les deux valeurs `PROPERTY_ID_*` ci-dessus par leurs identifiants respectifs. Cela permet à chaque binaire de charger la politique du canal natif correspondant ; les choix restent enregistrés localement par propriété et ne sont pas synchronisés entre iOS et Android.

L’identifiant de propriété est une référence publique de configuration, pas un secret. Le client accepte HTTPS; HTTP est limité aux hôtes loopback pour le développement. Appeler `aman.loadPolicy()` au démarrage si l’application doit piloter elle-même le chargement. Le panneau charge la politique à son montage et utilise la politique valide en cache si le réseau échoue.

## Relier les finalités aux SDK de l’application

Le panneau enregistre le choix sur l’appareil et ne démarre aucun SDK tiers. Avant d’intégrer le composant, désactive l’auto-initialisation et l’auto-collecte des SDK facultatifs dans leur configuration native. Un `useEffect` intervient après le montage React : l’application ne doit donc pas compter sur un appel d’arrêt tardif pour empêcher leur premier envoi. Initialise chaque SDK uniquement depuis `startAnalyticsIfNotStarted()` lorsque `isAllowed()` vaut `true`; `stopAnalyticsIfSupported()` sert à appliquer un refus ou un retrait après coup. L’application hôte réconcilie les états après chargement ou changement de politique :

```tsx
useEffect(() => {
  const apply = () => {
    if (aman.isAllowed('analytics')) startAnalyticsIfNotStarted();
    else stopAnalyticsIfSupported();
  };
  const unsubscribe = aman.subscribe(apply);
  apply(); // Démarrage fermé côté JS ; les SDK doivent aussi être configurés pour ne pas s’auto-initialiser.
  // AmanConsentBanner charge la politique, notifie ce client et propose une nouvelle tentative.
  return unsubscribe;
}, []);
```

Pour signaler un choix au serveur, l’application peut appeler `aman.recordDecision(decision)` depuis `aman.onDecision(...)`, uniquement après validation de son avis et du modèle de collecte. L’envoi ne joint aucun identifiant de compte ou d’appareil persistant. Une erreur réseau ne supprime pas le choix local. Les événements reçus sont des déclarations du client SDK; ils ne prouvent ni identité, ni affichage, ni action réelle et ne forment pas à eux seuls une preuve juridique.

## Limites avant pilote

- SDK pilote compilé et non publié sur npm ; pas de matrice de compatibilité ni de release signée. Le workflow est configuré pour joindre un SBOM CycloneDX limité au graphe npm React Native lors d’un lancement manuel, mais cette configuration n’a pas encore été exécutée ; il manque un SBOM couvrant les plateformes natives et l’environnement de build, ainsi qu’une validation d’accessibilité.
- Le stockage est fourni par l’application. Si son écriture échoue, le choix ne dure que pendant la session en mémoire. Le choix reste local jusqu’à un appel d’envoi explicite; il n’existe pas de synchronisation multi-appareil ni de file de reprise.
- L’application doit démarrer, arrêter et réconcilier réellement ses SDK tiers. Une bibliothèque native déjà initialisée peut ne pas pouvoir être déchargée.
- La collecte, les formalités, les durées et le contenu de l’avis restent à valider par le client et ses conseils; le SDK ne garantit pas la conformité.
