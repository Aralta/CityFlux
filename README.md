# Mobilité Urbaine

Un projet d'analyse et de traitement de données de mobilité urbaine utilisant Docker, Spark, Django, Redis et Celery.

## Vue d'ensemble

Ce dépôt contient plusieurs services orchestrés avec `docker-compose` :

- `db` : base de données PostgreSQL avec PostGIS pour données géospatiales.
- `spark-master` : master Apache Spark (3.5.3) pour lancer des jobs PySpark.
- `spark-worker` : workers Spark (2 réplicas) pour exécuter les tâches distribuées.
- `spark-history` : interface History Server de Spark (port 18080).
- `web` : application Django servant l'API / l'interface (port 8000).
- `celery-worker` : workers Celery pour tâches asynchrones.
- `redis` : broker Redis pour Celery et cache.

Les dossiers principaux :

- `django/` : code Django, Dockerfile, entrypoint, requirements.
- `spark/` : image Spark + scripts d'entrée + configuration.
- `db/` : configuration PostgreSQL avec PostGIS.
- `data/` : dossier local (monté dans les conteneurs) pour jeux de données.
- `apps/` : applications Spark Python.

## Arborescence du projet

```
mobilite-urbaine/
├── apps/                           # Scripts PySpark (montés dans Spark)
├── data/                           # Données (montées dans Spark)
├── db/                             # Configuration PostgreSQL + PostGIS
│   ├── Dockerfile
│   └── initdb.sql                  # Script d'initialisation de la base
├── django/                         # Application web Django
│   ├── app/
│   │   ├── __init__.py
│   │   ├── app.py                  # Point d'entrée Django
│   │   ├── celery_app.py           # Configuration Celery
│   │   ├── tasks.py                # Tâches Celery
│   │   ├── static/                 # Fichiers statiques
│   │   │   ├── css/
│   │   │   │   ├── carte.css
│   │   │   │   ├── common.css
│   │   │   │   ├── console.css
│   │   │   │   ├── enhanced_data.css
│   │   │   │   ├── multi_console.css
│   │   │   │   └── style.css
│   │   │   └── js/                 # Script JS des templates 
│   │   │       ├── carte-config.js     
│   │   │       ├── carte-utils.js      
│   │   │       ├── carte-controller.js 
│   │   │       ├── enhanced_data.js
│   │   │       └── multi_console.js
│   │   ├── templates/              # Templates HTML
│   │   │   ├── carte.html
│   │   │   ├── db_console.html
│   │   │   ├── enhanced_data.html
│   │   │   ├── index.html
│   │   │   ├── multi_console.html
│   │   │   └── spark_upper.html
│   │   └── views/                  # Vues Python
│   │       ├── __init__.py
│   │       ├── carte.py            
│   │       ├── database.py         
│   │       ├── docker_console.py
│   │       ├── get_enhanced_data.py 
│   │       └── handler.py
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── settings.py
├── spark/                          # Configuration Apache Spark
│   ├── app/                        # Applications Spark Python
│   │   ├── map_data_process.py     
│   │   ├── spark_job_listener.py
│   │   └── upper.py
│   ├── Dockerfile
│   ├── entrypoint.sh
│   ├── requirements.txt
│   └── spark-defaults.conf
├── template/                       # Templates de projet
├── .env                            # Variables d'environnement (non versionné)
├── docker-compose.yml              # Orchestration des services Docker
└── README.md                       # Documentation du projet
```

> **Note** : Le dossier `venv/` (environnement virtuel Python) n'est pas listé car il ne doit pas être versionné. Ajoutez-le à `.gitignore`.

## Prérequis

- Docker (>= 20.10) et Docker Compose
- Au minimum 8 Go de RAM pour exécuter Spark + DB localement (plus recommandé pour gros jeux de données)
- Fichier `.env` à la racine contenant les variables listées ci-dessous

## Variables d'environnement (.env)

Créez un fichier `.env` à la racine (même dossier que `docker-compose.yml`) avec :

```env
# Spark
SPARK_MASTER=spark://spark-master:7077
SPARK_NO_DAEMONIZE=true

# PostgreSQL
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=mobility

# Django (utilise les mêmes vars que Postgres)
SQL_HOST=db
SQL_PORT=5432
SQL_USER=user
SQL_PASSWORD=password
SQL_DB=mobility
DJANGO_SECRET_KEY=change_me_to_a_secure_key_in_production
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

⚠️ **Important** : Changez `DJANGO_SECRET_KEY` et les mots de passe en production !

## Ports exposés (par défaut)

- PostgreSQL : 5432
- Django (web) : 8000
- Redis : 6379
- Spark Master UI : 8080
- Spark Master (RPC) : 7077
- Spark History UI : 18080

## Volumes montés

- `./data` -> `/opt/spark/data` (données utilisées par Spark)
- `./apps` -> `/opt/spark/apps` (applications Spark Python)
- volume Docker `postgres_data` -> données PostgreSQL persistantes
- volume Docker `spark-logs` -> événements Spark pour HistoryServer

## Démarrage rapide

1. Construire et démarrer les services :

```bash
docker compose up --build
```

2. Les services démarrent dans l'ordre grâce aux healthchecks :
   - `db` démarre en premier
   - `redis` démarre ensuite
   - `spark-master` démarre et attend d'être sain
   - `spark-worker`, `web` et `celery-worker` démarrent après

3. Accès aux interfaces :
   - Django : `http://localhost:8000`
   - Spark Master UI : `http://localhost:8080`
   - Spark History : `http://localhost:18080`


## Celery - Tâches asynchrones

- Vérifier le statut des workers Celery :

```bash
docker compose exec celery-worker celery -A app inspect active
```

- Voir les logs du worker :

```bash
docker compose logs -f celery-worker
```

- Redémarrer le worker après modification du code :

```bash
docker compose restart celery-worker
```

## Jobs Spark

- Pour soumettre un job Spark Python (depuis le master) :

```bash
docker compose exec spark-master spark-submit \
  --master spark://spark-master:7077 \
  /opt/spark/apps/votre_script.py
```

- Les workers Spark sont configurés avec 2 cœurs et 2 Go de RAM chacun. Ajustez dans `docker-compose.yml` si nécessaire.

## Développement local

- Pour reconstruire uniquement un service :

```bash
docker compose up --build web
```

- Pour voir les logs d'un service spécifique :

```bash
docker compose logs -f web
docker compose logs -f spark-master
```

- Pour exécuter une commande dans un conteneur :

```bash
docker compose exec web bash
docker compose exec spark-master bash
```

## Healthchecks

Le compose inclut des healthchecks pour garantir un démarrage ordonné :

- `db` : vérifie `pg_isready` (20s start period)
- `redis` : vérifie `redis-cli ping`
- `spark-master` : vérifie l'API Web (30s start period)
- `web` : vérifie l'endpoint Django (30s start period)

## Dépannage

### PostgreSQL ne démarre pas

```bash
docker compose logs db
# Vérifiez .env et les permissions sur postgres_data
```

### Spark UI ne répond pas

```bash
docker compose logs spark-master
# Vérifiez que Java est installé dans l'image
docker compose exec spark-master java -version
```

### Erreurs Celery / Redis

```bash
docker compose logs redis
docker compose logs celery-worker
# Vérifiez CELERY_BROKER_URL dans .env
```

### Erreurs de dépendances Python

Vérifiez les `requirements.txt` et rebuild :

```bash
docker compose build --no-cache web
docker compose build --no-cache celery-worker
```

### Problèmes de mémoire Spark

Augmentez les ressources dans `docker-compose.yml` :

```yaml
spark-worker:
  environment:
    - SPARK_WORKER_CORES=4
    - SPARK_WORKER_MEMORY=4g
```

## Tests

Pour ajouter et exécuter des tests Django :

```bash
# Créer des tests dans django/app/tests/
docker compose exec web python manage.py test

# Avec coverage
docker compose exec web coverage run --source='.' manage.py test
docker compose exec web coverage report
```

## Architecture réseau

Tous les services communiquent via le réseau `mobility-network` (bridge). Les services se résolvent par leur nom de conteneur :

- Django → PostgreSQL : `db:5432`
- Django → Redis : `redis:6379`
- Spark Workers → Master : `spark-master:7077`

### Déploiement sur plusieurs machines (machines séparées)

`docker compose` (en mode “classique”) est pensé pour **une seule machine**. Pour répartir les services sur plusieurs hôtes, vous avez 2 approches :

#### Option A — Simple (sans orchestrateur, IP/DNS fixes)
Objectif : exécuter des sous-ensembles de services sur des machines différentes, en remplaçant les noms Compose (`db`, `redis`, `spark-master`) par des **IP/DNS atteignables**.

1) **Choisir un découpage** (exemple)
- Machine A (Data) : `db`, `redis`
- Machine B (Spark) : `spark-master`, `spark-worker`, `spark-history`
- Machine C (App) : `web`, `celery-worker`

2) **Ouvrir les ports réseau (firewall)**
- PostgreSQL : `5432` (Machine A)
- Redis : `6379` (Machine A)
- Spark Master RPC : `7077` (Machine B)
- Spark Master UI : `8080` (Machine B, optionnel)
- Spark History : `18080` (Machine B, optionnel)
- Django : `8000` (Machine C)

3) **Adapter les variables d’environnement `.env` sur chaque machine**
Sur **Machine C (App)**, pointez vers les hôtes réels :
```env
SQL_HOST=<IP_OU_DNS_MACHINE_A>
SQL_PORT=5432
CELERY_BROKER_URL=redis://<IP_OU_DNS_MACHINE_A>:6379/0
CELERY_RESULT_BACKEND=redis://<IP_OU_DNS_MACHINE_A>:6379/0
DJANGO_ALLOWED_HOSTS=<dns_machine_c>,<ip_machine_c>,localhost,127.0.0.1
```

Sur **Machine B (Spark)**, pointez les workers vers le master :
```env
SPARK_MASTER=spark://<IP_OU_DNS_MACHINE_B>:7077
```
et côté `spark-worker`, l’URL master doit viser cette même adresse (`spark://...:7077`).

4) **Démarrer dans le bon ordre**
- Machine A : démarrer `db` puis `redis`
- Machine B : démarrer `spark-master` puis `spark-worker` (+ `spark-history` si besoin)
- Machine C : démarrer `web` puis `celery-worker`

5) **Points d’attention**
- Les volumes (`postgres_data`, `spark-logs`) deviennent **locaux à chaque machine** : c’est normal, mais ce n’est pas un “stockage partagé”.
- Sécurité : n’exposez pas `5432/6379` sur Internet. Préférez un réseau privé/VPN et/ou restreignez par firewall.

#### Option B — Recommandée (orchestrateur : Docker Swarm / Kubernetes)
Objectif : avoir un **réseau overlay** et un placement multi-nœuds sans gérer manuellement les IPs.

- **Docker Swarm (rapide à mettre en place)** :
  1. Initialiser le swarm sur une machine manager : `docker swarm init`
  2. Faire joindre les autres machines : `docker swarm join ...`
  3. Créer un réseau overlay : `docker network create -d overlay mobility-network`
  4. Déployer avec une stack (le champ `deploy:` sera pris en compte en swarm) : `docker stack deploy -c docker-compose.yml mobility`

- **Kubernetes (plus complet)** :
  - Déployer PostgreSQL/Redis/Spark/Django via Helm/manifests, avec Services internes + Ingress pour exposer Django/Spark UI.
  - Utiliser des PersistentVolumes pour `postgres_data` et éventuellement pour les logs Spark.


## Bonnes pratiques

- Ne committez jamais `.env` - utilisez `.env.example` comme template
- Pour la production, désactivez `DJANGO_DEBUG` et utilisez un secret key fort
- Testez les jobs Spark sur des échantillons avant le dataset complet
- Surveillez les logs avec `docker compose logs -f`
- Utilisez des volumes nommés pour les données persistantes
- Régulièrement : `docker compose down -v` puis rebuild pour nettoyer

## Architecture du code

Le code a été refactorisé pour suivre les bonnes pratiques :

### Frontend JavaScript (`django/app/static/js/`)

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `carte-config.js` | ~270 | Configurations : `POI_ICONS`, `ZONE_COLORS`, `TILE_CONFIGS` |
| `carte-utils.js` | ~130 | Utilitaires : `getPOIIcon()`, `getZoneColor()`, `createEmojiIcon()` |
| `carte-controller.js` | ~540 | Classe `MapController` et initialisation |

### Backend Python (`django/app/views/`)

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `carte.py` | ~265 | API carte avec `LAYERS_CONFIG` centralisé |
| `database.py` | ~280 | Gestionnaire PostGIS DRY avec méthodes utilitaires |
| `get_enhanced_data.py` | ~180 | API Overpass avec `OSM_DATA_CONFIG` centralisé |

### Spark (`spark/app/`)

| Fichier | Lignes | Description |
|---------|--------|-------------|
| `map_data_process.py` | ~310 | Traitement données avec mappings centralisés |

## Fichiers importants

- `docker-compose.yml` : orchestration des services
- `.env` : variables d'environnement (non versionné)
- `spark/Dockerfile`, `django/Dockerfile`, `db/Dockerfile` : images personnalisées
- `spark/requirements.txt`, `django/requirements.txt` : dépendances Python
- `spark/entrypoint.sh` : script de démarrage Spark (master/worker/history)
- `django/entrypoint.sh` : script de démarrage Django
- `data/` : datasets (monté en volume)
- `apps/` : applications Spark

## Auteur

Projet Polytech TAI - Mobilité Urbaine

