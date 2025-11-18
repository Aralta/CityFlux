# Mobilité Urbaine

Un projet d'analyse et de traitement de données de mobilité urbaine utilisant Docker, Spark et Django.

## Vue d'ensemble

Ce dépôt contient plusieurs services orchestrés avec `docker-compose` :

- `db` : base de données PostgreSQL (image `postgres:16-alpine`).
- `spark-master` : master Apache Spark (3.5.3) pour lancer des jobs PySpark.
- `spark-worker` : workers Spark (déployés en réplicas) pour exécuter les tâches distribuées.
- `spark-history` : interface History Server de Spark (port 18080).
- `web` : application Django servant l'API / l'interface (port 8000).
- `preprocess` : conteneur pour scripts de prétraitement (ex. `preprocess.py`).

Les dossiers principaux :

- `django/` : code Django, Dockerfile, entrypoint, requirements.
- `spark/` : image Spark + scripts d'entrée + configuration.
- `preprocess/` : scripts et Dockerfile pour le prétraitement.
- `data/` : dossier local (monté dans les conteneurs) pour jeux de données.

## Contrat rapide

- Entrées : fichiers de données CSV/Parquet dans `./data/` ou source SQL (Postgres).
- Sorties : résultats temporaires dans `./data/`, tables dans Postgres.
- Erreurs possibles : variables d'environnement manquantes, Java non installé dans l'image Spark, dépendances Python manquantes.

## Prérequis

- Docker (>= 20.10) et Docker Compose
- Au minimum 8 Go de RAM pour exécuter Spark + DB localement (plus recommandé pour gros jeux de données)
- Fichier `.env` à la racine contenant les variables listées ci-dessous

## Variables d'environnement (.env)

Créez un fichier `.env` à la racine (même dossier que `docker-compose.yml`) avec au moins :

```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=changeme
POSTGRES_DB=mobilite
# autres variables optionnelles utilisées par les Dockerfiles
```

Assurez-vous que ces valeurs correspondent à vos besoins. Le `docker-compose.yml` référence ce fichier via `env_file: - .env`.

## Ports exposés (par défaut)

- PostgreSQL : 5432
- Django (web) : 8000
- Spark Master UI : 8080
- Spark Master (RPC) : 7077
- Spark History UI : 18080

## Volumes montés

- `./data` -> données utilisées par Spark / preprocess
- volume Docker `postgres_data` -> données PostgreSQL persistantes
- volume Docker `spark-logs` -> événements Spark pour HistoryServer

## Démarrage rapide

1. Construire et démarrer les services :

```bash
docker compose up --build
```

2. Attendre que `db` et `spark-master` soient en bonne santé (le compose utilise des healthchecks pour certains services). Ensuite :

- Django disponible sur `http://localhost:8000`
- Spark UI sur `http://localhost:8080`
- Spark History sur `http://localhost:18080`

## Commandes utiles (dans le conteneur `web` / `django`)

- Exécuter les migrations Django :

```bash
docker compose exec web python manage.py migrate
```

- Créer un superutilisateur :

```bash
docker compose exec web python manage.py createsuperuser
```

- Lancer la shell Django :

```bash
docker compose exec web python manage.py shell
```

## Prétraitement et jobs Spark

- Le service `preprocess` exécute `preprocess.py` par défaut (défini dans le `preprocess/Dockerfile`). Pour exécuter manuellement :

```bash
docker compose run --rm preprocess
```

- Pour soumettre un job Spark Python (depuis l'hôte, en utilisant le master exposé) :

```bash
# exemple : soumettre app.py qui se trouve dans ./apps
docker compose exec spark-master spark-submit --master spark://spark-master:7077 /opt/spark/apps/app.py
```

- Les jars nécessaires (ex : driver JDBC PostgreSQL) sont ajoutés à l'image Spark (vérifié dans `spark/Dockerfile`).

## Développement local

- Modifiez le code dans `django/app/` ou `preprocess/` et reconstruisez l'image si nécessaire :

```bash
docker compose up --build web
```

- Pour itérer rapidement sur les scripts PySpark, montez `./apps` (déjà monté dans `docker-compose.yml`) et utilisez `spark-submit` depuis le conteneur `spark-master`.

## Dépannage

- Si PostgreSQL ne démarre pas : vérifier `.env` et logs :

```bash
docker compose logs db
```

- Si Spark UI ne répond pas : vérifier `spark-master` logs, s'assurer que Java est présent dans l'image (les Dockerfiles installent `default-jdk-headless`) :

```bash
docker compose logs spark-master
```

- Erreurs Python liées aux dépendances : vérifiez `requirements.txt` dans chaque image (`django/`, `spark/`, `preprocess/`) et rebuild l'image.

## Tests & qualité

Aucun test automatisé n'est fourni par défaut. Pour ajouter des tests Django :

1. Ajouter des tests dans `django/app/tests/`
2. Exécuter :

```bash
docker compose exec web python manage.py test
```

## Fichiers importants

- `docker-compose.yml` : orchestration des services
- `spark/Dockerfile`, `django/Dockerfile`, `preprocess/Dockerfile` : définitions d'images
- `spark/requirements.txt`, `django/requirements.txt`, `preprocess/requirements.txt` : dépendances
- `spark/spark-defaults.conf` : configuration Spark
- `data/` : emplacement des jeux de données (monté dans les conteneurs)

## Bonnes pratiques

- Ne stockez pas de données sensibles dans le repo. Utilisez `.env` local et gitignore.
- Pour de gros volumes de données, testez les jobs Spark sur un petit échantillon local avant d'exécuter sur tout le dataset.
- Augmentez la mémoire CPU/RAM affectés au démon Docker si Spark manque de ressources.

## Contribution

Forkez le dépôt, ouvrez une branche feature/fix, puis une pull request. Documentez les changements et ajoutez des tests quand possible.

## Auteur

Répertoire fourni par l'équipe projet — README généré pour faciliter l'usage local et le déploiement via Docker Compose.

