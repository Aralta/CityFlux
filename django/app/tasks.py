from celery import shared_task
import json
import os
import uuid
import redis


Spark_local_script = ["map_data_process.py", "upper.py", "data_converter.py"]
SHARED_DATA_PATH = "/app/data" if os.path.exists("/app/data") else "/opt/spark/data"


@shared_task(name="tasks.run_spark_script")
def run_spark_job(data_json, spark_script_name):
    """
    Lance un job Spark en écrivant les données dans un fichier partagé
    et en publiant une demande sur Redis pour que Spark le traite.
    """
    if spark_script_name not in Spark_local_script:
        raise ValueError(f"Script Spark inconnu: {spark_script_name}")
    
    try:
        job_id = str(uuid.uuid4())
        input_file_path = os.path.join(SHARED_DATA_PATH, f"spark_input_{job_id}.json")
        
        os.makedirs(SHARED_DATA_PATH, exist_ok=True)
        with open(input_file_path, 'w') as f:
            f.write(data_json)
        
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=0
        )
        
        job_info = {
            "job_id": job_id,
            "script_name": spark_script_name,
            "input_file": f"/opt/spark/data/spark_input_{job_id}.json",
            "status": "pending"
        }
        
        redis_client.publish('spark_jobs', json.dumps(job_info))
        
        return {"job_id": job_id, "status": "submitted", "input_file": input_file_path}
        
    except Exception as e:
        raise RuntimeError(f"Échec de la soumission du job Spark: {str(e)}")


@shared_task(name='tasks.health_check')
def health_check():
    """Tâche simple pour vérifier que Celery fonctionne."""
    return {'status': 'ok', 'message': 'Celery worker is running'}
