# ALAMANE — guide d’intégration du SDK Web

**Aperçu pilote · source JavaScript non signée · à valider avec l’équipe sécurité du site**

Ce guide accompagne `aman-cmp.js`. Le fichier est hébergé par l’équipe cliente sur un domaine qu’elle contrôle ; il n’existe pas de CDN ALAMANE prêt pour la production. La prévisualisation GitHub Actions est temporaire et ne constitue pas une release signée.

## 1. Préparer la propriété

Dans la console, créer une propriété de canal **Web**, déclarer l’origine exacte du site (HTTPS, hôte et port éventuel, sans chemin), créer une politique et la publier. L’origine configure l’accès aux deux routes publiques du SDK ; elle ne prouve pas le contrôle du domaine. L’identifiant de propriété est une référence publique, pas un secret.

Avant de publier, le responsable du traitement et ses conseils doivent examiner les finalités, les états initiaux, la notice, les destinataires, les durées et les règles applicables. ALAMANE ne détermine pas la qualification juridique et ne garantit pas la conformité.

## 2. Héberger et initialiser le fichier

Télécharger `aman-cmp.js` depuis le dépôt ou l’artefact `alamane-web-preview-<commit>`, vérifier son empreinte avec `SHA256SUMS`, puis l’héberger, par exemple sous `/assets/aman-cmp.js`, sur un domaine contrôlé et approuvé par l’équipe cliente.

```html
<script nonce="{{CSP_NONCE}}"
        src="/assets/aman-cmp.js"
        data-aman-api-base-url="https://cmp.example.ma"
        data-aman-property-id="PROPERTY_ID"
        data-aman-channel="web"
        data-aman-collect-decision-events="false"
        data-aman-request-timeout-ms="10000"
        data-aman-locale="fr"
        data-aman-allowed-script-origins="https://cdn.fournisseur.example"></script>

<script type="text/plain"
        nonce="{{CSP_NONCE}}"
        data-aman-category="analytics"
        data-aman-src="/assets/analytics.js"></script>
```

Remplacer `cmp.example.ma`, `PROPERTY_ID`, le chemin du SDK et les ressources d’exemple. L’URL distante de l’API doit être en HTTPS ; HTTP est limité aux hôtes loopback de développement. Le canal Web laisse la remontée des décisions désactivée par défaut. Le serveur de l’application doit remplacer `{{CSP_NONCE}}` par une valeur aléatoire propre à la réponse HTTP et réutiliser cette même valeur dans son en-tête CSP.

## 3. Raccorder les technologies

Les scripts facultatifs doivent être configurés pour ne pas démarrer avant le choix applicable. Pour le chargement géré par ALAMANE, utiliser un élément `type="text/plain"`, `data-aman-src` et l’identifiant de finalité dans `data-aman-category`.

Contrat de chargement des scripts gérés :

- **Nonce.** Si la balise du SDK porte un nonce, un placeholder ne démarre que s’il porte **le même nonce** (`nonce="{{CSP_NONCE}}"`), et seul ce placeholder reçoit le nonce sur le `<script>` créé. Un placeholder sans nonce, ou avec un autre nonce, est ignoré : du balisage injecté dans la page ne peut donc pas emprunter le nonce du SDK.
- **Source.** `data-aman-src` est résolu en URL absolue par rapport à l’adresse de la page. Sont refusés les URL avec identifiants, les protocoles autres que `https:`/`http:` (`javascript:`, `data:`, `blob:`…) et les origines non autorisées. Par défaut, seule l’origine de la page est autorisée ; ajouter chaque autre origine réellement utilisée dans `data-aman-allowed-script-origins` sur la balise du SDK (liste séparée par des espaces, origine seule : `https://hôte[:port]`, sans chemin ; `http:` n’est accepté que pour un hôte loopback). Cette liste n’est lue que sur la balise du SDK, jamais depuis `window.AmanConsentConfig`.
- **Sans nonce.** Les intégrations existantes sans nonce continuent de fonctionner pour les scripts de même origine ; les scripts tiers doivent désormais être ajoutés à `data-aman-allowed-script-origins`.
- **Refus.** Un placeholder refusé n’est pas chargé ; le SDK émet `aman:tag-blocked` avec la finalité et le motif (`nonce`, `url`, `credentials`, `protocol` ou `origin`), une seule fois par motif.
- **Limites.** Ces contrôles réduisent l’exploitation d’une injection HTML à travers le SDK ; ils ne remplacent ni l’assainissement des contenus, ni la CSP du site, et ne corrigent pas une XSS existante. Une injection capable d’exécuter du JavaScript, ou une page qui divulgue son nonce, reste hors de leur portée. Vérifier les déclencheurs de GTM séparément : un déclencheur `Page View` peut partir avant l’événement de consentement.

Raccorder aussi chaque finalité à son mécanisme de démarrage et d’arrêt fournisseur. Pour une intégration JavaScript directe, `AmanCMP.registerPurposeHandler` reçoit l’état initial puis les changements applicables. La fonction `start` n’est appelée que lorsque la finalité est active ; elle peut renvoyer une fonction de nettoyage exécutée quand elle devient inactive, quand l’inscription est retirée ou quand le contexte de politique (propriété/version/canal) change alors que la finalité reste active :

```js
const unregisterAnalytics = window.AmanCMP.registerPurposeHandler('analytics', () => {
  startAnalyticsIfNotStarted();
  return () => stopAnalyticsIfSupported();
});
```

Enregistrer ce raccordement depuis le code de l’application après le chargement de `aman-cmp.js`. Le démarrage et le nettoyage sont synchrones ; le nettoyage doit appeler le mécanisme d’arrêt prévu par le fournisseur. Si `start` échoue après une initialisation partielle, il doit annuler ses effets partiels avant de lever l’erreur. Pour GTM, utiliser ses déclencheurs et l’événement `aman:consent-update` avec une seule voie de raccordement par finalité afin d’éviter un double démarrage. Le SDK ne peut pas décharger une bibliothèque déjà exécutée, annuler une donnée déjà transmise, ni garantir que l’API d’arrêt d’un fournisseur efface ses données locales ; vérifier ce comportement pour chaque technologie. Une erreur du callback émet `aman:purpose-handler-error` avec la finalité et la phase (`start` ou `stop`), sans inclure de choix ni de données visiteur.

## 4. Langue, politique et réseau

Le SDK utilise les langues `fr` et `ar` et reprend `defaultLanguage` de la politique ; `data-aman-locale` peut suivre la langue de l’application. La direction RTL est appliquée pour l’arabe standard. La durée maximale Web est bornée à 180 jours dans ce prototype ; elle ne détermine pas la règle juridique d’un traitement.

Les requêtes de politique et de décision expirent après 10 secondes par défaut. En cas d’erreur réseau ou de réponse temporaire, une dernière politique valide peut être utilisée depuis le cache. Une réponse `404` ou une politique invalide efface le choix et le cache ; les finalités optionnelles restent alors désactivées. Si le stockage persistant est indisponible, le choix peut ne durer que jusqu’à la fermeture de l’onglet.

## 5. CSP et revue de sécurité

Le SDK peut être hébergé sur le domaine du client, comme `/assets/aman-cmp.js` dans l’exemple. L’API distante doit être autorisée dans `connect-src`. Le module crée une feuille `<style>` et, après un choix favorable, les balises `<script>` des ressources gérées. Il donne le nonce de sa propre balise à sa feuille de style et aux seuls scripts créés depuis un placeholder portant ce même nonce (voir section 3).

Exemple de valeur d’en-tête à adapter à la CSP déjà administrée par l’application :

```text
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{{CSP_NONCE}}'; style-src 'self' 'nonce-{{CSP_NONCE}}'; connect-src 'self' https://cmp.example.ma; object-src 'none'; base-uri 'self'; frame-ancestors 'self'
```

`{{CSP_NONCE}}` doit être remplacé par le nonce aléatoire de la réponse, avec la même valeur sur la balise du SDK, sur chaque placeholder géré et dans les directives `script-src` et `style-src`. Si les ressources du SDK ou les scripts approuvés sont servis depuis d’autres hôtes, l’équipe cliente doit les ajouter explicitement à la directive appropriée. Cette liste ne couvre pas les fournisseurs tiers du client. Ne pas ajouter globalement `'unsafe-inline'` pour résoudre une erreur CSP : faire examiner toute exception et limiter sa portée.

Le test navigateur `bash scripts/run-web-sdk-tests.sh` (Chrome ou Chromium headless) vérifie ces règles avec et sans nonce. Avant le pilote, l’équipe cliente doit examiner le code, les hôtes réseau, la CSP, l’accessibilité et le comportement des scripts réels dans son environnement. L’artefact est une source de prévisualisation vérifiable par checksum, sans signature d’origine, attestation ni garantie de production. Ne pas l’utiliser sur un site bancaire ou avec des données réelles tant que les validations, l’hébergement et les responsabilités ne sont pas convenus.

## 6. Retour arrière de la route de test

Préparer et faire approuver ces étapes avant l’intégration. Les exécuter uniquement sur la route autorisée :

1. Restaurer la version précédente de la route ou du composant applicatif via le mécanisme de livraison du client.
2. Retirer la balise `aman-cmp.js`, les balises `type="text/plain"` portant `data-aman-src` et les appels à `AmanCMP.registerPurposeHandler` ajoutés pour le pilote. Vérifier aussi les déclencheurs GTM ou les initialisations directes des fournisseurs modifiés pour l’essai.
3. Retirer de la CSP uniquement les hôtes et le nonce qui ne sont plus utilisés par cette intégration, après vérification qu’aucune autre fonctionnalité ne les requiert. Garder l’en-tête de sécurité du client sous le contrôle de son équipe.
4. Recharger la route et vérifier dans l’onglet réseau que les ressources ALAMANE et les traceurs optionnels du pilote ne sont plus demandés. Un fournisseur déjà démarré peut nécessiter son propre mécanisme d’arrêt ; le retrait de la balise ALAMANE ne peut pas annuler une requête déjà envoyée.
5. Si le client veut aussi effacer le choix local de cette propriété sur ce navigateur de test, supprimer uniquement les deux clés correspondant à son identifiant depuis `localStorage` et `sessionStorage` : `aman:choice:PROPERTY_ID` et `aman:policy:PROPERTY_ID`. Ne pas appeler `AmanCMP.clearDemoData()` sur une origine partagée : cette fonction efface les caches et choix ALAMANE de toutes les propriétés de cette origine.

Consigner l’heure, la version restaurée, les vérifications réseau et toute limite d’arrêt fournisseur dans le compte rendu de recette. Cette procédure doit être testée par l’équipe du client avant d’autoriser une fenêtre d’intervention.
