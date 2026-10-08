# ALAMANE — fiche de découverte CIH BANK

**Document interne · 8 octobre 2026 · À compléter après un entretien autorisé**
**But :** vérifier si un problème réel de gouvernance des choix Web justifie un pilote exploratoire. Ce document ne présume ni d’un besoin de CIH BANK, ni d’un intérêt d’achat.

## Signal public et hypothèse à tester

Le dossier de prospection relève deux signaux publics : le rapport ESG 2024 évoque la transformation digitale et la protection des données clients ; une offre de chef de projet digital publiée le 30 septembre 2026 décrit l’évolution de parcours et de l’application mobile. Ces faits indiquent une activité digitale, pas un projet de CMP ni une intention d’achat.

**Hypothèse de découverte :** commencer par demander comment un parcours Web public et non authentifié est inventorié, gouverné et relié aux technologies de mesure ou de marketing. N’élargir au mobile qu’après avoir confirmé un besoin et identifié les équipes applicatives concernées.

Sources consignées dans le [dossier de prospection](./PROSPECTION_BANQUES_MAROC.md) : [rapport ESG CIH 2024](https://www.cihbank.ma/sites/default/files/2025-04/Rapport_ESG_CIH_2024.pdf), [offre de chef de projet digital](https://recrutement.cihbank.ma/1092_offre-emploi-chef-de-projet-digital.html). Vérification documentaire datée du 8 octobre 2026 ; revérifier les pages avant toute présentation externe.

## Résultat attendu de l’entretien

À la fin des 30 minutes, pouvoir répondre aux questions suivantes avec les mots du prospect :

1. Existe-t-il un problème actuel concernant l’inventaire, l’approbation ou l’application des choix de consentement ?
2. Qui en est responsable et qui peut porter un pilote ?
3. Quel premier domaine et quelles technologies peuvent être étudiés avec autorisation ?
4. Quelles exigences sécurité, hébergement, juridique et achats bloquent ou conditionnent le pilote ?
5. Quelle est la prochaine étape convenue, avec un responsable et une date ?

## Participants à réunir

- Sponsor ou responsable produit, digital ou canaux ;
- équipe Web qui contrôle les pages, tags et gestionnaire de balises ;
- DSI / architecture et RSSI ;
- DPO / juridique ;
- achats fournisseurs si l’intérêt et le processus de référencement le justifient.

Demander au premier interlocuteur quels rôles doivent participer. Ne rechercher ni ne nommer des personnes sans source autorisée.

## Déroulé proposé — 30 minutes

| Temps | Sujet | Ce qu’il faut apprendre |
| --- | --- | --- |
| 0–3 min | Contexte et objectif | Confirmer que l’échange porte sur une difficulté actuelle, pas seulement sur une présentation produit. |
| 3–12 min | Pratiques actuelles | Cartographier équipes, domaines, inventaire, technologies, validations et fréquence de revue. |
| 12–19 min | Conséquences et priorité | Comprendre les erreurs, retards, doublons, risques ou coûts effectivement observés et leur priorité. |
| 19–24 min | Conditions d’intégration | Identifier les exigences de sécurité, hébergement, identité, données, retrait des SDK et achats. |
| 24–28 min | Démonstration facultative | Si elle est souhaitée, montrer uniquement le parcours local fictif et ses limites indiquées ci-dessous. |
| 28–30 min | Décision de suite | Obtenir une étape précise, un propriétaire, une date et les participants nécessaires. |

## Questions de qualification

### Problème, processus et impact

- Comment les cookies, tags et SDK facultatifs sont-ils inventoriés aujourd’hui sur les parcours publics ?
- Qui propose, valide et modifie les finalités et les textes ? Comment les changements sont-ils reliés aux équipes qui déploient les tags ?
- Le processus varie-t-il selon les marques, domaines ou équipes ? Où observez-vous des reprises, retards ou erreurs ?
- Quand le visiteur modifie ou retire un choix, quelles actions les équipes attendent-elles de chaque technologie ? Comment vérifiez-vous le résultat ?
- Quel événement récent a rendu ce sujet prioritaire ? Quel indicateur ou coût permettrait de mesurer une amélioration ?

### Périmètre et intégration

- Un domaine Web public non authentifié peut-il servir de périmètre de découverte ? Qui peut autoriser son examen ?
- Quel gestionnaire de balises et quels outils de mesure ou marketing seraient dans le premier échantillon ?
- Comment les scripts facultatifs sont-ils initialisés, arrêtés ou désactivés après un retrait ? Quelles limites techniques sont connues ?
- Le mobile est-il un besoin confirmé dès le départ, ou une étape ultérieure ? Quels frameworks, versions et équipes seraient concernés ?
- Quelles langues et exigences d’accessibilité faut-il examiner avec les équipes concernées ?

### Sécurité, données et achat

- Quelles exigences sont éliminatoires pour un nouvel outil : SSO/MFA, audit, chiffrement, test d’intrusion, continuité, SLA ou clauses fournisseur ?
- Quels modes d’hébergement sont recevables et qui décide de la région, des transferts et des sous-traitants ?
- Les choix doivent-ils rester sur l’appareil, être conservés par CIH ou être transmis à une plateforme ? Quelle minimisation serait requise ?
- Quel est le processus d’homologation fournisseur, ses étapes et son délai typique ?
- Qui détient le budget, quelle ligne pourrait financer une POC et quelle date de décision est réaliste ?

## Démonstration autorisée à proposer

La démonstration est facultative. Elle doit se dérouler sur l’environnement local avec des données, politiques, comptes et tags fictifs, sans accès à un domaine, une application ou un système CIH. Montrer la console multi-organisation, une politique fictive, la revue à deux personnes, puis le parcours accepter / refuser / personnaliser sur le site de démonstration.

Dire explicitement que :

- l’API et la console restent locales ; aucun service hébergé de production n’est proposé ;
- le parcours Web doit encore être intégré et validé sur un domaine acheteur ;
- les SDK mobiles compilent ou s’emballent en CI, mais ne sont pas intégrés dans une application cliente et ne sont pas distribués en release signée ;
- l’arrêt d’un SDK tiers déjà initialisé dépend de son intégration côté application ;
- les événements centralisés sont facultatifs et client-déclarés ; ils ne prouvent pas l’identité, l’affichage ou l’action du visiteur ;
- ALAMANE n’apporte ni garantie de conformité ni avis juridique ; les règles et textes doivent être validés par le responsable et ses conseils.

Ne pas importer d’inventaire CIH, saisir de données réelles, utiliser des identifiants CIH ou présenter les statistiques simulées comme des mesures client.

## Fiche de notes après entretien

| Champ | Notes factuelles — séparer les propos du prospect de nos hypothèses |
| --- | --- |
| Date, format et participants par fonction |  |
| Problème actuel confirmé (citation courte ou résumé fidèle) |  |
| Processus et outils actuellement utilisés |  |
| Domaines / canaux potentiellement concernés |  |
| Technologies prioritaires et comportement attendu après refus / retrait |  |
| Impact constaté et indicateur de succès souhaité |  |
| Sponsor métier et décideurs encore absents |  |
| Exigences sécurité / hébergement / juridique / achats |  |
| Budget, ligne budgétaire et calendrier confirmés ou inconnus |  |
| Périmètre de découverte autorisé par écrit, le cas échéant |  |
| Prochaine étape, responsable et date |  |
| Objections, inconnues et hypothèses à invalider |  |

## Règle de qualification

Ne faire passer CIH BANK au statut d’opportunité que si un interlocuteur confirme un problème actuel, un sponsor, un chemin d’achat, des exigences fournisseur, un périmètre autorisable et un budget ou une ligne budgétaire. Une réunion, une offre d’emploi liée au digital ou une publication institutionnelle ne constituent pas une validation du besoin.

Après l’entretien, classer chaque critère **confirmé**, **infirmé** ou **inconnu**, puis décider : poursuivre la découverte, préparer un cadrage écrit de pilote, ou arrêter. Ne pas proposer une POC mobile ou hébergée tant que l’environnement et les validations nécessaires ne sont pas disponibles.

## Sources et couverture

- **Sources utilisées :** dossier interne de prospection et signaux publics CIH BANK cités plus haut, consignés au 8 octobre 2026 ; plan de commercialisation et support de découverte ALAMANE.
- **Couverture :** préparation à un entretien avec CIH BANK uniquement. Aucun contact, besoin, budget, décideur ou processus d’achat n’a été confirmé ; aucune personne n’a été recherchée ou contactée.
- **Étape suivante :** obtenir un entretien exploratoire via un canal professionnel autorisé, puis compléter cette fiche avec des faits attribués à leur source.
