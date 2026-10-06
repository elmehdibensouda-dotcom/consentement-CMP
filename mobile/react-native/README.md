# Aman Consent — React Native SDK starter

Ce package source fournit un panneau natif React Native FR/AR, le chargement d’une politique publiée, la conservation locale d’un choix par propriété dans le stockage privé choisi par l’application, et une méthode d’envoi facultative appelée explicitement. Après le choix, il expose un bouton accessible « Gérer mes préférences » pour rouvrir le panneau; placer le composant dans une zone durable de l’application, comme ses paramètres de confidentialité. Il vise React Native 0.72+ et React 18+. Aucun binaire ni package npm public n’est publié.

## Installation locale

Ajouter le dossier `mobile/react-native` comme dépendance locale au projet, puis fournir un adaptateur de stockage. Exemple avec AsyncStorage :

```sh
# Adapter le chemin local vers le checkout Aman dans le projet client.
npm install ../alamane-consent/mobile/react-native @react-native-async-storage/async-storage
```

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

- Package de démarrage à compiler et intégrer dans les versions React Native ciblées; aucune matrice de compatibilité, release signée, SBOM ou validation d’accessibilité n’est fournie.
- Le stockage est fourni par l’application. Le choix reste local jusqu’à un appel d’envoi explicite; il n’existe pas de synchronisation multi-appareil ni de file de reprise.
- L’application doit démarrer, arrêter et réconcilier réellement ses SDK tiers. Une bibliothèque native déjà initialisée peut ne pas pouvoir être déchargée.
- La collecte, les formalités, les durées et le contenu de l’avis restent à valider par le client et ses conseils; le SDK ne garantit pas la conformité.
