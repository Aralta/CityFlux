import os
import time
from pyspark.sql import SparkSession

def wait_for_services():
    """Attend que les services soient prêts"""
    print("⏳ Attente des services...")
    time.sleep(10)  # Attend que Spark et Postgres soient prêts

def main():
    wait_for_services()
    
    print("🚀 Démarrage du preprocessing...")
    
    # Configuration Spark
    spark = SparkSession.builder \
        .appName("MobilityPreprocessing") \
        .master(os.getenv("SPARK_MASTER", "local[*]")) \
        .config("spark.jars", "/opt/spark/jars/postgresql-42.7.4.jar") \
        .getOrCreate()
    
    print("✅ SparkSession créée")
    
    # Configuration PostgreSQL
    jdbc_url = f"jdbc:postgresql://{os.getenv('SQL_HOST')}:{os.getenv('SQL_PORT')}/{os.getenv('SQL_DB')}"
    connection_properties = {
        "user": os.getenv('SQL_USER'),
        "password": os.getenv('SQL_PASSWORD'),
        "driver": "org.postgresql.Driver"
    }
    
    print(f"📊 Connexion à: {jdbc_url}")
    
    # Exemple: lecture depuis /data
    data_path = "/data"
    if os.path.exists(data_path):
        print(f"📂 Répertoire /data trouvé")
        # df = spark.read.csv(f"{data_path}/your_file.csv", header=True)
        # df.write.jdbc(url=jdbc_url, table="your_table", mode="overwrite", properties=connection_properties)
    
    print("✅ Preprocessing terminé!")
    spark.stop()

if __name__ == "__main__":
    main()