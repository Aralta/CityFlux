import os
import uuid
import json
from django.http import JsonResponse
from tasks import run_spark_job

# Chemin partagé avec Spark (doit correspondre au volume mount dans docker-compose)
SHARED_UPLOAD_PATH = "/app/data/uploads"

def trigger_conversion_job(request):
    """
    API Endpoint pour uploader un fichier et lancer le job de conversion Spark.
    POST params: data_file, data_type, action
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data_file = request.FILES.get('data_file')
        data_type = request.POST.get('data_type')
        action = request.POST.get('action')
        
        if not data_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
            
        # Créer le dossier s'il n'existe pas
        if not os.path.exists(SHARED_UPLOAD_PATH):
            os.makedirs(SHARED_UPLOAD_PATH, exist_ok=True)
            
        # Sauvegarder le fichier avec un ID unique
        unique_id = str(uuid.uuid4())
        safe_filename = data_file.name.replace(" ", "_")
        filename = f"{unique_id}_{safe_filename}"
        file_path = os.path.join(SHARED_UPLOAD_PATH, filename)
        
        with open(file_path, 'wb+') as destination:
            for chunk in data_file.chunks():
                destination.write(chunk)
                
        # Préparer les données pour le script Spark
        # Chemin relatif au montage dans le conteneur Spark
        # Django voit /app/data, Spark voit /opt/spark/data
        # Donc /app/data/uploads/x -> /opt/spark/data/uploads/x
        spark_file_path = f"/opt/spark/data/uploads/{filename}"
        
        job_payload = {
            "input_file": spark_file_path,
            "data_type": data_type,
            "action": action,
            "original_filename": data_file.name,
            "job_uuid": unique_id
        }
        
        # Sérialiser en JSON pour passer à la tâche Celery
        payload_json = json.dumps(job_payload)
        
        # Lancer la tâche Celery (qui va notifier Spark via Redis)
        # Le script Spark s'appelle 'data_converter.py'
        task_result = run_spark_job.delay(payload_json, "data_converter.py")
        
        return JsonResponse({
            'status': 'submitted',
            'job_id': task_result.id,
            'message': 'Job de conversion soumis à Spark',
            'file_saved': filename
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
