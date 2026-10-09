# ALAMANE — support de découverte et de démonstration

**Version de travail · 9 octobre 2026**
**Premier prospect visé :** une compagnie d’assurance au Maroc
**Usage :** préparer un entretien exploratoire et une démonstration sur données fictives. Ce document n’est ni une offre contractuelle ni une déclaration de conformité ou de sécurité.

Pour les questions d’installation et de distribution des SDK, voir le [guide d’intégration pilote](./GUIDE_INTEGRATION_PILOTE.md). Le guide décrit l’état du prototype ; il ne représente pas une procédure de mise en production.

## Présentation en 30 secondes

ALAMANE est un projet de plateforme qui vise à aider les organisations à gouverner les préférences de consentement sur plusieurs sites et applications. Une console centralise les propriétés et les politiques versionnées ; des composants Web et mobiles appliquent les choix configurés par l’organisation. Nous cherchons à valider avec des équipes digitales, juridiques et sécurité les besoins d’intégration, d’approbation et de preuve avant de cadrer un pilote.

## À qui parler

Chercher un sponsor métier ou digital et, dès le premier échange, demander à inclure les rôles qui peuvent valider le pilote :

- responsable produit, digital ou canaux ;
- DPO / juridique ou responsable de la protection des données ;
- RSSI, architecture et achats fournisseurs ;
- équipes Web et mobiles qui contrôlent les tags et SDK tiers.

## Parcours de démonstration assurance — 20 minutes

Utiliser uniquement l’environnement local et des données fictives. Lancer `bash scripts/start-demo.sh --web-only` pour préparer la base dédiée au pilote Web assurance, la console locale et la maquette `demo-assurance.html`. Le script demande un compte administrateur local si nécessaire ; il refuse de toucher une base PostgreSQL et un port déjà occupé. Il crée une propriété Web de développement et un brouillon bilingue. Les finalités, durées et notices restent des exemples à remplacer et à faire valider par l’assureur. Pour montrer l’approbation à deux personnes, inviter un second compte de démonstration depuis la console, accepter l’invitation dans un autre profil, puis publier le brouillon avec ce second compte.

1. **Cadrer le problème (2 min).** Demander comment les finalités, tags et approbations sont actuellement répartis entre les domaines et équipes.
2. **Montrer le tableau de bord (2 min).** En session connectée, montrer l’organisation Assurance Démo, sa propriété Web et les actions conformité. Les décisions reçues sont agrégées et exportables seulement après activation explicite de la collecte ; la base dédiée ne contient aucun événement visiteur fictif injecté. Les chiffres d’inventaire affichés restent des exemples, pas un scan complet du portail.
3. **Montrer la politique et la gouvernance (6 min).** Ouvrir le brouillon Web FR/AR, expliquer que les finalités, durées, notices et états sont des exemples à faire valider par l’assureur. Modifier un champ, enregistrer une révision, puis montrer l’approbation par le second compte et l’historique. Ne pas présenter les textes d’exemple comme un avis juridique.
4. **Montrer la gouvernance (3 min).** Enregistrer un changement, afficher sa révision, puis montrer qu’un autre compte doit publier le brouillon lorsque la validation à deux personnes est activée. Avant publication, saisir le motif qui sera conservé dans le journal d’audit ; préciser qu’il documente l’action et ne prouve ni la revue réelle ni une validation juridique.
5. **Montrer l’expérience Web (4 min).** Ouvrir `demo-assurance.html?property=ID` avec l’identifiant de la propriété publiée. Montrer accepter, refuser, personnaliser, rouvrir et révoquer les préférences ; confirmer que les scripts locaux fictifs suivent le choix. Le lien en haut de page bascule le module entre français et arabe ; le reste de la page fictive demeure en français. Le bouton de réinitialisation est réservé aux essais locaux. Aucune balise tierce réelle n’est intégrée.
6. **Montrer la traçabilité (3 min).** Ouvrir l’historique d’administration et exporter son CSV. Garder la collecte des décisions désactivée pour la démonstration. Expliquer que si elle est autorisée et activée plus tard, les événements déclarés par le SDK ne prouveront ni identité, ni affichage, ni action réelle du visiteur.

Ne pas faire de démonstration live d’un portail client, d’un domaine tiers ou d’un SDK publicitaire réel sans autorisation et périmètre écrits. Les SDK mobiles compilent ou s’emballent dans la CI, mais n’ont pas été intégrés dans une application cliente ; ne pas les annoncer comme validés ou distribués.

## Questions de découverte

1. Combien de domaines, marques, applications et équipes doivent partager les mêmes règles ou les faire varier ?
2. Comment recensez-vous aujourd’hui les cookies, tags Web et SDK intégrés aux applications ? À quelle fréquence l’inventaire est-il revu ?
3. Qui décide et approuve une finalité ? Au-delà de la double validation déjà imposée pour une propriété de production, quelles approbations ou séparations d’environnement sont nécessaires ?
4. Quel comportement doit suivre chaque technologie quand le visiteur refuse, retire son choix ou n’a pas encore répondu ?
5. Quelles langues, exigences d’accessibilité et contraintes de marque s’appliquent aux parcours Web et mobile ?
6. Faut-il conserver une preuve de choix côté terminal, dans le SI du client ou dans un service central ? Quelles données seraient acceptables pour cette preuve ?
7. Quels fournisseurs, gestionnaires de tags, frameworks mobiles et parcours WebView doivent être intégrés en premier ?
8. Quelles exigences bloquent l’homologation d’un fournisseur : SSO, MFA, journaux, chiffrement, tests d’intrusion, continuité, hébergement ou sous-traitants ?
9. Quel modèle de déploiement est envisageable : service hébergé, tenant dédié, cloud privé ou installation contrôlée par le client ? Qui doit valider la résidence et les transferts de données ?
10. Qui détient le budget, quelle est la procédure d’achat et quelle date permettrait de prendre une décision après un pilote ?

À la fin, consigner le sponsor, les décideurs manquants, les critères de sécurité, le périmètre technique, le processus d’achat et la prochaine étape datée. Une conversation positive n’est pas à elle seule une validation du marché.

## Hypothèse de pilote assurance à discuter

Proposer, uniquement si le prospect confirme l’intérêt et après revue des équipes concernées, un pilote limité :

- **Durée indicative :** 6 à 10 semaines, à ajuster selon l’intégration et l’homologation ;
- **Périmètre initial :** une seule route de recette de l’espace assuré, derrière l’authentification de test du client, sur une origine approuvée par écrit et dans un environnement isolé ;
- **Données :** aucun compte assuré réel, numéro de contrat, sinistre, donnée de santé, identifiant de session ou secret de production ; comptes et données synthétiques ;
- **Travail conjoint :** établir l’inventaire accepté, configurer les finalités, intégrer les scripts autorisés, puis vérifier les comportements accepter/refuser/modifier et les changements publiés ;
- **Livrables à définir au contrat :** périmètre et responsabilités, compte rendu des écarts, résultats des vérifications convenues, effort d’intégration, exigences restant à satisfaire et recommandation de suite ;
- **Réussite :** critères écrits et acceptés par les deux parties avant le démarrage. La grille ci-dessous est une base de discussion, pas une promesse de résultat ; les seuils et moyens de preuve doivent être fixés selon le périmètre et l’environnement effectivement autorisés ;
- **Prix et achat :** prix fixe à chiffrer après qualification du périmètre, de l’hébergement, du support, des exigences de sécurité et des achats du client.

Ne pas démarrer sur une application de production ou avec des données personnelles tant que l’architecture, les responsabilités, le traitement, l’hébergement, les formalités et le contrat n’ont pas reçu les validations nécessaires.

### Grille de critères à convenir avant une POC

| Domaine | Mesure ou démonstration proposée | Preuve à conserver | Validation attendue |
| --- | --- | --- | --- |
| Périmètre et accès | Domaine, pages, environnements, rôles et technologies explicitement autorisés | Fiche de périmètre approuvée par le sponsor et les responsables techniques | Aucun système ou domaine hors périmètre n’est raccordé |
| Configuration et gouvernance | Création d’une politique, modification versionnée, approbation et publication par les personnes convenues, avec motif de publication enregistré | Révisions, motif saisi et entrées du journal d’administration exportés | Le client confirme que les étapes et responsabilités correspondent à son processus ; le motif ne constitue pas à lui seul une preuve de revue ou une validation juridique |
| Comportement des technologies | Pour chaque technologie de l’échantillon, vérifier démarrage, maintien et retrait selon les règles approuvées par le client | Matrice technologie × finalité × état, avec résultats observés et écarts | Chaque cas convenu a un résultat constaté et accepté par le responsable technique ; les exceptions sont consignées |
| Parcours visiteur | Afficher les parcours de choix et de modification dans les langues, navigateurs et tailles d’écran retenus | Fiche de vérification signée par les représentants désignés | Le client valide les textes et le comportement fonctionnel ; cette validation ne constitue pas un avis juridique |
| Intégration et effort | Mesurer le temps passé par les équipes et recenser les dépendances, changements et incidents d’intégration | Journal d’effort et liste d’obstacles | Les deux parties s’accordent sur les tâches et coûts restant à prévoir |
| Traçabilité technique | Montrer les versions publiées et l’historique administratif correspondant au scénario | Export de démonstration sur données fictives ou explicitement approuvées | Les informations nécessaires au processus interne du client sont présentes ; la trace ne prouve pas seule l’identité ou l’action du visiteur |
| Sécurité et exploitation | Vérifier les prérequis convenus dans l’environnement isolé et consigner tout écart ; aucun contrôle non exécuté n’est réputé réussi | Compte rendu daté des contrôles réellement effectués | Aucune donnée réelle n’est utilisée et aucun écart bloquant ne reste sans décision écrite |
| Décision de suite | Évaluer critères atteints, écarts, coûts, exigences fournisseurs et prochaines étapes | Décision conjointe de clôture ou plan de remédiation | Le sponsor confirme explicitement la suite, l’arrêt ou les conditions à remplir |

Avant signature, remplacer les formulations générales par des valeurs observables : versions de navigateur/appareil, technologies exactes, nombre de scénarios, rôles nommés, durée, responsables, seuils, exclusions et personne habilitée à accepter les résultats. Tout critère dépendant d’un service hébergé ou d’une intégration mobile est suspendu tant que cet environnement n’existe pas et n’a pas été autorisé.

## État produit à exprimer sans ambiguïté

| Élément | État actuel | Formulation à employer |
| --- | --- | --- |
| Console et API | Tranche locale avec organisations, rôles, transfert de propriété accepté par le destinataire, propriétés, politiques, validation à deux personnes configurable par organisation et imposée en production, motif de publication conservé dans l’audit et révocation auditée des invitations | « Nous pouvons démontrer le parcours sur environnement local. Le motif documente la publication, sans prouver la revue ou une validation juridique. » |
| Tableau de bord | Comptes de configuration réels en session ; agrégats Web disponibles seulement si l’intégrateur active la transmission ; chiffres intégrés de scan simulés ; imports JSON locaux limités aux propriétés Web et aux 20 derniers rapports | « Les comptes viennent de la configuration ALAMANE. La collecte des décisions est facultative. Le rapport d’inventaire est produit localement puis importé à la main ; l’équipe doit vérifier l’hôte et classer les résultats. » |
| SDK Web | Source de démonstration et tags fictifs | « Le flux Web se démontre sur nos pages factices ; l’intégration client reste à valider. » |
| SDK iOS, Android et React Native | CI privée : compilation de la bibliothèque Android et de l’exemple, compilation iOS pour simulateur, et compilation TypeScript/TSX puis packaging du tarball React Native à chaque push et pull request. Un aperçu AAR/APK debug n’est pas une release. Aucun SDK n’a été intégré dans une application acheteur, signé comme release ou distribué en environnement client. | « Nos bibliothèques iOS et Android se compilent dans notre CI, et notre paquet React Native est compilé et emballé. Ils restent à intégrer et valider sur vos versions et appareils cibles ; nous ne fournissons pas encore de release mobile signée. » |
| Événements de choix centralisés | Agrégats et export CSV des événements encore retenus après activation explicite Web ou appel natif ; aucune preuve d’identité, d’affichage ou de consentement juridique | « Nous pouvons montrer des compteurs client-déclarés après activation explicite. Leur modèle de preuve doit être défini avec le client et ses conseils. » |
| Hébergement et contrôles de production | Non disponibles dans cette tranche ; l’API refuse le mode production | « Aucun déploiement bancaire ou service de production n’est proposé aujourd’hui. » |
| Conformité | Aucune certification ou garantie portée par ALAMANE | « ALAMANE est un outil de configuration ; le client et ses conseils déterminent les règles applicables. » |

## Message d’introduction — brouillon à personnaliser

**Objet :** Échange sur la gouvernance du consentement Web et mobile

Bonjour [Prénom],

Je travaille sur ALAMANE, un projet de console destinée à centraliser la configuration et la gouvernance des choix de consentement sur plusieurs propriétés Web et mobiles. Je cherche à comprendre comment les grandes organisations gèrent aujourd’hui l’inventaire des technologies, l’approbation des changements et leur intégration avec les équipes digitales, juridiques et sécurité.

Seriez-vous disponible pour un échange exploratoire de 30 minutes ? Je peux vous montrer un démonstrateur local sur données fictives et recueillir vos critères, sans demander l’accès à vos systèmes ni à des données clients.

Bien cordialement,  
[Nom]

Ce texte est un brouillon. Il n’a pas été envoyé à un prospect.
