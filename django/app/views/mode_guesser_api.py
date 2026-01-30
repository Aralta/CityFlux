"""
API endpoints for the Transport Mode Guesser feature.
"""
import os
import json
import uuid
import redis
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from tasks import run_spark_job


SHARED_DATA_PATH = "/app/data" if os.path.exists("/app/data") else "/opt/spark/data"
RESULTS_PATH = os.path.join(SHARED_DATA_PATH, "results")


def get_redis_client():
    """Get a Redis client instance."""
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0
    )


@csrf_exempt
@require_http_methods(["POST"])
def trigger_mode_guesser(request):
    """
    API Endpoint to trigger the transport mode guesser Spark job.
    POST body: { "trajectory_ids": ["traj1", "traj2", ...] }
    """
    try:
        data = json.loads(request.body)
        trajectory_ids = data.get('trajectory_ids', [])

        if not trajectory_ids:
            return JsonResponse({'error': 'No trajectory IDs provided'}, status=400)

        # Generate unique job ID
        job_uuid = str(uuid.uuid4())

        # Prepare job payload
        job_payload = {
            "trajectory_ids": trajectory_ids,
            "job_uuid": job_uuid
        }

        payload_json = json.dumps(job_payload)

        # Submit Celery task
        task_result = run_spark_job.delay(payload_json, "mode_guesser.py")

        return JsonResponse({
            'status': 'submitted',
            'job_id': job_uuid,
            'celery_task_id': task_result.id,
            'message': 'Mode guesser job submitted to Spark'
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_mode_guesser_status(request, job_id):
    """
    API Endpoint to get the status of a mode guesser job.
    Returns results if completed.
    """
    try:
        # First, check Redis for results
        redis_client = get_redis_client()
        redis_key = f"mode_guesser:{job_id}"
        cached_result = redis_client.get(redis_key)

        if cached_result:
            result = json.loads(cached_result)
            return JsonResponse(result)

        # If not in Redis, check for result file
        result_file = os.path.join(RESULTS_PATH, f"mode_guesser_{job_id}.json")
        
        if os.path.exists(result_file):
            with open(result_file, 'r') as f:
                result = json.load(f)
            return JsonResponse(result)

        # Job still pending
        return JsonResponse({
            'status': 'pending',
            'job_id': job_id,
            'message': 'Job is still processing'
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
