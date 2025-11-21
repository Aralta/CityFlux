"""
Gestionnaire des vues pour la console base de données et les jobs Spark
"""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.db import connection
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect


def index(request):
    """Page d'accueil"""
    return render(request, 'index.html')


def health_check(request):
    """Endpoint de santé"""
    try:
        # Tester la connexion à la base de données
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return JsonResponse({
            'status': 'ok',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'database': 'disconnected',
            'error': str(e)
        }, status=500)


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