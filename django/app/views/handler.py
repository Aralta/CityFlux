"""
Gestionnaire des vues pour la console base de données et les jobs Spark
"""
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django.views.decorators.csrf import csrf_protect


def index(request):
    """Page d'accueil"""
    return render(request, 'index.html')


def health_check(request):
    """Endpoint de santé"""
    return JsonResponse({'status': 'ok'})


@csrf_protect
def database_console(request):
    """Console de base de données interactive"""
    context = {
        'query': '',
        'result': '',
        'error': ''
    }
    
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        context['query'] = query
        
        if query:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    
                    if query.upper().startswith('SELECT'):
                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        
                        result = f"Colonnes: {', '.join(columns)}\n\n"
                        for row in rows:
                            result += ' | '.join(str(value) for value in row) + '\n'
                        
                        if not rows:
                            result += "Aucun résultat trouvé."
                        
                        context['result'] = result
                    else:
                        affected_rows = cursor.rowcount
                        context['result'] = f"Requête exécutée avec succès. {affected_rows} ligne(s) affectée(s)."
                        
            except Exception as e:
                context['error'] = str(e)
    
    return render(request, 'db_console.html', context)


@csrf_protect
def spark_upper(request):
    """Exécution d'un job Spark pour transformer en majuscules"""
    context = {
        'input_text': 'hello world',
        'result': '',
        'error': '',
        'full_output': '',
        'loading': False
    }
    
    if request.method == 'POST':
        input_text = request.POST.get('input_text', 'hello world').strip()
        context['input_text'] = input_text
        
        if input_text:
            try:
                from pyspark.sql import SparkSession
                from pyspark.sql.functions import upper, col
                import io
                from contextlib import redirect_stdout, redirect_stderr
                
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    spark = SparkSession.builder \
                        .appName("DjangoUpperCase") \
                        .master("spark://spark-master:7077") \
                        .config("spark.executor.memory", "1g") \
                        .config("spark.executor.cores", "1") \
                        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
                        .config("spark.driver.host", "web") \
                        .getOrCreate()
                    
                    df = spark.createDataFrame([(input_text,)], ["texte"])
                    df_upper = df.withColumn("texte_majuscule", upper(col("texte")))
                    result = df_upper.select("texte_majuscule").first()[0]
                    spark.stop()
                
                stdout_logs = stdout_capture.getvalue()
                stderr_logs = stderr_capture.getvalue()
                
                context['result'] = result
                context['full_output'] = f"""✅ Transformation réussie via Apache Spark

📥 Entrée: {input_text}
📤 Sortie: {result}

📊 Informations du job:
- Application: DjangoUpperCase
- Master: spark://spark-master:7077
- Executor Memory: 1g
- Executor Cores: 1

📝 Logs (dernières lignes):
{stdout_logs[-500:] if stdout_logs else 'Aucun log stdout'}
{stderr_logs[-500:] if stderr_logs else ''}
"""
                
            except ImportError as e:
                context['error'] = f"PySpark n'est pas installé:\n{str(e)}\n\nAjoutez 'pyspark' à requirements.txt"
            except Exception as e:
                context['error'] = f"Erreur lors de l'exécution du job Spark:\n{type(e).__name__}: {str(e)}"
    
    return render(request, 'spark_upper.html', context)


def render_enhanced_data(request):
    """Rendu de la page des données enrichies"""
    return render(request, 'enhanced_data.html')

def conversion_view(request):
    """Page de l'outil de conversion de données"""
    return render(request, 'conversion.html')


def compute_view(request):
    """Page des scripts d'analyse"""
    return render(request, 'compute.html')


def compute_wiki_view(request):
    """Page wiki pour créer un nouveau module"""
    return render(request, 'compute_wiki.html')


def mode_guesser_view(request):
    """Page du Transport Mode Guesser"""
    from views.database import db_manager
    
    trajectory_ids = []
    try:
        if db_manager.connect():
            trajectory_ids = db_manager.get_trajectory_ids()
            db_manager.disconnect()
    except Exception as e:
        print(f"Error fetching trajectory IDs: {e}")
    
    return render(request, 'mode_guesser.html', {'trajectory_ids': trajectory_ids})


def trip_purpose_guesser_view(request):
    """Page du Trip Purpose Guesser"""
    from views.database import db_manager
    
    trajectory_ids = []
    try:
        if db_manager.connect():
            trajectory_ids = db_manager.get_trajectory_ids()
            db_manager.disconnect()
    except Exception as e:
        print(f"Error fetching trajectory IDs: {e}")
    
    return render(request, 'trip_purpose_guesser.html', {'trajectory_ids': trajectory_ids})


def analytics_view(request):
    """Page du dashboard analytics"""
    return render(request, 'analytics.html')


def heatmap_wip_view(request):
    """Page Work in Progress pour Heatmap"""
    return render(request, 'heatmap_wip.html')


def congestion_wip_view(request):
    """Page Work in Progress pour Encombrement des Routes"""
    return render(request, 'congestion_wip.html')