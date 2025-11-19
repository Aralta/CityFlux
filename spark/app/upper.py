from pyspark.sql import SparkSession
from pyspark.sql.functions import upper, col
import sys

def main():
    # Créer la session Spark
    spark = SparkSession.builder \
        .appName("UpperCaseJob") \
        .master("spark://spark-master:7077") \
        .getOrCreate()
    
    print("🚀 Démarrage du job UpperCase")
    
    # Récupérer le texte depuis les arguments ou utiliser un texte par défaut
    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
    else:
        input_text = "Bonjour, ceci est un test de transformation en majuscules avec Apache Spark!"
    
    print(f"📝 Texte d'entrée: {input_text}")
    
    # Créer un DataFrame avec le texte
    df = spark.createDataFrame([(input_text,)], ["texte"])
    
    # Transformer en majuscules
    df_upper = df.withColumn("texte_majuscule", upper(col("texte")))
    
    # Afficher les résultats
    print("\n✅ Résultats:")
    df_upper.show(truncate=False)
    
    # Récupérer le résultat
    result = df_upper.select("texte_majuscule").first()[0]
    print(f"\n🎯 Texte en majuscules: {result}")
    
    # Arrêter Spark
    spark.stop()
    print("✨ Job terminé avec succès!")

if __name__ == "__main__":
    main()