# ALAMANE — plan de commercialisation au Maroc

**Version de travail · 8 octobre 2026**
**Décision de départ :** préparer une première preuve de concept Web avec une compagnie d’assurance au Maroc. Les banques et grands groupes restent des segments prioritaires à qualifier ensuite ; les PME e-commerce et agences sont une piste d’expansion ultérieure.

## 1. Le produit

ALAMANE aide les organisations à inventorier les technologies qui observent ou collectent des données sur leurs sites et dans leurs applications mobiles, expliquer leurs usages aux utilisateurs, recueillir et respecter leurs choix, et retrouver les paramètres et événements associés.

**Promesse de lancement :** « Une gestion du consentement compréhensible, adaptée aux sites marocains et gouvernable à l’échelle de plusieurs domaines. »

Ne pas promettre une conformité garantie, une certification CNDP ou un taux de consentement amélioré. Le responsable du traitement garde ses obligations. ALAMANE fournit des outils et de la traçabilité ; les règles applicables doivent être validées selon chaque traitement.

## 2. Clientèle de départ et problème à résoudre

### Segment pilote

- Premier pilote à qualifier : assureur marocain, avec un cas d’usage Web dans une route de recette de l’espace assuré ; l’accès et l’autorisation client restent à obtenir.
- Banques et grands groupes marocains ayant plusieurs domaines, marques, parcours de connexion ou équipes digitales.
- Première vente à travailler avec un sponsor digital / produit, un DPO ou juriste, la sécurité informatique et les achats.

Le besoin à valider est une gouvernance centralisée : connaître les traceurs par domaine, traduire une politique en configuration qui respecte les choix des visiteurs, garder un historique exploitable, et prouver les changements aux équipes internes. Les exigences d’intégration, de sécurité, d’hébergement et de contractualisation peuvent être des critères d’achat bloquants.

Pour préparer le questionnaire fournisseur sans surpromettre, utiliser le [dossier de sécurité interne](./DOSSIER_SECURITE_FOURNISSEUR.md) comme inventaire de l’état actuel et des preuves manquantes. Ce document ne doit pas être transmis comme attestation ni comme preuve d’homologation. La [présélection d’hébergement au Maroc](./HEBERGEMENT_PREPARATION_MAROC.md) identifie OCI Casablanca comme premier candidat à préqualifier, sans le sélectionner : disponibilité, sauvegarde et reprise restent à démontrer au regard des exigences d’un acheteur bancaire.

### Besoins à vérifier avant de figer le produit

1. Qui possède aujourd’hui l’inventaire des traceurs et qui approuve les finalités par domaine ?
2. Où bloque le groupe : inventaire, gouvernance multi-domaines, configuration des tags, formalités CNDP, audit, sécurité ou intégration ?
3. Quelles exigences sont obligatoires pour un nouveau fournisseur SaaS : hébergement, résidence, chiffrement, SSO, audit, SLA, assurance, test d’intrusion ?
4. Quelles équipes approuvent l’achat, quel est le cycle budgétaire et peut-on commencer par un site public de moindre risque ?
5. Quelles langues sont nécessaires pour les visiteurs : français et arabe standard ? Darija seulement après validation ?
6. Quel budget peut être affecté à une preuve de concept et sur quelle ligne d’achat ?

Conduire 8 à 12 entretiens qualifiés au sein de 3 à 5 institutions (digital, juridique/DPO, sécurité et achats). Ne pas traiter une réunion exploratoire comme une validation : identifier le sponsor, les critères de sécurité, la procédure d’achat, le budget et le périmètre d’une preuve de concept écrite.

## 3. Cadre réglementaire de conception

La loi marocaine 09-08 et les publications de la CNDP sont les références locales de départ. La CNDP a publié la délibération D-939-2025 du 28 novembre 2025 sur le modèle de déclaration simplifiée pour certains traitements de données personnelles via des cookies.

Points à intégrer au parcours produit, après revue par un conseil marocain spécialisé :

- Le périmètre de D-939-2025 dépend des finalités du traitement ; la décision nomme notamment la publicité personnalisée, la personnalisation de contenu ou de services, le partage social et la mesure d’audience sans profilage.
- La délibération comporte une tension de rédaction à faire trancher avant toute règle de production : son paragraphe 6 indique que le consentement préalable n’est pas nécessaire pour certaines finalités, sauf la publicité personnalisée et le partage social, puis demande aussi de recueillir le consentement avant le premier dépôt de cookies. Elle exige dans tous les cas des moyens simples pour refuser et le respect de ce choix. ALAMANE ne déduit donc plus l’état initial de `consentRequired` : `initiallyEnabled` porte un réglage explicite séparé, traité comme désactivé dans les politiques historiques qui ne le contiennent pas. Pour le pilote, le responsable et son conseil doivent valider par finalité la règle applicable, l’état de départ et la conduite des tags avant publication ; le refus explicite doit toujours être appliqué conformément à la règle validée.
- L’information préalable doit identifier le responsable de traitement, les finalités, les catégories de données, les destinataires, les transferts à l’étranger et autorisations pertinentes, les coordonnées pour exercer les droits et les références de récépissés CNDP.
- La déclaration simplifiée prévue par la décision doit être faite par le responsable concerné avant le traitement entrant dans son champ. ALAMANE peut préparer un inventaire ou des éléments de travail, mais ne doit pas présenter le dépôt comme effectué à la place du client.
- La décision fixe une durée maximale de six mois pour les données de cookies qu’elle vise et pour la conservation du choix de consentement. Les transferts à l’étranger requièrent une autorisation préalable de la CNDP selon le texte.
- Les recommandations de la CNDP sur les sites rappellent aussi la notification des traitements et les formalités de transfert à l’étranger selon les cas.

**Conséquence produit :** ne pas présenter comme règle juridique marocaine une politique universelle, qu’elle bloque tous les cookies non essentiels jusqu’à acceptation ou qu’elle active par défaut des finalités. Le produit doit documenter la finalité et le réglage approuvé, signaler les cas sans validation et ne publier qu’après confirmation du responsable et de son conseil. Une revue juridique doit confirmer la classification des cas, l’interprétation de la rédaction de D-939-2025, les textes à jour et la responsabilité d’ALAMANE comme sous-traitant éventuel.

**Vérification des sources :** références officielles consultées le 8 octobre 2026. La [délibération D-939-2025](https://www.cndp.ma/wp-content/uploads/2025/12/Deliberation-N%C2%B0-D-939-2025-du-28112025-relative-au-modele-de-declaration-simplifiee-relative-au-traitement-des-donnees-a-caractere-personnel-de-cookies-sur-un-terminal.pdf) vise des finalités précises, prévoit une durée maximale de six mois pour les données et le choix exprimé, décrit l’information préalable et une déclaration simplifiée, et soumet les transferts à l’étranger à l’autorisation préalable de la CNDP. Sa rédaction sur le consentement doit être interprétée par un conseil : le paragraphe 6 prévoit des exceptions au consentement préalable pour certaines finalités tout en demandant un consentement avant le premier dépôt de cookies. Sur sa [page de procédure de notification](https://www.cndp.ma/procedures-de-notification-process/), la CNDP indique actuellement F-214, « déclaration normale conformément à une décision », pour la gestion des cookies de site Web et liste les pièces à joindre. Le client et son conseil doivent confirmer la procédure applicable au moment du dépôt. Voir aussi la page CNDP sur les [transferts de données à l’étranger](https://www.cndp.ma/transfert-de-donnees-a-letranger/). Ce relevé facilite la traçabilité du cadrage produit ; il ne constitue pas un avis juridique et doit être revu avant toute offre ou configuration client.

## 4. MVP vendable et périmètre final web + mobile

L’entrée [index.html](./index.html) redirige vers la console connectée [admin.html](./admin.html), qui s’ouvre sur une vue d’ensemble multi-organisation des comptes de configuration réels de la session : organisations, propriétés étiquetées développement / recette / production, politiques publiées, brouillons et actions administratives. La vue par propriété distingue une politique publiée, un brouillon sans publication et l’absence de politique publiée, puis ouvre directement la politique choisie. Cet indicateur décrit seulement la configuration de politique ; il ne prouve ni l’intégration du SDK ni l’état d’un déploiement. Cette étiquette facilite le suivi mais ne garantit pas une isolation technique entre environnements. Le SDK Web peut transmettre sur activation expresse des décisions client déclarées ; les API clients natifs exposent aussi un appel explicite que l’application hôte doit activer. La console agrège les événements reçus sur 30 jours, permet de comparer les décisions par finalité à l’intérieur de chaque propriété/version de politique et d’exporter les événements encore retenus en CSV par propriété ou de façon consolidée par organisation. Ces événements sont des déclarations du SDK : ils ne certifient pas l’identité du visiteur, l’affichage d’un écran ou l’action réelle et ne constituent pas à eux seuls une preuve juridique. Le [scanner local](./scanner-tool.html) observe une page courante, signale les marqueurs ALAMANE directs repérés dans les scripts, permet un classement manuel et télécharge un rapport JSON ; ce signal DOM ne prouve pas que tous les déclenchements sont contrôlés et ne remplace pas l’inspection des gestionnaires comme GTM. Un éditeur peut importer explicitement le rapport sur une propriété Web, où les 20 derniers imports sont conservés et peuvent être supprimés. Le scanner ne parcourt pas un site entier : les scans consolidés multi-page restent à construire. Les SDK Android, iOS et React Native disposent désormais d’étapes de compilation ou de packaging CI ; aucun n’a été éprouvé dans l’application d’un acheteur, signé comme release ou distribué en environnement client. Le premier pilote assurance vise une seule route Web de recette de l’espace assuré, avec comptes fictifs et origine autorisée ; l’intégration mobile reste hors de ce premier périmètre.

L’architecture du produit et le format commun des politiques sont décrits dans [ARCHITECTURE.md](./ARCHITECTURE.md) et [schemas/consent-policy.schema.json](./schemas/consent-policy.schema.json). L’éditeur conserve la notice historique et ajoute des champs séparés FR/AR ; le SDK Web et les SDK natifs choisissent le texte selon la langue affichée. Les SDK iOS et Android disposent d’une compilation CI ; le package React Native est transpilé en JavaScript et emballé dans la CI. Le [lancement manuel du 8 octobre 2026](https://github.com/elmehdibensouda-dotcom/alamane-consent/actions/runs/37767815026) a produit des aperçus temporaires des sources Web, iOS et Android/React Native, avec dépôt Maven local et manifestes SHA-256 vérifiés. Ils expirent le 22 octobre 2026 et ne portent pas de signature de release. Ce sont des bases de pilote, pas encore des bibliothèques intégrées chez un client ni des versions prêtes à distribuer en production.

### Pour l’administrateur

1. Créer une organisation, des propriétés étiquetées par environnement et des appartenances ; gérer les rôles owner, admin, editor et viewer. Le prototype possède déjà ces parcours, mais les étiquettes d’environnement ne séparent pas les données ni les déploiements.
2. Renseigner identité du responsable de traitement, contact, finalités et notice FR/AR, règles d’activation, fournisseurs associés, catégories de données, destinataires et références CNDP. Le client fournit et fait relire les contenus dans les langues qu’il propose. Les fournisseurs sont affichés à titre indicatif dans l’interface visiteur ; le client doit raccorder et vérifier chaque script ou SDK à l’identifiant de finalité correspondant.
3. Utiliser le scanner local existant pour relever les ressources visibles page par page, classer les résultats à la main et importer plusieurs rapports JSON mono-page en lot sur une propriété Web. La console en calcule une synthèse locale exportable en CSV ou JSON des ressources et cookies distincts observés, avec leurs pages et classements recensés. Le scanner ne parcourt pas un site entier ; son marqueur DOM ne prouve pas que tous les déclenchements sont contrôlés.
4. Configurer la bannière et le centre de préférences Web existants en français ou arabe standard, puis faire vérifier l’affichage RTL, l’accessibilité et les traductions sur les appareils et navigateurs retenus. Le RTL existe dans les SDK ; sa validation auprès d’utilisateurs reste à faire. Ajouter darija seulement après validation linguistique.
5. Montrer accepter, refuser, personnaliser et rouvrir le centre de préférences sur le prototype. Vérifier la compréhension et les comportements attendus avec le client avant une POC.
6. Raccorder explicitement chaque script pris en charge à sa finalité. Le SDK Web peut appeler un démarrage et son nettoyage par `AmanCMP.registerPurposeHandler`; l’intégrateur doit raccorder et valider l’API réelle d’arrêt du fournisseur. ALAMANE ne peut pas annuler une donnée déjà transmise ni décharger universellement une bibliothèque exécutée.
7. Utiliser la console existante pour consulter organisations, propriétés, politiques, historique administratif, agrégats des événements reçus et exports CSV. Les événements de choix sont facultatifs et client-déclarés ; ils ne constituent pas une preuve de rendu, d’identité ou d’action réelle.
8. Configurer le pont `dataLayer` / Google Tag Manager déjà présent avec des déclencheurs qui attendent l’événement et la finalité applicable. Le conteneur, ses balises et le retrait propre à chaque fournisseur restent à configurer et vérifier par le client. Les connecteurs CMS restent secondaires pour cette cible.

### Pour le visiteur du site

- Lire une information courte dans la langue affichée, ouvrir les détails et exprimer son choix sans ambiguïté.
- Accéder plus tard à ses préférences pour les modifier ou retirer un choix.
- Voir les cookies et finalités configurés ; les décisions respectent les règles choisies par l’administrateur.

### Dérouler les canaux en étapes

- **Prototype Web présent :** politique versionnée, SDK, bannière et centre de préférences FR/AR, choix local, blocage des balises explicitement raccordées, pont GTM, remontée de décision facultative et crochet `AmanCMP.registerPurposeHandler` pour relier activation et nettoyage fournisseur. La politique est revalidée toutes les cinq minutes et au retour de l’onglet au premier plan ; une nouvelle version invalide le choix précédent. Le nettoyage effectif dépend encore de chaque fournisseur et doit être testé sur les scripts du périmètre. Restent l’intégration et la validation sur un domaine autorisé par un acheteur, l’accessibilité et les navigateurs retenus.
- **SDK mobiles de démarrage présents :** clients natifs iOS/Android et React Native avec UI FR/AR, choix local, chargement de politique et `registerPurposeHandler` pour raccorder le démarrage et le nettoyage des SDK tiers à l’état effectif. React Native recharge la politique au retour au premier plan ; les exemples natifs demandent à l’application hôte de recharger puis appeler `updatePolicy(...)`. La CI compile ou emballe les sources, mais aucune intégration dans une application cliente, validation sur appareil réel, matrice de compatibilité ou release signée n’est démontrée. Avant une POC mobile, intégrer dans une application de test autorisée, vérifier les versions/appareils, accessibilité, stockage, hors-ligne, révocation et cycle de vie des SDK tiers ; documenter séparément ATT iOS et déclarations Google Play.
- **Extension entreprise :** SSO, audit centralisé, environnements contrôlés et options de déploiement après les exigences de sécurité et d’hébergement du premier acheteur.

Garder hors première offre les CGV/CGU, conformité multi-pays automatisée, classification IA autonome, A/B testing, certification publicitaire IAB / Google et conseil juridique. Ne pas vendre à une banque tant que son exigence principale (SaaS, cloud privé ou on-premise) n’est pas techniquement et économiquement faisable.

## 5. Proposition de preuve de concept et tarification à tester

Pour les assureurs, banques et groupes, le libre-service mensuel à bas prix ne convient probablement pas au processus d’achat. Ne pas publier de tarif catalogue avant entretiens, revue de sécurité et calcul du coût de déploiement. Qualifier une preuve de concept Web limitée à une route de recette choisie par le client, avec durée, livrables, responsabilités et critères de réussite convenus à l’avance.

| Étape hypothèse | Contenu |
| --- | --- |
| Atelier de cadrage | Payant ou crédité sur la preuve de concept ; inventaire du domaine, critères de sécurité, cartographie des scripts et périmètre contractuel |
| Preuve de concept | 6 à 10 semaines, 1 domaine public, environnement isolé, intégration convenue, rapport des tests et recommandations de suite |
| Contrat entreprise | Tarification annuelle à devis selon domaines, volume, SLA, support, hébergement et exigences de déploiement |

### Unités de devis à valider avec les acheteurs

| Composante possible | Unité de travail | Garde-fou avant de la facturer |
| --- | --- | --- |
| Plateforme et gouvernance | Forfait annuel par organisation, avec paliers de propriétés Web et applications | Définir précisément ce qui compte comme propriété, environnement, marque et canal ; l’étiquette d’environnement du prototype ne sépare pas les déploiements |
| Consommation | Palier de pages vues ou visiteurs agrégés par propriété / canal | Ne l’ajouter qu’après une mesure fiable, un plafond et une règle de dépassement testés ; ALAMANE ne mesure pas aujourd’hui de façon suffisamment complète les affichages de bandeau pour fonder une facture d’usage |
| Intégration et migration | Forfait de lancement ou jours d’accompagnement bornés | Chiffrer les heures d’ingénierie, la complexité GTM/CMS/SDK et les systèmes tiers autorisés ; exclure tout accès ou travail hors périmètre signé |
| Hébergement, support et sécurité | Options de service distinctes, sur exigences écrites | Ne pas vendre hébergement dédié, résidence, SLA, SSO, astreinte ou certification tant que l’option n’est pas réellement disponible et vérifiable |
| POC | Prix fixe pour périmètre, durée, livrables et critères acceptés | Calculer le prix après qualification sur les coûts directs, la charge prévue et les achats du client ; le crédit sur contrat annuel reste à décider |

Préparer les offres en dirhams après les entretiens et le calcul du coût de service. Ne pas facturer selon le taux d’acceptation : il doit rester une mesure descriptive, sans incitation commerciale à orienter le choix du visiteur. La base de données actuelle n’est pas un compteur complet d’impressions et les événements de consentement sont facultatifs ; aucun tarif au volume ne peut donc être défendu à partir des seuls événements reçus.

**Repères concurrentiels publics (consultés le 8 octobre 2026, sans valeur de prix cible marocain) :** [consentmanager](https://www.consentmanager.net/en/pricing/) affiche 23 € / mois pour 100 000 vues mensuelles et 59 € / mois pour 1 million, puis un forfait entreprise sur devis ; son [comparatif](https://www.consentmanager.net/en/features/) indique respectivement un site, trois sites et une tarification entreprise personnalisée. [OneTrust](https://www.onetrust.com/pricing/) indique calculer le prix de son offre CMP sur la moyenne des visiteurs quotidiens agrégée entre canaux et propriétés et renvoie vers un devis. Le centre d’aide d’[Axeptio](https://support.axeptio.eu/fr/articles/274061-la-duree-de-mon-abonnement) précise que ses offres Entreprise et Agence sont annuelles ; les prix exacts ne sont pas publiés sur cette page. Les modèles varient selon le produit et le segment ; ces sources n’établissent ni la demande ni le budget acceptable au Maroc. Elles justifient seulement de tester un abonnement entreprise combinant propriétés et service, puis un indicateur de volume uniquement si ALAMANE peut le mesurer correctement. Pour le libre-service PME, garder une offre séparée à étudier plus tard. Ne publier aucun prix ALAMANE avant les entretiens avec les acheteurs et le calcul des coûts réels.

Valider le budget auprès de l’acheteur économique, pas uniquement de l’équipe produit. Éviter une POC gratuite non limitée qui se transforme en intégration personnalisée sans chemin d’achat.

## 6. Plan de lancement — premières 12 semaines

### Semaines 1–3 · découverte acheteur, sécurité et juridique

- Cartographier les rôles et le cycle de décision de 3 à 5 banques / grands groupes.
- Faire relire le modèle de données, la classification des cookies, les textes de bannière, les rôles et transferts par un juriste marocain spécialisé en protection des données.
- Obtenir une note claire sur le traitement opéré par ALAMANE, son éventuelle qualité de sous-traitant, l’hébergement, les formalités CNDP et les contrats à signer.
- Obtenir le questionnaire de sécurité fournisseur et les exigences minimales d’intégration d’au moins un prospect.
- Décider si un SaaS multi-tenant est acceptable, et sous quelles conditions, avant de construire le déploiement.
- Valider avec les équipes app un échantillon réel des SDK tiers et leur modèle d’initialisation / retrait, sans intégrer l’app de production en POC.

### Semaines 4–8 · tranche produit démontrable

- Obtenir les exigences d’hébergement, d’identité, d’exploitation et de sécurité d’au moins un acheteur ; valider le choix entre service dédié, SaaS mutualisé, cloud privé ou installation contrôlée avant de construire la cible.
- Avant toute exposition de l’API à un pilote, valider sur la cible les plafonds provisoires d’événements actifs (100 000 au total et 25 000 par propriété par défaut), la réponse `503` avec `Retry-After`, les alertes de capacité et le comportement des SDK à saturation. Les plafonds de lignes sont codés mais n’ont pas été testés sous charge et ne remplacent pas une limite d’octets ni le dimensionnement du stockage.
- Valider l’adaptateur PostgreSQL et les migrations sur une instance cible, avec deux organisations concurrentes, les rôles applicatifs prévus, les permissions DML minimales, TLS, secrets externalisés, sauvegardes/restauration et supervision ; le prototype refuse encore `AMAN_ENVIRONMENT=production`.
- Fermer les écarts de distribution Web/mobile après les exigences du premier acheteur : releases versionnées et signées, provenance vérifiable, matrice de compatibilité et procédure de mise à jour/retour arrière. Les artefacts actuels sont des previews ; l’APK Android est debug.
- Choisir et vérifier le mécanisme de signature / attestation après confirmation de la visibilité du dépôt et du plan GitHub. Les aperçus actuels ne sont protégés que par un manifeste SHA-256 placé dans le même artefact ; les attestations GitHub pour des dépôts privés exigent GitHub Enterprise Cloud selon la documentation officielle. Ne pas rendre le code public uniquement pour obtenir cette fonction.
- Transformer les parcours existants en kit pilote : guide d’installation, jeux de données fictifs, propriété démo, scripts d’exemple, et consignes de test sur une page ou application appartenant au client. Le scanner reste local et mono-page ; l’agrégation porte uniquement sur les rapports importés, sans crawl ni validation automatique des classements.
- Finaliser le parcours d’inventaire des informations CNDP ; le produit ne dépose aucune formalité au nom du client et ne fournit pas d’avis juridique.
- Maintenir le dossier fournisseur comme inventaire interne : architecture, flux et sous-traitants, hébergement/transferts, contrôle d’accès, chiffrement, sauvegardes, réponse aux incidents, SLA, tests de sécurité et continuité. Ne le transmettre qu’après revue interne et adaptation aux faits vérifiables.
- Préparer politique de confidentialité ALAMANE, conditions SaaS, accord de sous-traitance et support. Validation juridique nécessaire avant usage commercial.
- Le contrat partagé de politique et les trois intégrations SDK existent déjà ; garder leurs validations de schéma synchronisées et documenter séparément les règles de cookies, les permissions système et les SDK tiers.

### Semaines 9–12 · preuve de concept encadrée

- Pour le premier assureur, intégrer sur une seule route de recette de l’espace assuré, derrière l’authentification de test du client, avec son autorisation écrite et les approbations juridiques, sécurité et achats. À défaut de recette disponible, rester sur la maquette ALAMANE locale.
- Examiner les scripts avant/après chaque choix dans un navigateur de test ; corriger les écarts d’application et de retrait.
- Tester permissions, environnement isolé, journalisation, retrait, conservation et suppression avec les responsables concernés.
- Observer installation, erreurs, demandes de support, compréhension FR/AR et coûts de déploiement.
- Faire un point hebdomadaire avec le sponsor et documenter les écarts et décisions.

### Après la POC · décision de vente

- Présenter un rapport POC et une offre annuelle chiffrée selon le périmètre, l’hébergement, le support et le SLA.
- Obtenir la validation des équipes juridique, sécurité, achats et du sponsor métier.
- Ne pas ouvrir d’inscription publique pour cette cible avant la validation d’un modèle de déploiement réutilisable.
- Planifier une POC mobile dédiée seulement après accord du propriétaire de l’app, revue de sécurité et tests séparés des prompts de plateforme.

## 7. Acquisition et vente

1. Prospection nominative auprès des directions digitales, DPO, responsables de sécurité et achats des groupes ciblés.
2. Cartographier le comité d’achat et le processus d’homologation fournisseur dès le premier rendez-vous.
3. Démontrer la gouvernance multi-domaines, la configuration et l’audit sur un environnement factice ; ne pas scanner un site tiers sans accord.
4. Chercher un partenaire marocain en intégration, cybersécurité ou conseil vie privée pour renforcer le dossier fournisseur.
5. Vendre visibilité, contrôle des choix et gouvernance déployable ; ne pas utiliser la peur d’une sanction ou une promesse de conformité garantie.

La première liste de comptes et les signaux publics sont dans [PROSPECTION_BANQUES_MAROC.md](./PROSPECTION_BANQUES_MAROC.md). Elle distingue les publications vérifiables des hypothèses et ne remplace pas les entretiens de découverte.
Les brouillons d’approche et le tableau de suivi sont dans [SEQUENCE_PROSPECTION.md](./SEQUENCE_PROSPECTION.md) ; ils restent à personnaliser et n’ont pas été envoyés.

### Vérifications avant toute diffusion publique

- **Nom de travail « ALAMANE » :** la politique de cookies d’[Aman.com](https://www.aman.com/cookie-policy) appelle le mécanisme de ce site « Aman Cookie Consent tool » ; cela justifie une vérification sans prouver un conflit juridique. La vérification officielle du 8 octobre 2026 confirme que le [guide de dépôt OMPIC](https://marque.directompic.ma/assets/documents/guide.pdf) recommande de rechercher les marques nationales et les enregistrements internationaux désignant le Maroc ; l’[OMPIC](https://www.ompic.ma/fr) publie un catalogue officiel et renvoie à DirectOMPIC. Le [profil Maroc de l’OMPI](https://www.wipo.int/en/web/country-profiles/ma) référence une collection nationale de marques marocaines dans la Global Brand Database, mais l’accès au moteur a présenté un CAPTCHA pendant cette vérification. Aucun résultat de recherche exploitable n’a donc été obtenu pour « ALAMANE », « AL AMANE » ou « AMAN » ; la disponibilité n’est pas établie. Faire une recherche exacte et par variantes, vérifier les classes et services retenus avec un conseil en propriété industrielle, puis obtenir son avis avant campagne, contrat ou investissement important. Le nom reste provisoire et ne doit pas être présenté comme disponible ou protégé.
- **Contact commercial :** l’adresse `bonjour@aman.ma` n’a pas été vérifiée. La page [commercialisation.html](./commercialisation.html) propose désormais la consultation de la [fiche de cadrage pilote](./FICHE_CADRAGE_PILOTE.html), mais ne permet pas encore de contacter le porteur du projet. Vérifier le domaine, la boîte et la réception d’un message de bout en bout, ou remplacer par un contact validé, avant une campagne publique.
- **Présence en ligne :** vérifier disponibilité et droits d’usage des domaines et identifiants sociaux retenus après décision sur le nom. Ne pas interpréter la présence d’un domaine comme une autorisation d’utiliser une marque.

## 8. Mesures de décision

À mesurer pendant la preuve de concept :

- délai entre création de l’environnement et bannière opérationnelle ;
- part des installations appliquant correctement les choix sur chaque tag supporté ;
- écarts ou faux positifs du scanner, avec résolution ;
- temps nécessaire à la revue d’un changement par les équipes métier, DPO et sécurité ;
- demandes de support par domaine et coût réel de déploiement ;
- conversion POC → contrat annuel et raison de refus ;
- choix acceptés / refusés, comme mesure descriptive, pas comme objectif à maximiser au détriment d’un choix libre.

**Porte de passage au contrat annuel :** avis juridique reçu, exigences fournisseur et sécurité satisfaites, flux de données / hébergement documentés, parcours de choix et retrait vérifié, accord de sous-traitance disponible, suppression/export actif, critères de succès POC remplis et sponsor disposant d’un chemin d’achat signé ou daté.

## 9. Décisions encore ouvertes

- Sous-segment premier : banque, assurance ou grand groupe ; taille et exigences de sécurité diffèrent sensiblement.
- Hébergement au Maroc ou à l’étranger : aucune promesse avant avis CNDP sur les transferts et confirmation du fournisseur.
- Distribution des SDK au pilote : préparer par défaut un bundle versionné pour le dépôt d’artefacts approuvé par le client ; confirmer avec sa sécurité les signatures, SBOM, attestations de provenance et durées de conservation. Les aperçus GitHub Actions actuels ne durent que 14 jours et le dépôt source reste privé.
- Prix de la POC et du contrat annuel ; SLA, support et facturation.
- Nom « ALAMANE » : revue d’antériorité encore à faire ; voir les vérifications préalables à la diffusion publique.
- Niveau de prise en charge arabe et darija, après tests avec utilisateurs et traductions humaines.
- Moment où le premier acheteur accepte de poursuivre de la POC web à l’intégration des apps iOS et Android.
- Certifications / compatibilités à revendiquer uniquement après vérification des conditions et inscription officielle correspondante.

## Sources de départ

- [CNDP — Délibération D-939-2025 (PDF)](https://www.cndp.ma/wp-content/uploads/2025/12/Deliberation-N%C2%B0-D-939-2025-du-28112025-relative-au-modele-de-declaration-simplifiee-relative-au-traitement-des-donnees-a-caractere-personnel-de-cookies-sur-un-terminal.pdf)
- [CNDP — Adéquation des sites web à la loi 09-08](https://www.cndp.ma/ar/%D9%85%D9%84%D8%A7%D8%A1%D9%85%D8%A9-%D9%85%D9%88%D8%A7%D9%82%D8%B9-%D8%A7%D9%84%D8%A7%D9%86%D8%AA%D8%B1%D9%86%D8%AA/)
- [Axeptio — référence produit fournie](https://www.axept.io/fr/)
- [CMP Cookies — exemple public de packaging](https://cmpcookies.com/fr/)
- [consentmanager — exemple public de fonctionnalités et tarification](https://www.consentmanager.net/fr/tarification/)

Les outils concurrents cités sont des exemples de marché disponibles publiquement ; ils ne démontrent pas une validation de la demande au Maroc.
