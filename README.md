# [PROJET EN COURS]

# The Magical CSV Merge Machine

## Problématique

Dans le contexte d'études statistiques, il est souvent nécessaire de recouper des données issues de sources diverses. Cependant, trop souvent, deux tables de données ne possèdent pas de clé en commun et les données qui permettraient une jointure ne sont pas exprimées de façon identique (fautes d'ortographe, abbréviations, etc.), ce qui rend difficile l'exploitation des données. Le nettoyage manuel est très chronophage voire impossible dans certains cas...

**Concrètement**: Comment apparier automatiquement ?

|Nom officiel | Adresse  | Ville |   | avec |  | NOM | RUE | VILLE |
|---|---|---|---|---|---|---|---|---|
| Société Française de Ramonage | 2 rue du Beffroy | Orsay |  | ... |  | s.f. rammonage| rue du beffroy, 2 | orsay |

## Objectif

L'objectif de ce projet est de créer une **API** ainsi qu'une **interface web** permettant d'apparier automatiquement des données csv sales à un réferentiel propre. Le service devra aussi pouvoir être installé et **tourner localement** (pour les utilisateurs ayant des données confidentielles). Nous projettons de proposer plusieurs sous-services:

- Détection (et remplacement) de valeurs représentant des valeurs manquantes (remplacer "no value" par "")
- Identification du type sémantique des colonnes (adresse, nom de personne, nom d'entreprise, téléphone, etc.)
- Nettoyage et standardisation approprié au type détecté
- (Suggestion de correspondances entre les colonnes de la source sale et du référentiel)
- Appariement de la source sale et du référentiel

Vous pouvez trouver [la définition officielle de l'objectif du projet](http://www.gouvernement.fr/entrepreneur-interet-general) (onglet Ministère de la recherche). 

## Qu'est ce qu'on a pour l'instant?

Le projet est encore en développement... Vous pouvez [faire des remarques (laisser des issues) ici](https://github.com/eig-2017/the-magical-csv-merge-machine/issues).

# Contexte
Ce projet est développé de Janvier à Novembre 2017 dans le cadre du [programme d'entrepreneur d'intérêt général](https://www.etalab.gouv.fr/decouvrez-la-1e-promotion-des-entrepreneurs-dinteret-general) au sein du département outils d'aide à la décision du Ministere de l'éducation nationale, de l'enseignement supérieur et de la recherche.

-------------------------------------------
# Faire tourner localement

```
$ python3 api.py
# Puis dans un autre terminal
$ python3 worker.py
```

- Après une minute, l'application devrait être disponible via: http://0.0.0.0:5000

-------------------------------------------

# Faire tourner l'application localement avec Docker [NON OPTIMISE, TRAVAIL EN COURS]
Pour faire tourner l'application 

- Installer docker: [lien](https://www.docker.com/community-edition)
- Construire l'image puis lancer le container
```
$ docker build -t merge_machine .
$ docker run -p 5000:5000 merge_machine
```
- Si vous êtes derrière un proxy et que vous rencontrez une erreur, [ce lien](https://robinwinslow.uk/2016/06/23/fix-docker-networking-dns/) peut aider
- Après une minute, l'application devrait être disponible via: `http://127.0.0.1:5000/`
- Pour voir le container docker (et son identifiant): `docker ps`
- Pour rejoindre un container précédent: `docker attach <identifiant_container>`




