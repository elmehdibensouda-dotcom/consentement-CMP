# ALAMANE — préparation d’un pilote Web fermé

**État au 9 octobre 2026 : kit local de démonstration en adaptation pour un premier assureur ; aucun pilote client ni hébergement public n’est configuré.**

## Cadrage du premier prospect — assurance

La cible de la présentation est un assureur. Le parcours à montrer est l’intégration du SDK Web dans une page d’essai de l’espace assuré, idéalement dans une recette protégée avec comptes fictifs. Une page authentifiée ne doit pas transmettre à ALAMANE de session, identifiant assuré, contrat, sinistre, donnée de santé ou autre donnée réelle. Le SDK de démonstration ne lit pas ces champs. L’équipe du prospect doit autoriser par écrit la route, l’origine, les testeurs et la fenêtre de test avant toute intégration sur son domaine.

Si l’accès à une recette client n’est pas accordé à temps, la démonstration se fait dans la maquette locale [demo-assurance.html](./demo-assurance.html) avec des finalités fictives. Cette solution montre le parcours visuel et les choix locaux ; elle ne prouve pas une intégration dans le portail de l’assureur. L’API locale n’est pas accessible au prospect et ne doit recevoir aucune donnée réelle.

## Périmètre visé

- Une seule propriété Web, sur une origine de recette contrôlée par le client et explicitement autorisée.
- Un environnement de recette isolé du site et des comptes de production.
- Pour le premier assureur, une route de l’espace assuré derrière l’authentification de test du client, limitée aux testeurs convenus ; une page publique fictive n’est qu’un repli de démonstration.
- Une politique et des technologies fictives tant que les équipes du client n’ont pas approuvé le contenu et les traitements.
- Aucun compte assuré réel, contrat, sinistre, donnée de santé, donnée réelle de visiteur, identifiant de session ou secret de production.
- Transmission centrale des décisions désactivée, sauf décision écrite ultérieure du client après revue.

Le domaine du client reste **à choisir et à autoriser par écrit**. La configuration locale ci-dessous utilise `http://localhost:8000`; elle ne publie rien sur Internet et ne constitue pas le pilote client.

## Préparer la démonstration Web locale

Depuis la racine du dépôt, lancer :

```sh
bash scripts/start-demo.sh --web-only
```

Le script utilise `.local/alamane-web-pilot.sqlite3`, distincte de la démonstration multi-canal. Il crée un compte administrateur local si nécessaire, puis ajoute l’organisation fictive « Assurance Démo » avec **une propriété `web`** et un brouillon bilingue français/arabe. Les autres enregistrements éventuels de cette base ne sont pas supprimés. Aucun événement visiteur n’est créé. Le script refuse les URL PostgreSQL pour éviter de toucher une base partagée.

La sortie affiche les adresses de la console, de la page fictive et de l’API. Pour ce mode, console, API et page de démonstration passent par la même origine `http://localhost:8000/console/`; l’API écoute sur `127.0.0.1` et le port 8001 n’est pas nécessaire. Cela évite le blocage navigateur rencontré avec une API sur un port séparé. `Ctrl+C` arrête le service local. Le port 8000 doit être libre.

Pour démontrer la publication avec l’approbation à deux personnes activée, créer un second compte local, l’inviter depuis la console, accepter l’invitation avec ce compte, puis publier le brouillon depuis ce second compte. Une propriété de développement ne remplace pas un déploiement isolé : cette règle de gouvernance ne constitue pas une séparation technique d’environnements.

## Parcours à dérouler avec des données fictives

1. Ouvrir la console, sélectionner « Assurance Démo » et vérifier sa propriété Web de développement.
2. Relire le brouillon d’exemple. Ne pas présenter ses finalités, durées ou notices comme un conseil juridique ou une politique client.
3. Faire approuver et publier le brouillon par un second compte local, puis ouvrir l’URL `demo-assurance.html` affichée par le script.
4. Parcourir accepter, refuser, personnaliser, rouvrir et réinitialiser le centre. Le lien « العربية / Français » change la langue du module ; utiliser `?lang=ar` pour le départ arabe. Le bouton de réinitialisation ne s’affiche que sur localhost et efface le choix de la propriété de démonstration courante.
5. Dans les outils développeur du navigateur, observer les scripts locaux fictifs avant le choix, après chaque choix et après une révocation. Aucun fournisseur tiers réel n’est configuré dans cette démonstration.
6. Confirmer que la console ne montre aucun événement visiteur injecté. Les métriques et événements ne doivent jamais être inventés pour rendre la démo plus convaincante.

Ces étapes constituent un scénario de démonstration. Elles ne sont pas une validation d’acceptation exécutée et ne prouvent ni la conformité juridique, ni l’intégration chez un client, ni l’arrêt réel de tous les fournisseurs.

## Conditions avant tout pilote sur un domaine client

Ne pas brancher le SDK sur un domaine tiers ni déployer l’API pour un acheteur avant d’avoir réuni les éléments suivants :

- Autorisation écrite du propriétaire du domaine, liste des pages, technologies et testeurs inclus, fenêtre d’intervention et procédure de retour arrière.
- Décision du client sur le domaine public ou sous-domaine de recette, l’accès fermé (par exemple VPN ou passerelle d’accès), le routage d’une petite cohorte de testeurs et le propriétaire du DNS/TLS.
- Approbation des équipes Web, sécurité, DPO/juridique et achats ; textes de politique et classement des finalités validés par le responsable de traitement et son conseil.
- Environnement d’hébergement distinct, URL HTTPS, origine exacte autorisée, base de données et comptes dédiés, secrets gérés hors du dépôt, sauvegarde/restauration démontrée, supervision et procédure d’incident convenues.
- Décision écrite sur la collecte. Par défaut, garder `collectDecisionEvents` à `false` et ne pas appeler `recordDecision` depuis l’application hôte.
- Scénarios, preuves, critères de réussite, responsables, durée, coûts et critères d’arrêt convenus avant le début.

Le dépôt actuel fournit un démonstrateur local SQLite ; le mode production est refusé. Il n’existe pas encore de service hébergé durci pour un client. L’adaptateur PostgreSQL et les documents de préproduction ne prouvent pas qu’un déploiement, une sauvegarde ou une reprise ont été validés sur une infrastructure réelle. **Aucune donnée réelle de visiteur ne doit être envoyée à l’API locale ou à une infrastructure non approuvée.**

## Décision de sortie

Le pilote ne peut passer à une suite commerciale que si le client confirme par écrit :

- que les parcours accepter/refuser/personnaliser et la révocation produisent le comportement attendu sur les technologies réellement incluses ;
- que la portée du domaine, la cohorte de test et l’environnement sont restés dans le périmètre autorisé ;
- les écarts de sécurité, d’exploitation, de langue, d’accessibilité et d’intégration observés, avec un responsable et une décision pour chacun ;
- la décision de poursuivre, corriger ou arrêter, ainsi que les prérequis d’achat et de production.

La fiche de cadrage client est disponible dans [FICHE_CADRAGE_PILOTE.html](./FICHE_CADRAGE_PILOTE.html). Les limites de sécurité du prototype sont détaillées dans [DOSSIER_SECURITE_FOURNISSEUR.md](./DOSSIER_SECURITE_FOURNISSEUR.md) ; ces documents ne sont ni des attestations ni une promesse de disponibilité en production.
