# ALAMANE — déroulé de démonstration pour un assureur

**Document interne · version de préparation du 10 octobre 2026**
**Durée conseillée :** 12 minutes dans un rendez-vous de découverte de 30 minutes.
**Périmètre :** console locale et espace assuré fictif, données synthétiques, SDK Web. Ce déroulé ne constitue ni une recette client ni une démonstration d’hébergement de production.

## Résultat recherché

Montrer comment une équipe configure une politique, fait relire une publication, présente un choix au visiteur et relie ce choix aux technologies optionnelles d’une page Web. À la fin, demander au prospect si ce parcours répond à un problème réel et quelles équipes devraient cadrer une éventuelle route de recette.

## Préparation avant le rendez-vous

1. Vérifier que le navigateur affiche les pages locales ALAMANE et que l’API de démonstration est démarrée. Depuis la racine du dépôt :

   ```sh
   bash scripts/start-demo.sh --web-only
   ```

2. Ouvrir les adresses de console et de démonstration annoncées par le script. Utiliser uniquement le compte local de démonstration créé ou configuré sur cette machine ; ne jamais afficher ni transmettre son mot de passe.
3. Confirmer que l’organisation et la propriété visibles portent des noms fictifs et que la propriété de démo est de canal Web.
4. Garder ouverte la page [demo-assurance.html](./demo-assurance.html), sans paramètre pointant vers une propriété client. Elle utilise des textes et scripts fictifs locaux.
5. Si la publication à deux personnes est montrée, préparer deux comptes locaux de démonstration et une politique fictive. Sinon, présenter l’écran de gouvernance sans prétendre qu’une politique est publiée.
6. Fermer les autres onglets, notifications et outils contenant des données privées. Ne pas ouvrir de domaine ou de compte du prospect.

Si un service local ne répond pas ou si la politique de démonstration n’est pas prête, utiliser la page fictive en mode aperçu et expliquer que la partie console/API n’est pas disponible à cet instant. Ne pas improviser avec des identifiants ou données réels.

## Déroulé proposé

### 0–2 min — cadrer la démonstration

Dire : « Je vais vous montrer un prototype local avec des données fictives. Il ne se connecte pas à vos systèmes, ne reçoit aucune donnée d’assuré et n’est pas un service de production. L’objectif est de recueillir vos critères pour savoir si un pilote Web limité aurait du sens. »

Confirmer que le prospect souhaite voir la démonstration avant de partager l’écran.

### 2–5 min — configurer et gouverner une propriété

Dans la console :

1. Sélectionner l’organisation fictive.
2. Ouvrir la propriété Web de démonstration et montrer son identifiant comme référence de configuration publique, pas comme secret.
3. Montrer les finalités et leur état initial, puis préciser que leur qualification et les textes doivent être validés par le responsable de traitement et ses conseils.
4. Montrer la revue/publication à deux personnes si le scénario préparé le permet. Expliquer que le journal trace des actions de configuration ; il ne prouve pas à lui seul la validité juridique d’une politique ni l’identité du visiteur.

Ne pas présenter les rapports ou événements d’exemple comme des données client, des mesures réelles ou une preuve de consentement.

### 5–9 min — suivre le parcours visiteur

Sur l’espace assuré fictif :

1. Montrer le panneau en français, les catégories facultatives et les informations de traitement d’exemple.
2. Ouvrir les préférences, enregistrer un choix personnalisé puis revenir au panneau.
3. Montrer que les indicateurs « mesure d’audience » et « publicité personnalisée » suivent le choix sur cette page. Ce sont des scripts locaux qui affichent un état ; aucun fournisseur tiers n’est appelé.
4. Passer en arabe avec le lien de langue et montrer le sens de lecture RTL.
5. Si le temps le permet, utiliser « Recommencer le parcours de consentement » pour retirer le choix local de cette propriété fictive, puis vérifier que l’état revient à l’attente du choix.

Dire que l’application réelle d’un retrait aux SDK dépend de l’intégration et des mécanismes d’arrêt de chaque fournisseur. ALAMANE ne peut pas annuler une donnée déjà envoyée.

### 9–11 min — expliquer l’intégration

Montrer l’extrait Web correspondant dans la console ou dans le [guide d’intégration](./SDK_WEB.md). Résumer : l’équipe cliente héberge le fichier sur un domaine qu’elle contrôle, déclare l’origine et relie chaque finalité à ses propres scripts. Le client décide séparément s’il transmet des événements au serveur ; cette remontée est désactivée par défaut dans le scénario Web.

Préciser qu’un identifiant de propriété n’est pas un secret et qu’une intégration chez le prospect nécessite une origine et une route de recette autorisées, HTTPS, une revue CSP/sécurité et un mécanisme de retour arrière convenu.

### 11–12 min — passer à la découverte

Poser ces questions, puis laisser le prospect décrire son processus :

- Comment les équipes inventorient-elles et valident-elles aujourd’hui les tags ou SDK facultatifs ?
- Quel serait le périmètre le plus petit et le plus représentatif pour évaluer le parcours Web ?
- Qui doit examiner l’intégration : équipe Web, sécurité, DPO/juridique, architecture et achats ?
- Quelles exigences d’hébergement, d’identité, de données, de preuve et de retrait sont éliminatoires ?
- Quelle serait la prochaine étape utile, avec un responsable et une date ?

Consigner les réponses comme des propos du prospect, en distinguant les faits, les hypothèses et les inconnues. Ne pas enregistrer ni envoyer de données sans son accord.

## Réponses courtes aux questions prévisibles

| Question | Réponse à donner |
| --- | --- |
| « Est-ce déjà installé chez nous ? » | « Non. La démonstration est locale et fictive. Aucune intégration chez vous n’a été réalisée. » |
| « Est-ce prêt pour la production ? » | « Non. Il n’y a pas encore de service de production hébergé et durci, ni de SLA ou de validation indépendante. » |
| « Est-ce que cela garantit notre conformité ? » | « Non. L’outil aide à configurer et gouverner des choix ; votre organisation et ses conseils déterminent les règles, les textes et les formalités. » |
| « Est-ce une preuve que l’assuré a vu et choisi ? » | « Pas à lui seul. Un événement SDK est une déclaration technique ; il ne vérifie ni l’identité, ni l’affichage, ni l’action réelle du visiteur. » |
| « Peut-on tester sur une route de recette ? » | « C’est une étape à cadrer. Il faut d’abord une autorisation écrite, une route et une origine dédiées, des comptes fictifs, un hébergement accepté, une revue sécurité/DPO et un retour arrière approuvé. » |
| « Les applications mobiles sont-elles incluses ? » | « Des SDK de démarrage existent pour iOS, Android et React Native, mais ils ne sont pas le périmètre de ce pilote Web et n’ont pas été intégrés ni approuvés dans une application de votre organisation. » |

## Après le rendez-vous

Compléter [FICHE_DECOUVERTE_CIH_BANK.md](./FICHE_DECOUVERTE_CIH_BANK.md) si le rendez-vous concerne CIH BANK, sinon reprendre ses rubriques dans une fiche propre au prospect. Écrire seulement les décisions réellement prises : problème confirmé ou non, sponsor, équipes à réunir, exigences, route éventuellement autorisée, propriétaire et date de la prochaine étape. Une démonstration positive ne vaut ni autorisation d’intégration, ni validation fournisseur, ni décision d’achat.

## Limites à ne pas omettre

- La page, la politique et les scripts de démonstration sont fictifs ; aucun service d’assurance ni fournisseur tiers n’est appelé.
- La console et l’API sont locales. La démo ne démontre pas l’exploitation, la disponibilité, les sauvegardes ou la résidence de données d’un service hébergé.
- Les choix Web restent locaux dans le scénario par défaut. Aucun événement visiteur n’est à inventer ou à activer pour rendre la présentation plus convaincante.
- Les parcours observés pendant une présentation ne sont pas une recette de sécurité, d’accessibilité ou d’acceptation client.
