# ALAMANE — support de découverte et de démonstration

**Version de travail · 8 octobre 2026**
**Cible initiale :** banques et grandes entreprises au Maroc  
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

## Parcours de démonstration — 20 minutes

Utiliser uniquement l’environnement local avec des données fictives. Après avoir créé le premier admin et démarré les serveurs, lancer `python backend/seed_demo.py` pour préparer une organisation, une propriété Web locale et un brouillon fictifs. Depuis la console, inviter un second compte de démonstration et accepter l’invitation dans un autre profil de navigateur. Pendant la séance, un compte prépare le brouillon et le second le publie ; la validation à deux personnes est activée par défaut. Elle est imposée pour les propriétés étiquetées production, même si l’organisation la désactive pour le développement ou la recette.

1. **Cadrer le problème (2 min).** Demander comment les finalités, tags et approbations sont actuellement répartis entre les domaines et équipes.
2. **Montrer le tableau de bord (2 min).** En session connectée, montrer les comptes de configuration réels — organisations, propriétés, états de politiques et brouillons — puis filtrer par organisation. Les décisions reçues sont agrégées par propriété et exportables en CSV uniquement si la collecte a été activée ; la propriété préparée par le seed n’a aucun événement fictif injecté. Les chiffres de scan du tableau de bord sont simulés. Un outil séparé permet un inventaire ponctuel local sur une page ouverte et exporte un JSON. L’éditeur peut l’importer manuellement sur une propriété Web de la console locale ; ne pas importer d’URL ou d’inventaire client réel dans cette démo.
3. **Montrer la console (6 min).** Sélectionner l’organisation fictive préparée par le seed, montrer sa propriété de développement et son brouillon, expliquer ses finalités FR/AR, la durée configurée et les champs d’information fictifs à remplacer/faire valider par le client.
4. **Montrer la gouvernance (3 min).** Enregistrer un changement, afficher sa révision, puis montrer qu’un autre compte doit publier le brouillon lorsque la validation à deux personnes est activée.
5. **Montrer l’expérience Web (4 min).** Charger la page fictive de démonstration avec la propriété publiée ; accepter, refuser ou personnaliser ; rouvrir le centre de préférences. Si une nouvelle version est publiée pendant que la page reste ouverte, le SDK la revalide au retour de l’onglet au premier plan ou dans les cinq minutes et redemande un choix pour cette version. Les scripts utilisés sont locaux et fictifs.
6. **Montrer la traçabilité (3 min).** Ouvrir l’historique d’administration et exporter son CSV. Si la collecte a été activée pour la démonstration, exporter aussi le CSV des événements encore retenus et expliquer qu’il s’agit de déclarations du SDK, sans identité visiteur ni preuve d’affichage/action réelle. Sinon, ne pas fabriquer d’événements pour la séance.

Ne pas faire de démonstration live d’une app bancaire, d’un domaine tiers ou d’un SDK publicitaire réel sans autorisation et périmètre écrits. Les SDK mobiles compilent ou s’emballent dans la CI, mais n’ont pas été intégrés dans une application cliente ; ne pas les annoncer comme validés ou distribués.

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

## Hypothèse de pilote à discuter

Proposer, uniquement si le prospect confirme l’intérêt et après revue des équipes concernées, un pilote limité :

- **Durée indicative :** 6 à 10 semaines, à ajuster selon l’intégration et l’homologation ;
- **Périmètre initial :** un domaine Web public, non authentifié, environnement isolé et technologies convenues avec le client ;
- **Données :** aucune donnée bancaire, identifiant de compte, donnée réelle de visiteur ou secret de production ; politiques et événements de démonstration fictifs ;
- **Travail conjoint :** établir l’inventaire accepté, configurer les finalités, intégrer les scripts autorisés, puis vérifier les comportements accepter/refuser/modifier et les changements publiés ;
- **Livrables à définir au contrat :** périmètre et responsabilités, compte rendu des écarts, résultats des vérifications convenues, effort d’intégration, exigences restant à satisfaire et recommandation de suite ;
- **Réussite :** critères écrits à l’avance, par exemple le comportement observé pour chaque technologie du périmètre, le temps de revue par les équipes et la capacité à exporter l’historique administratif ;
- **Prix et achat :** prix fixe à chiffrer après qualification du périmètre, de l’hébergement, du support, des exigences de sécurité et des achats du client.

Ne pas démarrer sur une application de production ou avec des données personnelles tant que l’architecture, les responsabilités, le traitement, l’hébergement, les formalités et le contrat n’ont pas reçu les validations nécessaires.

## État produit à exprimer sans ambiguïté

| Élément | État actuel | Formulation à employer |
| --- | --- | --- |
| Console et API | Tranche locale avec organisations, rôles, transfert de propriété accepté par le destinataire, propriétés, politiques, validation à deux personnes configurable par organisation et imposée en production, journal d’administration et révocation auditée des invitations | « Nous pouvons démontrer le parcours sur environnement local. » |
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
