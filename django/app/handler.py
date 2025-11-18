import os
import sys
import django
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.urls import path
from django.template import Template, Context
from django.core.management import execute_from_command_line
from django.db import connection
from django.middleware.csrf import get_token

# Configuration Django inline
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production'),
        ALLOWED_HOSTS=['*'],
        ROOT_URLCONF=__name__,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.environ.get('POSTGRES_DB', 'mobilite_urbaine'),
                'USER': os.environ.get('POSTGRES_USER', 'admin'),
                'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'admin'),
                'HOST': os.environ.get('SQL_HOST', 'db'),
                'PORT': os.environ.get('SQL_PORT', '5432'),
            }
        },
        TEMPLATES=[{
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': [],
            'APP_DIRS': False,
            'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                ],
            },
        }],
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
        ],
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
        ],
    )

django.setup()

# Templates HTML intégrés
INDEX_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mobilité Urbaine</title>
</head>
<body>
    <header>
        <h1>Mobilité Urbaine</h1>
    </header>
    
    <main>
        <section>
            <h2>Bienvenue</h2>
            <p>Contenu de la page.</p>
            <ul>
                <li><a href="/db-console/">Accéder à la console base de données</a></li>
                <li><a href="/spark-upper/">Exécuter un job Spark (Upper Case)</a></li>
            </ul>
        </section>
    </main>
    
    <footer>
        <p>&copy; 2025 - 2026 Mobilité Urbaine</p>
    </footer>
</body>
</html>
"""

DB_CONSOLE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Console Base de Données</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        textarea {
            width: 100%;
            min-height: 150px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            border: 1px solid #ddd;
            border-radius: 4px;
            resize: vertical;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }
        .error {
            background-color: #f8d7da;
            border-color: #f5c6cb;
            color: #721c24;
        }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #007bff;
            text-decoration: none;
        }
        .back-link:hover {
            text-decoration: underline;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Retour à l'accueil</a>
        <h1>Console Base de Données</h1>
        <form method="POST" action="">
            <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">
            <label for="query">Entrez votre commande SQL :</label>
            <textarea id="query" name="query" placeholder="SELECT * FROM table_name;">{{ query }}</textarea>
            <button type="submit">Exécuter</button>
        </form>

        {% if result %}
        <div class="result">
            <strong>Résultat :</strong><br>
            {{ result }}
        </div>
        {% endif %}

        {% if error %}
        <div class="result error">
            <strong>Erreur :</strong><br>
            {{ error }}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

SPARKLE_STATE_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spark Job Executor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
        }
        .input-group {
            margin: 20px 0;
        }
        label {
            display: block;
            margin-bottom: 10px;
            font-weight: bold;
        }
        input[type="text"] {
            width: 100%;
            padding: 10px;
            font-size: 16px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            background-color: #28a745;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-top: 10px;
        }
        button:hover {
            background-color: #218838;
        }
        button:disabled {
            background-color: #6c757d;
            cursor: not-allowed;
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            white-space: pre-wrap;
            max-height: 500px;
            overflow-y: auto;
        }
        .success {
            background-color: #d4edda;
            border-color: #c3e6cb;
            color: #155724;
        }
        .error {
            background-color: #f8d7da;
            border-color: #f5c6cb;
            color: #721c24;
        }
        .loading {
            background-color: #d1ecf1;
            border-color: #bee5eb;
            color: #0c5460;
        }
        .back-link {
            display: inline-block;
            margin-bottom: 20px;
            color: #007bff;
            text-decoration: none;
        }
        .back-link:hover {
            text-decoration: underline;
        }
        .info-box {
            background-color: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <a href="/" class="back-link">← Retour à l'accueil</a>
        <h1>🚀 Spark Job - Upper Case</h1>
        
        <div class="info-box">
            <strong>ℹ️ Information :</strong><br>
            Ce job Spark transforme du texte en majuscules en utilisant Apache Spark distribué.
        </div>

        <form method="POST" action="">
            <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">
            
            <div class="input-group">
                <label for="input_text">Texte à transformer :</label>
                <input type="text" 
                       id="input_text" 
                       name="input_text" 
                       value="{{ input_text }}" 
                       placeholder="Entrez votre texte...">
            </div>
            
            <button type="submit">Exécuter le Job Spark</button>
        </form>

        {% if loading %}
        <div class="result loading">
            <strong>⏳ Exécution en cours...</strong><br>
            Le job Spark est en cours d'exécution. Veuillez patienter...
        </div>
        {% endif %}

        {% if result %}
        <div class="result success">
            <strong>✅ Résultat du Job Spark :</strong><br><br>
            <strong>Entrée :</strong> {{ input_text }}<br>
            <strong>Sortie :</strong> {{ result }}<br><br>
            <strong>📊 Logs complets :</strong><br>
            {{ full_output }}
        </div>
        {% endif %}

        {% if error %}
        <div class="result error">
            <strong>❌ Erreur d'exécution :</strong><br>
            {{ error }}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

def index(request):
    return HttpResponse(INDEX_HTML)


def health_check(request):
    return JsonResponse({'status': 'ok'})

def database_console(request):
    context = {
        'query': '',
        'result': '',
        'error': '',
        'csrf_token': get_token(request)
    }
    
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        context['query'] = query
        
        if query:
            try:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    
                    # Si c'est une requête SELECT, récupérer les résultats
                    if query.upper().startswith('SELECT'):
                        columns = [col[0] for col in cursor.description]
                        rows = cursor.fetchall()
                        
                        # Formatter les résultats
                        result = f"Colonnes: {', '.join(columns)}\n\n"
                        for row in rows:
                            result += ' | '.join(str(value) for value in row) + '\n'
                        
                        if not rows:
                            result += "Aucun résultat trouvé."
                        
                        context['result'] = result
                    else:
                        # Pour INSERT, UPDATE, DELETE, etc.
                        affected_rows = cursor.rowcount
                        context['result'] = f"Requête exécutée avec succès. {affected_rows} ligne(s) affectée(s)."
                        
            except Exception as e:
                context['error'] = str(e)
    
    # Utiliser le template Django pour le rendu
    template = Template(DB_CONSOLE_HTML)
    html = template.render(Context(context))
    return HttpResponse(html)

def sparkle_state(request):
    context = {
        'input_text': 'hello world',
        'result': '',
        'error': '',
        'full_output': '',
        'loading': False,
        'csrf_token': get_token(request)
    }
    
    if request.method == 'POST':
        input_text = request.POST.get('input_text', 'hello world').strip()
        context['input_text'] = input_text
        
        if input_text:
            try:
                # Importer PySpark
                from pyspark.sql import SparkSession
                from pyspark.sql.functions import upper, col
                import io
                from contextlib import redirect_stdout, redirect_stderr
                
                # Capturer les logs
                stdout_capture = io.StringIO()
                stderr_capture = io.StringIO()
                
                with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                    # Créer une session Spark
                    spark = SparkSession.builder \
                        .appName("DjangoUpperCase") \
                        .master("spark://spark-master:7077") \
                        .config("spark.executor.memory", "1g") \
                        .config("spark.executor.cores", "1") \
                        .config("spark.sql.warehouse.dir", "/tmp/spark-warehouse") \
                        .config("spark.driver.host", "web") \
                        .getOrCreate()
                    
                    # Créer un DataFrame avec le texte
                    df = spark.createDataFrame([(input_text,)], ["texte"])
                    
                    # Transformer en majuscules
                    df_upper = df.withColumn("texte_majuscule", upper(col("texte")))
                    
                    # Récupérer le résultat
                    result = df_upper.select("texte_majuscule").first()[0]
                    
                    # Arrêter Spark
                    spark.stop()
                
                # Récupérer les logs
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
                context['error'] = f"PySpark n'est pas installé:\n{str(e)}\n\nAjoutez 'pyspark' à django/requirements.txt et reconstruisez l'image Docker."
            except Exception as e:
                context['error'] = f"Erreur lors de l'exécution du job Spark:\n{type(e).__name__}: {str(e)}"
    
    template = Template(SPARKLE_STATE_HTML)
    html = template.render(Context(context))
    return HttpResponse(html)

urlpatterns = [
    path('', index, name='index'),
    path('health/', health_check, name='health_check'),
    path('db-console/', database_console, name='database_console'),
    path('spark-upper/', sparkle_state, name='sparkle_state'),
]

if __name__ == "__main__":
    execute_from_command_line(sys.argv)