# ALAMANE — préparation d’un pilote Web fermé

**État au 9 octobre 2026 : kit local de démonstration prêt à préparer ; aucun pilote client ni hébergement public n’est configuré.**

## Périmètre visé

- Une seule propriété Web, sur un domaine public contrôlé par le client et explicitement autorisé.
- Un environnement de recette isolé du site et des comptes de production.
- Une page publique non authentifiée ou une page de recette représentative, avec accès limité aux testeurs convenus.
- Une politique et des technologies fictives tant que les équipes du client n’ont pas approuvé le contenu et les traitements.
- Aucune donnée bancaire, donnée réelle de visiteur, identifiant de compte ou secret de production.
- Transmission centrale des décisions désactivée, sauf décision écrite ultérieure du client après revue.

Le domaine du client reste **à choisir et à autoriser par écrit**. La configuration locale ci-dessous utilise `http://localhost:8000`; elle ne publie rien sur Internet et ne constitue pas le pilote client.

## Préparer la démonstration Web locale

Depuis la racine du dépôt, lancer :

```sh
bash scripts/start-demo.sh --web-only
```

Le script utilise une base dédiée, `.local/alamane-web-pilot.sqlite3`, distincte de la démonstration multi-canal. Il crée un compte administrateur local si nécessaire, puis une organisation fictive « Banque Démo » et **une seule propriété `web`**. Les politiques sont des brouillons d’exemple en français et en arabe ; aucun événement visiteur n’est créé. Le script refuse les URL PostgreSQL pour éviter de toucher une base partagée.

La sortie affiche les adresses de la console, de la page fictive et de l’API. Les services n’écoutent que sur `127.0.0.1`; `Ctrl+C` les arrête. Il faut des ports locaux 8000 et 8001 libres.

Pour démontrer la publication avec l’approbation à deux personnes activée, créer un second compte local, l’inviter depuis la console, accepter l’invitation avec ce compte, puis publier le brouillon depuis ce second compte. Une propriété de développement ne remplace pas un déploiement isolé : cette règle de gouvernance ne constitue pas une séparation technique d’environnements.

## Parcours à dérouler avec des données fictives

1. Ouvrir la console et vérifier qu’elle ne contient que l’organisation fictive et sa propriété Web.
2. Relire le brouillon d’exemple. Ne pas présenter ses finalités, durées ou notices comme un conseil juridique ou une politique client.
3. Faire approuver et publier le brouillon par un second compte local, puis ouvrir l’URL `demo-site.html` affichée par le script.
4. Parcourir accepter, refuser, personnaliser et rouvrir le centre de préférences en français et en arabe standard.
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
