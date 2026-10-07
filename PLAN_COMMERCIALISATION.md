# ALAMANE — plan de commercialisation au Maroc

**Version de travail · 5 octobre 2026**
**Décision de départ :** valider une preuve de concept avec une grande entreprise ou une banque au Maroc. Les PME e-commerce et agences deviennent un segment d’expansion possible, pas le premier marché.

## 1. Le produit

ALAMANE aide les organisations à inventorier les technologies qui observent ou collectent des données sur leurs sites et dans leurs applications mobiles, expliquer leurs usages aux utilisateurs, recueillir et respecter leurs choix, et retrouver les paramètres et événements associés.

**Promesse de lancement :** « Une gestion du consentement compréhensible, adaptée aux sites marocains et gouvernable à l’échelle de plusieurs domaines. »

Ne pas promettre une conformité garantie, une certification CNDP ou un taux de consentement amélioré. Le responsable du traitement garde ses obligations. ALAMANE fournit des outils et de la traçabilité ; les règles applicables doivent être validées selon chaque traitement.

## 2. Clientèle de départ et problème à résoudre

### Segment pilote

- Banques et grands groupes marocains ayant plusieurs domaines, marques, parcours de connexion ou équipes digitales.
- Première vente à travailler avec un sponsor digital / produit, un DPO ou juriste, la sécurité informatique et les achats.

Le besoin à valider est une gouvernance centralisée : connaître les traceurs par domaine, traduire une politique en configuration qui respecte les choix des visiteurs, garder un historique exploitable, et prouver les changements aux équipes internes. Les exigences d’intégration, de sécurité, d’hébergement et de contractualisation peuvent être des critères d’achat bloquants.

Pour préparer le questionnaire fournisseur sans surpromettre, utiliser le [dossier de sécurité interne](./DOSSIER_SECURITE_FOURNISSEUR.md) comme inventaire de l’état actuel et des preuves manquantes. Ce document ne doit pas être transmis comme attestation ni comme preuve d’homologation.

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
- La décision indique que le consentement préalable n’est pas nécessaire pour certaines finalités décrites, sauf notamment pour la publicité personnalisée et le partage sur les réseaux sociaux. Elle demande aussi des moyens simples pour exprimer un refus et que ce choix soit respecté. Côté produit, `consentRequired=false` signifie donc « actif par défaut », pas « refus impossible » ; un refus explicite enregistré doit désactiver la finalité configurée. La classification elle-même reste à valider par le responsable et son conseil.
- L’information préalable doit identifier le responsable de traitement, les finalités, les catégories de données, les destinataires, les transferts à l’étranger et autorisations pertinentes, les coordonnées pour exercer les droits et les références de récépissés CNDP.
- La déclaration simplifiée prévue par la décision doit être faite par le responsable concerné avant le traitement entrant dans son champ. ALAMANE peut préparer un inventaire ou des éléments de travail, mais ne doit pas présenter le dépôt comme effectué à la place du client.
- La décision fixe une durée maximale de six mois pour les données de cookies qu’elle vise et pour la conservation du choix de consentement. Les transferts à l’étranger requièrent une autorisation préalable de la CNDP selon le texte.
- Les recommandations de la CNDP sur les sites rappellent aussi la notification des traitements et les formalités de transfert à l’étranger selon les cas.

**Conséquence produit :** ne pas coder une règle universelle « tout cookie non essentiel bloqué jusqu’à acceptation » comme conseil légal marocain. Le produit doit documenter la finalité et le réglage choisi, demander les informations de traitement manquantes et appliquer la règle configurée. Une revue juridique doit confirmer la classification des cas, les textes à jour et la responsabilité d’ALAMANE comme sous-traitant éventuel.

**Vérification des sources :** références officielles consultées le 5 octobre 2026. La [délibération D-939-2025](https://www.cndp.ma/wp-content/uploads/2025/12/Deliberation-N%C2%B0-D-939-2025-du-28112025-relative-au-modele-de-declaration-simplifiee-relative-au-traitement-des-donnees-a-caractere-personnel-de-cookies-sur-un-terminal.pdf) précise son champ par finalité, la durée maximale de six mois pour les données visées et le choix exprimé, l’information préalable, la déclaration correspondante et les transferts soumis à autorisation CNDP. La CNDP recense aussi la [procédure de notification relative à la gestion des cookies](https://www.cndp.ma/procedures-de-notification-process/) et sa page sur les [transferts de données à l’étranger](https://www.cndp.ma/transfert-de-donnees-a-letranger/). Ce relevé facilite la traçabilité du cadrage produit ; il ne constitue pas un avis juridique et doit être revu avant toute offre ou configuration client.

## 4. MVP vendable et périmètre final web + mobile

L’entrée [index.html](./index.html) redirige vers la console connectée [admin.html](./admin.html), qui s’ouvre sur une vue d’ensemble multi-organisation des comptes de configuration réels de la session : organisations, propriétés étiquetées développement / recette / production, politiques publiées, brouillons et actions administratives. Cette étiquette facilite le suivi mais ne garantit pas une isolation technique entre environnements. Le SDK Web peut transmettre sur activation expresse des décisions client déclarées ; les API clients natifs exposent aussi un appel explicite que l’application hôte doit activer. La console agrège les événements reçus sur 30 jours et permet d’exporter les événements encore retenus en CSV par propriété. Ces événements sont des déclarations du SDK : ils ne certifient pas l’identité du visiteur, l’affichage d’un écran ou l’action réelle et ne constituent pas à eux seuls une preuve juridique. Le [scanner local](./scanner-tool.html) observe une page courante, signale les marqueurs ALAMANE directs repérés dans les scripts, permet un classement manuel et télécharge un rapport JSON ; ce signal DOM ne prouve pas que tous les déclenchements sont contrôlés et ne remplace pas l’inspection des gestionnaires comme GTM. Un éditeur peut importer explicitement le rapport sur une propriété Web, où les 20 derniers imports sont conservés et peuvent être supprimés. Le scanner ne parcourt pas un site entier : les scans consolidés multi-page restent à construire. Les SDK Android, iOS et React Native disposent désormais d’étapes de compilation ou de packaging CI ; aucun n’a été éprouvé dans l’application d’un acheteur, signé comme release ou distribué en environnement client. La première preuve de concept bancaire peut démarrer sur un domaine web public pour réduire le périmètre de sécurité ; l’intégration mobile reste une étape à valider avant une offre omnicanale.

L’architecture du produit et le format commun des politiques sont décrits dans [ARCHITECTURE.md](./ARCHITECTURE.md) et [schemas/consent-policy.schema.json](./schemas/consent-policy.schema.json). L’éditeur conserve la notice historique et ajoute des champs séparés FR/AR ; le SDK Web et les SDK natifs choisissent le texte selon la langue affichée. Les SDK iOS et Android disposent d’une compilation CI ; le package React Native est transpilé en JavaScript et emballé dans la CI. Ce sont des bases de pilote, pas encore des bibliothèques intégrées chez un client, signées comme releases ou prêtes à distribuer en production.

### Pour l’administrateur

1. Créer une organisation, des environnements et des domaines ; gérer les rôles d’administrateur, d’éditeur et de lecteur.
2. Renseigner identité du responsable de traitement, contact, finalités et notice FR/AR, règles d’activation, fournisseurs associés, catégories de données, destinataires et références CNDP. Le client fournit et fait relire les contenus dans les langues qu’il propose. Les fournisseurs sont affichés à titre indicatif dans l’interface visiteur ; le client doit raccorder et vérifier chaque script ou SDK à l’identifiant de finalité correspondant.
3. Détecter les cookies et scripts présents, proposer une classification modifiable et dater les scans. Chaque résultat doit être revu par le client avant activation.
4. Concevoir une bannière FR / AR, avec affichage RTL vérifié sur appareil mobile. Ajouter darija après validation de traduction et compréhension utilisateur.
5. Afficher des choix compréhensibles, permettre la personnalisation et rouvrir le centre de préférences.
6. Appliquer les choix aux scripts configurés et produire une preuve minimale, horodatée, versionnée et exportable.
7. Voir l’historique, le dernier scan, la configuration publiée et la durée de conservation.
8. Ajouter une intégration contrôlée à Google Tag Manager / dataLayer, après validation de l’architecture du groupe. Les connecteurs CMS restent secondaires pour cette cible.

### Pour le visiteur du site

- Lire une information courte dans la langue affichée, ouvrir les détails et exprimer son choix sans ambiguïté.
- Accéder plus tard à ses préférences pour les modifier ou retirer un choix.
- Voir les cookies et finalités configurés ; les décisions respectent les règles choisies par l’administrateur.

### Dérouler les canaux en étapes

- **Tranche web POC :** politique versionnée, SDK web, bannière, état enregistré, contrôle de scripts pris en charge, et test sur domaine public non authentifié.
- **Tranche mobile :** SDK iOS et Android qui exposent un état local/hors-ligne, un UI natif accessible et des callbacks d’état effectif après choix ou changement de politique ; documenter l’ATT iOS et les déclarations Google Play séparément. Le SDK informe les intégrateurs et ne peut pas décharger magiquement un SDK tiers déjà initialisé.
- **Extension entreprise :** SSO, audit centralisé, environnements contrôlés et options de déploiement après les exigences de sécurité et d’hébergement du premier acheteur.

Garder hors première offre les CGV/CGU, conformité multi-pays automatisée, classification IA autonome, A/B testing, certification publicitaire IAB / Google et conseil juridique. Ne pas vendre à une banque tant que son exigence principale (SaaS, cloud privé ou on-premise) n’est pas techniquement et économiquement faisable.

## 5. Proposition de preuve de concept et tarification à tester

Pour les banques et groupes, le libre-service mensuel à bas prix ne convient probablement pas au processus d’achat. Ne pas publier de tarif catalogue avant entretiens, revue de sécurité et calcul du coût de déploiement. Tester une preuve de concept cadrée sur un domaine public / non authentifié, avec prix fixe, durée, livrables, responsabilités et critères de succès convenus à l’avance.

| Étape hypothèse | Contenu |
| --- | --- |
| Atelier de cadrage | Payant ou crédité sur la preuve de concept ; inventaire du domaine, critères de sécurité, cartographie des scripts et périmètre contractuel |
| Preuve de concept | 6 à 10 semaines, 1 domaine public, environnement isolé, intégration convenue, rapport des tests et recommandations de suite |
| Contrat entreprise | Tarification annuelle à devis selon domaines, volume, SLA, support, hébergement et exigences de déploiement |

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

- Compléter le socle local déjà réalisé (organisations, rôles, propriétés, politiques versionnées, API de diffusion et journal administratif) par une persistance et une exploitation adaptées au pilote après choix de déploiement et revue des exigences acheteur.
- Implémenter la bannière et le centre de préférences, le respect des choix par les tags pris en charge, le journal de preuve, la suppression / anonymisation selon les durées retenues.
- Créer un script d’installation et un parcours guidé pour les informations CNDP.
- Préparer un dossier fournisseur : architecture, flux et sous-traitants, hébergement/transferts, contrôle d’accès, chiffrement, sauvegardes, réponse aux incidents, SLA, tests de sécurité et continuité.
- Préparer politique de confidentialité ALAMANE, conditions SaaS, accord de sous-traitance et support. Validation juridique nécessaire avant usage commercial.
- Figer le contrat de politique partagé entre le tableau de bord, le SDK web et les SDK mobiles ; une règle n’est pas supposée identique entre une catégorie de cookies et une permission native.

### Semaines 9–12 · preuve de concept encadrée

- Déployer sur un domaine public non authentifié d’une institution, seulement après approbations juridique, sécurité et achat.
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

- **Nom de travail « ALAMANE » :** la politique de cookies d’[Aman.com](https://www.aman.com/cookie-policy) appelle le mécanisme de ce site « Aman Cookie Consent tool » ; elle ne désigne pas le produit comme « ALAMANE ». Cette proximité de nom justifie une vérification, mais ne prouve ni un conflit juridique ni l’existence d’une marque enregistrée au Maroc. La recherche d’antériorité OMPIC n’a pas été effectuée. Le guide officiel OMPIC recommande de rechercher dans les bases des marques nationales et des enregistrements internationaux désignant le Maroc ([guide du dépôt de marque](https://marque.directompic.ma/assets/documents/guide.pdf)). Rechercher « ALAMANE », « AL AMANE », « AMAN » et les variantes pertinentes pour les classes et services envisagés, puis demander une revue de marque au Maroc et dans les marchés visés avant campagne, contrat ou investissement important. Ne pas lancer publiquement le nom avant cette vérification.
- **Contact commercial :** l’adresse `bonjour@aman.ma` n’a pas été vérifiée. Le bouton de la page [commercialisation.html](./commercialisation.html) est désactivé et indique que l’adresse doit être confirmée. Vérifier le domaine, la boîte et la réception d’un message de bout en bout, ou remplacer par un contact validé, avant de diffuser la page.
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
