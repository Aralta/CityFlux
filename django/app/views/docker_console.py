"""
Vue pour la multi-console Docker
"""
import subprocess
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


# Mapping des services vers les containers Docker
SERVICE_CONTAINERS = {
    'db': 'postgres_postgis',
    'spark-master': 'spark-master',
    'spark-worker': None,  # Handled specially (multiple workers)
    'spark-history': 'spark-history',
    'spark-job-listener': 'spark-job-listener',
    'web': 'django-server',
    'celery-worker': 'celery-worker',
    'redis': 'redis-server'
}


def multi_console_view(request):
    """Render the multi-console page"""
    return render(request, 'multi_console.html')


@require_GET
def get_docker_logs(request, service_id):
    """
    API endpoint to get Docker logs for a specific service
    
    Args:
        service_id: The service identifier (e.g., 'db', 'spark-master')
    
    Query params:
        tail: Number of lines to retrieve (default: 100)
        since: Get logs since timestamp (optional)
    """
    tail = request.GET.get('tail', '100')
    since = request.GET.get('since', '')
    
    if service_id not in SERVICE_CONTAINERS:
        return JsonResponse({
            'status': 'error',
            'error': f'Service inconnu: {service_id}'
        }, status=404)
    
    container_name = SERVICE_CONTAINERS[service_id]
    
    # Handle spark-worker specially (multiple containers)
    if service_id == 'spark-worker':
        return get_spark_worker_logs(tail, since)
    
    try:
        # Check container status first
        status_result = subprocess.run(
            ['docker', 'inspect', '-f', '{{.State.Status}}', container_name],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        container_status = status_result.stdout.strip() if status_result.returncode == 0 else 'not_found'
        
        # Get logs
        cmd = ['docker', 'logs', '--tail', tail]
        if since:
            cmd.extend(['--since', since])
        cmd.append(container_name)
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Docker logs go to stderr for some containers
        logs = result.stdout if result.stdout else result.stderr
        
        return JsonResponse({
            'status': 'success',
            'service': service_id,
            'container': container_name,
            'container_status': container_status,
            'logs': logs
        })
        
    except subprocess.TimeoutExpired:
        return JsonResponse({
            'status': 'error',
            'error': 'Timeout lors de la récupération des logs'
        }, status=504)
    except FileNotFoundError:
        return JsonResponse({
            'status': 'error',
            'error': 'Docker n\'est pas disponible'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


def get_spark_worker_logs(tail, since):
    """Get logs from all Spark worker containers"""
    try:
        # Find all spark worker containers
        result = subprocess.run(
            ['docker', 'ps', '-a', '--filter', 'name=mobilite-urbaine-spark-worker', '--format', '{{.Names}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        worker_containers = [name.strip() for name in result.stdout.strip().split('\n') if name.strip()]
        
        if not worker_containers:
            return JsonResponse({
                'status': 'success',
                'service': 'spark-worker',
                'container_status': 'not_found',
                'logs': 'Aucun worker Spark trouvé'
            })
        
        all_logs = []
        status = 'running'
        
        for container in worker_containers:
            # Get status
            status_result = subprocess.run(
                ['docker', 'inspect', '-f', '{{.State.Status}}', container],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Get logs
            cmd = ['docker', 'logs', '--tail', str(int(tail) // len(worker_containers))]
            if since:
                cmd.extend(['--since', since])
            cmd.append(container)
            
            log_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            logs = log_result.stdout if log_result.stdout else log_result.stderr
            all_logs.append(f"=== {container} ===\n{logs}")
        
        return JsonResponse({
            'status': 'success',
            'service': 'spark-worker',
            'container': ', '.join(worker_containers),
            'container_status': status,
            'logs': '\n\n'.join(all_logs)
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)


@require_GET
def get_all_containers_status(request):
    """Get status of all Docker containers"""
    try:
        result = subprocess.run(
            ['docker', 'ps', '-a', '--format', '{{.Names}}\t{{.Status}}\t{{.State}}'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        containers = {}
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    name, status, state = parts[0], parts[1], parts[2]
                    containers[name] = {
                        'status': status,
                        'state': state
                    }
        
        # Map to our services
        services_status = {}
        for service_id, container_name in SERVICE_CONTAINERS.items():
            if container_name:
                if container_name in containers:
                    services_status[service_id] = containers[container_name]
                else:
                    services_status[service_id] = {'status': 'not found', 'state': 'unknown'}
            else:
                # Handle spark-worker
                worker_statuses = [v for k, v in containers.items() if 'spark-worker' in k]
                if worker_statuses:
                    services_status[service_id] = worker_statuses[0]
                else:
                    services_status[service_id] = {'status': 'not found', 'state': 'unknown'}
        
        return JsonResponse({
            'status': 'success',
            'services': services_status
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        }, status=500)
