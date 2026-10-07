# ALAMANE Consent — React Native SDK starter

Ce SDK fournit un panneau natif React Native FR/AR, le chargement d’une politique publiée, la conservation locale d’un choix par propriété dans le stockage privé choisi par l’application, et une méthode d’envoi facultative appelée explicitement. Si le stockage refuse une lecture, le SDK essaie quand même de charger la politique depuis le serveur ; un choix dont l’écriture échoue reste appliqué en mémoire pendant la session et le panneau avertit qu’il pourra être redemandé après fermeture. Le panneau recharge la politique lorsque l’application revient au premier plan ; une nouvelle version invalide le choix local précédent, puis le visiteur est invité à choisir selon cette version. Après le choix, il expose un bouton accessible « Gérer mes préférences » pour rouvrir le panneau ; placer le composant dans une zone durable de l’application, comme ses paramètres de confidentialité. Il vise React Native 0.72+ et React 18+. Le code TypeScript/TSX est compilé en JavaScript CommonJS par Babel pour le paquet. Il n’est pas publié sur un registre npm ; un tarball privé est joint aux exécutions manuelles du workflow GitHub Actions pendant 14 jours.

Le SDK peut utiliser la dernière politique valide en cache lors d’une erreur réseau ou d’une réponse temporaire du service (`408`, `425`, `429` ou `5xx`). Une réponse non temporaire (dont `404`, qui signifie qu’aucune politique n’est publiée) ou une réponse de politique invalide efface la politique et le choix locaux ; `isAllowed()` renvoie alors `false` jusqu’au chargement d’une politique valide.

## Installation du paquet pilote privé

Depuis l’exécution manuelle du workflow GitHub Actions, télécharger l’artefact `alamane-mobile-preview-<commit>`, vérifier `SHA256SUMS` avec `shasum -a 256 -c SHA256SUMS` sur macOS ou `sha256sum -c SHA256SUMS` sur Linux, puis vérifier `BUILD-INFO.txt` pour confirmer le commit source et l’exécution attendue. Le manifeste protège l’intégrité après téléchargement; il ne signe pas le package et ne certifie pas son origine. Extraire `aman-consent-react-native-0.1.0.tgz`. Dans l’application cliente, installer le tarball avec l’adaptateur de stockage choisi par l’application :

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

const aman = new AmanConsentClient({
  baseUrl: 'https://cmp.example.ma',
  propertyId: 'PROPERTY_ID',
  channel: Platform.OS === 'ios' ? 'ios' : 'android',
  storage: AsyncStorage,
});

export function AppConsent() {
  return <AmanConsentBanner client={aman} language="fr" />;
}
```

L’identifiant de propriété est une référence publique de configuration, pas un secret. Le client accepte HTTPS; HTTP est limité aux hôtes loopback pour le développement. Appeler `aman.loadPolicy()` au démarrage si l’application doit piloter elle-même le chargement. Le panneau charge la politique à son montage et utilise la politique valide en cache si le réseau échoue.

## Relier les finalités aux SDK de l’application

Le panneau enregistre le choix sur l’appareil et ne démarre aucun SDK tiers. L’application hôte applique les états effectifs à ses propres SDK et les réconcilie après chargement ou changement de politique :

```tsx
useEffect(() => {
  const apply = () => {
    if (aman.isAllowed('analytics')) startAnalyticsIfNotStarted();
    else stopAnalyticsIfSupported();
  };
  const unsubscribe = aman.subscribe(apply);
  aman.loadPolicy().then(apply).catch(reportConsentSetupError);
  return unsubscribe;
}, []);
```

Pour signaler un choix au serveur, l’application peut appeler `aman.recordDecision(decision)` depuis `aman.onDecision(...)`, uniquement après validation de son avis et du modèle de collecte. L’envoi ne joint aucun identifiant de compte ou d’appareil persistant. Une erreur réseau ne supprime pas le choix local. Les événements reçus sont des déclarations du client SDK; ils ne prouvent ni identité, ni affichage, ni action réelle et ne forment pas à eux seuls une preuve juridique.

## Limites avant pilote

- SDK pilote compilé et non publié sur npm; aucune matrice de compatibilité, release signée, SBOM ou validation d’accessibilité n’est fournie.
- Le stockage est fourni par l’application. Si son écriture échoue, le choix ne dure que pendant la session en mémoire. Le choix reste local jusqu’à un appel d’envoi explicite; il n’existe pas de synchronisation multi-appareil ni de file de reprise.
- L’application doit démarrer, arrêter et réconcilier réellement ses SDK tiers. Une bibliothèque native déjà initialisée peut ne pas pouvoir être déchargée.
- La collecte, les formalités, les durées et le contenu de l’avis restent à valider par le client et ses conseils; le SDK ne garantit pas la conformité.
