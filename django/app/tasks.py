from celery import shared_task
import json
import os
import uuid
import redis


# Celery recupere les donnes des different channels Redis et lance les jobs Spark via ces taches Celery
# Celery comprend quel tache lancer en fonction du nom de la tache defini ci-dessous car ce nom est utilise dans le publish Redis dans Django
Spark_local_script = ["map_data_process.py", "upper.py"]  # Noms des scripts Spark disponibles

# Chemin du volume partagé entre Django/Celery et Spark
SHARED_DATA_PATH = "/app/data" if os.path.exists("/app/data") else "/opt/spark/data"


@shared_task(name="tasks.run_spark_script")
def run_spark_job(data_json, spark_script_name):
    """
    Lance un job Spark en écrivant les données dans un fichier partagé
    et en publiant une demande sur Redis pour que Spark le traite.
    
    Note: Cette approche utilise un volume partagé car le conteneur Celery
    n'a pas accès à Docker pour exécuter `docker exec`.
    """
    if spark_script_name not in Spark_local_script:
        raise ValueError(f"Script Spark inconnu: {spark_script_name}")
    
    try:
        # Générer un identifiant unique pour ce job
        job_id = str(uuid.uuid4())
        
        # Chemin du fichier d'entrée dans le volume partagé
        # Le volume ./data est monté dans /opt/spark/data (Spark) et peut être accessible via /app/data
        input_file_path = os.path.join(SHARED_DATA_PATH, f"spark_input_{job_id}.json")
        
        # Sauvegarder les données JSON dans le fichier partagé
        os.makedirs(SHARED_DATA_PATH, exist_ok=True)
        with open(input_file_path, 'w') as f:
            f.write(data_json)
        
        print(f"📁 Données sauvegardées dans: {input_file_path}")
        
        # Publier un message Redis pour notifier qu'un job Spark est prêt
        # Le script Spark peut écouter ce channel ou être lancé manuellement
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0
        )
        
        job_info = {
            "job_id": job_id,
            "script_name": spark_script_name,
            "input_file": f"/opt/spark/data/spark_input_{job_id}.json",  # Chemin côté Spark
            "status": "pending"
        }
        
        redis_client.publish('spark_jobs', json.dumps(job_info))
        print(f"📤 Job Spark publié sur Redis: {job_info}")
        
        # Note: Pour exécuter le job Spark, vous pouvez:
        # 1. Avoir un listener dans le conteneur Spark qui écoute le channel 'spark_jobs'
        # 2. Ou exécuter manuellement depuis le host:
        #    docker exec spark-master spark-submit --master spark://spark-master:7077 \
        #        /opt/spark/apps/map_data_process.py --input /opt/spark/data/spark_input_<job_id>.json
        
        print("✅ Job Spark soumis avec succès.")
        return {"job_id": job_id, "status": "submitted", "input_file": input_file_path}
        
    except Exception as e:
        raise RuntimeError(f"Échec de la soumission du job Spark: {str(e)}")


@shared_task(name='tasks.health_check')
def health_check():
    """Tâche simple pour vérifier que Celery fonctionne."""
    return {'status': 'ok', 'message': 'Celery worker is running'}
