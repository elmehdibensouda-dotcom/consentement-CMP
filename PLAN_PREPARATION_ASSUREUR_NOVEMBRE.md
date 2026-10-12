# ALAMANE — préparation du pilote avec un assureur

**Document interne de pilotage — 9 octobre 2026**  
**Cible :** présentation début novembre 2026, fenêtre de travail proposée du 2 au 6 novembre (date client à confirmer).  
**Périmètre retenu :** une propriété Web de recette intégrée dans une page de test de l’espace assuré, même si cette page est derrière une authentification de recette.

## Définition du résultat attendu

Être capable de présenter le parcours ALAMANE dans une page d’espace assuré de test et de remettre à l’équipe Web du prospect un extrait d’intégration reproductible. Le test reste limité à une route de recette, des comptes et données fictifs, une origine autorisée et une politique validée par le prospect. La démonstration ne doit pas être décrite comme un déploiement de production ni comme une conformité juridique garantie.

Le SDK Web est le canal du premier pilote. iOS, Android et React Native restent hors du périmètre de novembre, sauf démonstration ultérieure distincte. Les événements centralisés sont désactivés jusqu’à décision écrite du prospect et revue DPO/juridique.

## État vérifié au 9 octobre

- **Disponible localement :** console multi-organisation, propriétés Web, politiques bilingues FR/AR, brouillons et approbation, journal d’audit, SDK Web et page de démonstration fictive.
- **Amélioré dans le dépôt pendant cette préparation :** tableau des propriétés à défilement horizontal ; bloc « Actions conformité prioritaires » qui ouvre la politique concernée. La navigation vers l’éditeur a été vérifiée dans le navigateur local.
- **Amélioré pour l’assurance :** le seed produit une notice arabe cohérente avec une entité d’assurance ; l’image locale de préproduction inclut la page `demo-assurance.html` et son contrôle de santé a une syntaxe Docker valide.
- **Kit d’intégration Web préparé :** extrait avec nonce CSP, exemple de directives `script-src` / `style-src` / `connect-src` et retour arrière par route ; à faire relire et tester par la sécurité du client dans son environnement avant usage.
- **QA partielle :** 19 tests API passent sur une base temporaire isolée ; les contrôles de syntaxe du SDK Web et du scanner passent. Le build Docker local réussit et le contenu du paquet a été vérifié. Dans le navigateur local, les parcours accepter, refuser, personnaliser, rouvrir et retirer le choix ont été exercés en français, et le module arabe RTL a été contrôlé. Les états des scripts fictifs suivent ces choix. Deux défauts de la maquette locale ont été corrigés (état après refus, ouverture du centre sans politique distante). Le parcours navigateur n’est pas encore automatisé et l’intégration assureur n’est pas testée.
- **Non prêt pour un client :** pas de service hébergé, HTTPS public, environnement isolé, base PostgreSQL réelle, sauvegarde/restauration démontrée, supervision, SSO/MFA ou test de sécurité indépendant. Le mode production du serveur est volontairement refusé.
- **Pas encore démontré :** intégration dans l’espace assuré du prospect, revue de ses équipes Web/sécurité/DPO, autorisation du domaine, tests d’acceptation sur son environnement et décision relative à l’hébergement et à la collecte.

## Plan de travail et portes de décision

| Fenêtre cible | Travail | Preuve de sortie | Responsable principal |
| --- | --- | --- | --- |
| 9–13 oct. | Cadrer une page et une seule origine de recette avec le prospect ; confirmer sponsor digital, équipe Web, DPO/juridique et sécurité ; demander CSP, accès test et modèle d’hébergement accepté. | Fiche de périmètre : URL, route, testeurs, données exclues, fenêtre, retour arrière et contacts. | ALAMANE + prospect |
| 12–16 oct. | Stabiliser la démonstration Web assurance : écran de portail fictif, policy publiée de test, code SDK exact, instructions CSP et retour arrière ; distinguer clairement démonstration locale et test client. | Démo locale rejouable et bundle/source datés, avec empreintes. | ALAMANE |
| 19–23 oct. | Si le prospect fournit son environnement et autorise le test : intégrer sur une route de recette protégée, avec faux comptes et traceurs fictifs ; garder la collecte centrale désactivée par défaut. Sinon, ne pas brancher son domaine et préparer une répétition sur le portail simulé. | Capture/version et journal de scénarios, autorisation écrite si intégration chez le prospect. | Prospect Web + ALAMANE |
| 26–30 oct. | Exécuter les scénarios, corriger les défauts bloquants, revoir le dossier sécurité et répéter la présentation. | Résultats accepter/refuser/personnaliser/révoquer, FR/AR, nouvelle version, indisponibilité réseau, CSP et retrait ; limites et écarts consignés. | ALAMANE + prospect |
| 2–6 nov. | Présenter le produit et proposer la prochaine étape convenue. | Démonstration reproductible, kit d’intégration, décisions et prérequis documentés. | ALAMANE |

Les dates ci-dessus sont des cibles de préparation, pas des rendez-vous confirmés. L’intégration réelle dans le portail dépend de l’accès à une recette, d’une origine approuvée et d’une fenêtre convenue avec le prospect.

## Critères de sortie pour la présentation

- La bannière s’affiche dans le portail fictif ou la route de recette approuvée et ne lit aucune donnée de session/contrat/assuré.
- Accepter, refuser, personnaliser, rouvrir et révoquer produisent les états attendus ; les scripts optionnels fictifs suivent les choix et l’arrêt est observé.
- Le choix reste local ; aucune transmission centrale de décision ni aucune balise tierce réelle n’est activée par défaut.
- Une nouvelle politique et l’absence d’une politique valide ont un comportement compréhensible et documenté.
- L’équipe peut copier l’extrait, appliquer les directives CSP nécessaires et retirer l’intégration par retour arrière.
- La console indique ses limites : un événement SDK reçu ne prouve ni identité de l’assuré, ni affichage de la bannière, ni application réelle du choix.
- Les responsables du prospect valident textes, finalités, conservation, traitement et formalités qui les concernent.

## Blocages qui empêchent un pilote hébergé réel

1. Le dépôt n’a pas d’environnement Web HTTPS public ou accessible au prospect ; le serveur actuel est un démonstrateur local.
2. L’hébergement et la résidence de données ne sont pas décidés avec le prospect ; aucune base de données hébergée n’a été validée.
3. L’autorisation d’injecter le SDK, la route de recette, la politique de contenu/CSP, les testeurs et le mécanisme de retour arrière ne sont pas connus.
4. Le dossier sécurité décrit des écarts encore ouverts : sauvegardes/restauration, supervision, revue de sécurité indépendante, réponses aux exigences fournisseur et contrôles d’exploitation.
5. Le choix de collecte d’événements doit être fixé avec le prospect. Le réglage sûr pour la première présentation est de ne transmettre aucun événement visiteur.

Si les conditions d’accès et de sécurité du prospect ne sont pas satisfaites avant la fenêtre d’intégration, la présentation montrera le portail fictif et l’extrait d’intégration ; elle ne revendiquera pas un essai dans le système du prospect.

## Documents de référence

- [Kit de test Web dans l’environnement du client](./PILOTE_CLIENT_WEB.md)
- [Déroulé de démonstration pour un assureur](./SCRIPT_DEMONSTRATION_ASSUREUR.md)
- [Préparation d’un pilote Web fermé](./PILOTE_WEB_FERME.md)
- [Guide d’intégration du pilote](./GUIDE_INTEGRATION_PILOTE.md)
- [Dossier de sécurité fournisseur — état interne](./DOSSIER_SECURITE_FOURNISSEUR.md)
- [Plan de commercialisation Maroc](./PLAN_COMMERCIALISATION.md)
