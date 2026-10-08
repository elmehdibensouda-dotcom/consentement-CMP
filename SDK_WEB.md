# ALAMANE — guide d’intégration du SDK Web

**Aperçu pilote · source JavaScript non signée · à valider avec l’équipe sécurité du site**

Ce guide accompagne `aman-cmp.js`. Le fichier est hébergé par l’équipe cliente sur un domaine qu’elle contrôle ; il n’existe pas de CDN ALAMANE prêt pour la production. La prévisualisation GitHub Actions est temporaire et ne constitue pas une release signée.

## 1. Préparer la propriété

Dans la console, créer une propriété de canal **Web**, déclarer l’origine exacte du site (HTTPS, hôte et port éventuel, sans chemin), créer une politique et la publier. L’origine configure l’accès aux deux routes publiques du SDK ; elle ne prouve pas le contrôle du domaine. L’identifiant de propriété est une référence publique, pas un secret.

Avant de publier, le responsable du traitement et ses conseils doivent examiner les finalités, les états initiaux, la notice, les destinataires, les durées et les règles applicables. ALAMANE ne détermine pas la qualification juridique et ne garantit pas la conformité.

## 2. Héberger et initialiser le fichier

Télécharger `aman-cmp.js` depuis le dépôt ou l’artefact `alamane-web-preview-<commit>`, vérifier son empreinte avec `SHA256SUMS`, puis l’héberger, par exemple sous `/assets/aman-cmp.js`, sur un domaine contrôlé et approuvé par l’équipe cliente.

```html
<script src="/assets/aman-cmp.js"
        data-aman-api-base-url="https://cmp.example.ma"
        data-aman-property-id="PROPERTY_ID"
        data-aman-channel="web"
        data-aman-collect-decision-events="false"
        data-aman-request-timeout-ms="10000"></script>

<script type="text/plain"
        data-aman-category="analytics"
        data-aman-src="/assets/analytics.js"></script>
```

Remplacer `cmp.example.ma`, `PROPERTY_ID` et les ressources d’exemple. L’URL distante de l’API doit être en HTTPS ; HTTP est limité aux hôtes loopback de développement. Le canal Web laisse la remontée des décisions désactivée par défaut.

## 3. Raccorder les technologies

Les scripts facultatifs doivent être configurés pour ne pas démarrer avant le choix applicable. Pour le chargement géré par ALAMANE, utiliser un élément `type="text/plain"`, `data-aman-src` et l’identifiant de finalité dans `data-aman-category`. Vérifier les déclencheurs de GTM séparément : un déclencheur `Page View` peut partir avant l’événement de consentement.

Raccorder aussi chaque finalité à son mécanisme de démarrage et d’arrêt fournisseur. Le SDK peut charger une ressource gérée après autorisation, mais ne peut pas décharger une bibliothèque déjà exécutée ni annuler une donnée déjà transmise.

## 4. Langue, politique et réseau

Le SDK utilise les langues `fr` et `ar` et reprend `defaultLanguage` de la politique ; `data-aman-locale` peut suivre la langue de l’application. La direction RTL est appliquée pour l’arabe standard. La durée maximale Web est bornée à 180 jours dans ce prototype ; elle ne détermine pas la règle juridique d’un traitement.

Les requêtes de politique et de décision expirent après 10 secondes par défaut. En cas d’erreur réseau ou de réponse temporaire, une dernière politique valide peut être utilisée depuis le cache. Une réponse `404` ou une politique invalide efface le choix et le cache ; les finalités optionnelles restent alors désactivées. Si le stockage persistant est indisponible, le choix peut ne durer que jusqu’à la fermeture de l’onglet.

## 5. CSP et revue de sécurité

La CSP du site doit autoriser le domaine du SDK dans `script-src`, l’hôte de l’API dans `connect-src` et le style inline requis par la bannière dans `style-src`. Avec une CSP à nonce, ajouter le nonce de la réponse à la balise `<script src>` afin qu’il soit propagé aux éléments gérés.

Avant le pilote, l’équipe cliente doit examiner le code, les hôtes réseau, la CSP, l’accessibilité et le comportement des scripts réels dans son environnement. L’artefact est une source de prévisualisation vérifiable par checksum, sans signature d’origine, attestation ni garantie de production. Ne pas l’utiliser sur un site bancaire ou avec des données réelles tant que les validations, l’hébergement et les responsabilités ne sont pas convenus.
