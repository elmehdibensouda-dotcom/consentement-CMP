# Préparer l’hébergement d’ALAMANE au Maroc

**État de la recherche : 8 octobre 2026**  
**Décision : aucun fournisseur n’est sélectionné et aucune donnée réelle ne doit être hébergée.**

## Ce que confirment les sources publiques

| Option | État vérifié | Conséquence pour ALAMANE |
| --- | --- | --- |
| **Oracle Cloud Infrastructure (OCI), Casablanca** | La région `af-casablanca-1` est disponible depuis le 20 février 2026. La fiche OCI indique un seul domaine de disponibilité. Oracle annonce une seconde région à Settat, mais la présente comme prévue. | C’est le premier candidat à une évaluation technique de préproduction si un acheteur exige une région cloud publique au Maroc. Un seul domaine de disponibilité ne prouve pas une architecture HA ou une reprise après sinistre adaptée à une banque ; mesurer les services réellement disponibles, les options de sauvegarde/restauration, les engagements et le plan de continuité. Ne pas dépendre de Settat avant sa disponibilité vérifiée. |
| **AWS Wavelength, Casablanca avec Orange** | La zone Wavelength de Casablanca est annoncée en disponibilité générale depuis janvier 2025. AWS décrit du calcul et du stockage proposés en partenariat avec Orange, avec des capacités de résidence des données et une expérience opérationnelle similaire à une région AWS. | À évaluer seulement si les services nécessaires au produit et le modèle d’exploitation conviennent. Une zone Wavelength n’est pas une région AWS publique complète : faire préciser où résident les plans de contrôle, journaux, sauvegardes, support et données de gestion, ainsi que la topologie et les responsabilités Orange/AWS. |
| **Azure et Google Cloud** | Les listes officielles consultées des régions Azure et Google Cloud ne répertorient pas de région publique au Maroc. Microsoft répertorie notamment Johannesburg et Le Cap en Afrique ; Google répertorie Johannesburg. | Ces clouds peuvent rester pertinents si l’acheteur accepte une autre région et a évalué les transferts et la résidence. Leur présence commerciale, réseau ou edge au Maroc ne doit pas être présentée comme un hébergement des données dans le pays. |

Sources officielles : [fiche de lancement OCI Casablanca](https://docs.oracle.com/en-us/iaas/releasenotes/oci/new-region-casablanca-1.htm), [annonce Oracle de la région Casablanca et du projet Settat](https://www.oracle.com/africa-fr/news/announcement/oracle-first-hyperscaler-open-public-cloud-2026-04-07/), [annonce AWS Wavelength Casablanca](https://aws.amazon.com/about-aws/whats-new/2025/01/aws-wavelength-zone-casablanca/), [infrastructure AWS](https://aws.amazon.com/about-aws/global-infrastructure/), [régions Azure](https://learn.microsoft.com/en-us/azure/reliability/regions-list), [régions Google Cloud](https://cloud.google.com/about/locations/).

## Recommandation de travail

Préqualifier **OCI Casablanca** pour une démonstration technique de préproduction, sans engagement commercial et sans données client. L’existence d’une région locale répond à une question concrète de résidence au niveau de l’infrastructure, mais ne valide ni l’aptitude bancaire ni la conformité juridique du service. Le fait qu’elle ait actuellement un seul domaine de disponibilité en fait aussi un point à traiter explicitement pour la disponibilité et la reprise.

Garder **AWS Wavelength Casablanca** comme option comparative à demander à Orange/AWS si l’acheteur l’utilise déjà ou si son architecture convient mieux. Ne pas comparer les fournisseurs sur le seul intitulé « cloud local » : demander une cartographie écrite de l’emplacement des données par catégorie et service.

## Conditions avant une préproduction partagée

1. Obtenir les exigences écrites du premier acheteur : résidence primaire, sauvegardes et reprise, SSO, réseau privé, chiffrement et clés, journalisation, support, SLA, audits, sous-traitants, notification d’incident et suppression.
2. Faire confirmer par le client et son conseil les formalités CNDP pertinentes, les autorisations de transfert éventuelles et les responsabilités des parties. L’hébergement au Maroc ne vaut pas validation juridique.
3. Vérifier contractuellement le lieu des données de production, sauvegardes, journaux, métadonnées, accès d’exploitation et support. Documenter toute exception et tout transfert.
4. Évaluer sur le fournisseur retenu les services disponibles dans la région, les limites de capacité, la redondance réelle, les sauvegardes, la restauration et une procédure de sortie. Pour OCI Casablanca, traiter explicitement le domaine de disponibilité unique actuellement publié.
5. Construire puis exécuter un déploiement de préproduction isolé : PostgreSQL, secrets gérés, TLS, accès administrateur, sauvegarde/restauration, supervision, alertes, collecte des journaux et réponse aux incidents. Le dépôt ne contient actuellement que la recette de conteneur ; cette validation n’a pas eu lieu.
6. N’ouvrir un pilote qu’après revue de sécurité et d’architecture du client, accord écrit sur le périmètre de données synthétiques, critères de succès, responsabilités et retour arrière.

## Limites de cette recherche

Cette comparaison est une présélection documentaire, pas une analyse contractuelle, juridique, tarifaire ou de capacité. Les catalogues, prix, services et conditions évoluent ; demander au fournisseur une confirmation écrite au moment de l’évaluation. Aucun fournisseur n’est choisi pour ALAMANE et aucun hébergement n’est provisionné.
