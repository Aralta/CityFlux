#!/usr/bin/env python3
"""
Spark Job Listener - Écoute Redis pour lancer les jobs Spark automatiquement.

Ce script s'exécute dans le conteneur Spark et écoute le channel Redis 'spark_jobs'.
Quand un message est reçu, il lance le job Spark correspondant via spark-submit.
"""

import redis
import json
import subprocess
import os
import sys
import time

# Forcer le flush des outputs pour Docker
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
SPARK_MASTER = os.getenv('SPARK_MASTER_URL', 'spark://spark-master:7077')
SPARK_APPS_PATH = '/opt/spark/apps'

# Mapping des scripts disponibles
AVAILABLE_SCRIPTS = {
    'map_data_process.py': os.path.join(SPARK_APPS_PATH, 'map_data_process.py'),
    'upper.py': os.path.join(SPARK_APPS_PATH, 'upper.py'),
    'data_converter.py': os.path.join(SPARK_APPS_PATH, 'data_converter.py'),
}


def run_spark_job(job_info):
    """
    Exécute un job Spark via spark-submit.
    
    Args:
        job_info: dict contenant job_id, script_name, input_file
    """
    job_id = job_info.get('job_id')
    script_name = job_info.get('script_name')
    input_file = job_info.get('input_file')
    
    print(f"🚀 Démarrage du job Spark: {job_id}")
    print(f"   Script: {script_name}")
    print(f"   Input: {input_file}")
    
    if script_name not in AVAILABLE_SCRIPTS:
        print(f"❌ Script inconnu: {script_name}")
        return False
    
    script_path = AVAILABLE_SCRIPTS[script_name]
    
    if not os.path.exists(script_path):
        print(f"❌ Script non trouvé: {script_path}")
        return False
    
    if not os.path.exists(input_file):
        print(f"❌ Fichier d'entrée non trouvé: {input_file}")
        return False
    
    # Construire la commande spark-submit
    cmd = [
        'spark-submit',
        '--master', SPARK_MASTER,
        '--deploy-mode', 'client',
        '--name', f'job_{job_id}',
        '--conf', 'spark.sql.shuffle.partitions=8',
        '--conf', 'spark.default.parallelism=8',
        script_path,
        '--input', input_file,
        '--job-id', job_id
    ]
    
    print(f"📋 Commande: {' '.join(cmd)}")
    
    try:
        # Exécuter le job Spark
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Job {job_id} terminé avec succès")
            # Afficher la sortie complète (ou tronquée si > 2000 chars)
            output = result.stdout
            if len(output) > 2000:
                # Afficher le début et la fin
                print(f"   Sortie (début):\n{output[:1000]}")
                print(f"   [...{len(output)-2000} caractères omis...]")
                print(f"   Sortie (fin):\n{output[-1000:]}")
            else:
                print(f"   Sortie:\n{output}")
            return True
        else:
            print(f"❌ Job {job_id} échoué (code: {result.returncode})")
            # Afficher plus d'erreurs pour le debug
            print(f"   Erreur stderr:\n{result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr}")
            if result.stdout:
                print(f"   Sortie stdout:\n{result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ Job {job_id} timeout après 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution du job {job_id}: {e}")
        return False


def update_job_status(redis_client, job_id, status, result=None):
    """Met à jour le statut du job dans Redis."""
    job_status = {
        'job_id': job_id,
        'status': status,
        'result': result,
        'timestamp': time.time()
    }
    redis_client.set(f'spark_job_status:{job_id}', json.dumps(job_status))
    redis_client.expire(f'spark_job_status:{job_id}', 3600)  # Expire après 1 heure


def main():
    """Boucle principale du listener."""
    print("🎧 Démarrage du Spark Job Listener...")
    print(f"   Redis: {REDIS_HOST}:{REDIS_PORT}")
    print(f"   Spark Master: {SPARK_MASTER}")
    
    # Attendre que Redis soit disponible
    max_retries = 30
    for i in range(max_retries):
        try:
            redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=0,
                decode_responses=True
            )
            redis_client.ping()
            print("✅ Connecté à Redis")
            break
        except redis.ConnectionError:
            print(f"⏳ Attente de Redis... ({i+1}/{max_retries})")
            time.sleep(2)
    else:
        print("❌ Impossible de se connecter à Redis")
        sys.exit(1)
    
    # S'abonner au channel spark_jobs
    pubsub = redis_client.pubsub()
    pubsub.subscribe('spark_jobs')
    
    print("📡 En écoute sur le channel 'spark_jobs'...")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                job_info = json.loads(message['data'])
                print(f"\n📥 Job reçu: {job_info}")
                
                job_id = job_info.get('job_id')
                
                # Mettre à jour le statut à "running"
                update_job_status(redis_client, job_id, 'running')
                
                # Exécuter le job
                success = run_spark_job(job_info)
                
                # Mettre à jour le statut final
                final_status = 'completed' if success else 'failed'
                update_job_status(redis_client, job_id, final_status)
                
            except json.JSONDecodeError as e:
                print(f"❌ Erreur de parsing JSON: {e}")
            except Exception as e:
                print(f"❌ Erreur lors du traitement du message: {e}")


if __name__ == '__main__':
    main()
