from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, explode, lit
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, ArrayType, MapType
)
import sys
import json

'''
Input : Json of overpass API output data

Output : Processed data ready to be stored in DB

Utilisation : Job spark lancé via subprocess depuis une tâche Celery dans Django
'''

# Mapping basé sur les VALEURS des tags (pas les clés)
# Format: "valeur_tag": (category, subcategory)
Field_Name_Mapping_Point = {
    # Education (amenity=*)
    "school": ("education", "ecole primaire"),
    "university": ("education", "universite"),
    "kindergarten": ("education", "maternelle"),
    "college": ("education", "college"),
    "library": ("education", "bibliotheque"),

    # Santé (amenity=*)
    "hospital": ("santé", "hopital"),
    "clinic": ("santé", "clinique"),
    "pharmacy": ("santé", "pharmacie"),
    "doctors": ("santé", "medecin"),

    # Restauration (amenity=*)
    "restaurant": ("restauration", "restaurant"),
    "cafe": ("restauration", "cafe"),
    "fast_food": ("restauration", "restauration rapide"),

    # Transport (railway=*, aeroway=*, amenity=*)
    "station": ("transport", "gare"),
    "halt": ("transport", "halte ferroviaire"),
    "ferry_terminal": ("transport", "terminal de ferry"),
    "bus_station": ("transport", "gare routière"),
    "aerodrome": ("transport", "aerodrome"),

    # Commerce (shop=*)
    "supermarket": ("commerce", "supermarche"),
    "mall": ("commerce", "centre commercial"),
    "bakery": ("commerce", "boulangerie"),
    "butcher": ("commerce", "boucherie"),
    "convenience": ("commerce", "supérette"),

    # Loisirs (leisure=*, amenity=*, tourism=*)
    "sports_centre": ("loisirs", "centre sportif"),
    "fitness_centre": ("loisirs", "centre de fitness"),
    "stadium": ("loisirs", "stade"),
    "cinema": ("loisirs", "cinema"),
    "theatre": ("loisirs", "theatre"),
    "museum": ("loisirs", "musee"),
    "park": ("loisirs", "parc"),
    "music_venue": ("loisirs", "salle de concert"),

    # Industrie (industrial=*, landuse=*)
    "industrial": ("industrie", "site industriel"),
    "warehouse": ("industrie", "entrepot"),

    # Sécurité (amenity=*)
    "fire_station": ("sécurité", "caserne de pompiers"),
    "police": ("sécurité", "poste de police"),
}

Field_Name_Mapping_Area = {
    "residential": ("habitation", "résidentiel"),
    "commercial": ("commerce", "commercial"),
    "industrial": ("industrie", "industriel"),
    "forest": ("nature", "forêt"),
    "farmland": ("nature", "terre agricole"),
    "aerodrome": ("transport", "aerodrome"),
}

# Tags à vérifier pour la catégorisation
TAGS_TO_CHECK = ["amenity", "shop", "leisure", "tourism", "railway", "aeroway", "landuse", "industrial"]


# Schémas pour les DataFrames de sortie (compatibles avec les tables PostgreSQL)
POINT_SCHEMA = StructType([
    StructField("position", StringType(), True),  # WKT format: POINT(lon lat)
    StructField("category", StringType(), True),
    StructField("subcategory", StringType(), True),
    StructField("name", StringType(), True),
    StructField("description", StringType(), True)
])

AREA_SCHEMA = StructType([
    StructField("zone", StringType(), True),  # WKT format: POLYGON((...))
    StructField("category", StringType(), True),
    StructField("subcategory", StringType(), True),
    StructField("name", StringType(), True),
    StructField("description", StringType(), True)
])


def is_point(element):
    """
    Vérifie si l'élément est un point.
    - type 'node' avec lat/lon
    - type 'way'/'relation' avec center mais sans geometry (out center)
    - type 'way'/'relation' avec geometry mais c'est une ligne (pas un polygone fermé)
    """
    elem_type = element.get("type")
    
    # Les nodes sont toujours des points
    if elem_type == "node":
        return "lat" in element and "lon" in element
    
    # Si on a une geometry, vérifier si c'est un polygone ou une ligne
    if "geometry" in element:
        geometry = element.get("geometry", [])
        if isinstance(geometry, list) and len(geometry) >= 3:
            # C'est un polygone si le premier et dernier point sont proches
            # (fermé) - donc c'est une zone, pas un point
            first = geometry[0]
            last = geometry[-1]
            if abs(first.get("lat", 0) - last.get("lat", 0)) < 0.0001 and \
               abs(first.get("lon", 0) - last.get("lon", 0)) < 0.0001:
                return False  # C'est une zone
        # Sinon on le traite comme un point (via son centre)
        if "center" in element:
            return True
        # Calculer le centre à partir de geometry si pas de center
        if geometry:
            return True
    
    # Si on a center mais pas de geometry, c'est un point
    if "center" in element:
        return True
    
    # Si on a lat/lon directement
    if "lat" in element and "lon" in element:
        return True
    
    return False


def is_area(element):
    """
    Vérifie si l'élément est une zone (polygone fermé).
    """
    if "geometry" not in element:
        return False
    geometry = element.get("geometry")
    if not isinstance(geometry, list) or len(geometry) < 3:
        return False
    
    # Vérifier si c'est un polygone fermé
    first = geometry[0]
    last = geometry[-1]
    is_closed = abs(first.get("lat", 0) - last.get("lat", 0)) < 0.0001 and \
                abs(first.get("lon", 0) - last.get("lon", 0)) < 0.0001
    
    return is_closed


def get_category_from_tags(tags, mapping):
    """
    Cherche dans les tags une valeur correspondant au mapping.
    Retourne (category, subcategory) ou (None, None) si non trouvé.
    """
    if not tags:
        return (None, None)
    
    for tag_key in TAGS_TO_CHECK:
        if tag_key in tags:
            tag_value = tags[tag_key]
            if tag_value in mapping:
                return mapping[tag_value]
    return (None, None)


def build_address(tags):
    """Construit une adresse à partir des tags disponibles."""
    if not tags:
        return "unknown"
    
    parts = []
    if "addr:housenumber" in tags:
        parts.append(tags["addr:housenumber"])
    if "addr:street" in tags:
        parts.append(tags["addr:street"])
    if "addr:city" in tags:
        parts.append(tags["addr:city"])
    if "addr:postcode" in tags:
        parts.append(tags["addr:postcode"])
    if "addr:country" in tags:
        parts.append(tags["addr:country"])
    
    return ", ".join(parts) if parts else "unknown"


def process_point(element):
    """Traite un élément de type point."""
    if element is None:
        return None
        
    compressed_element = {}
    
    # Extraction des coordonnées
    try:
        if "center" in element:
            lat = float(element["center"]["lat"])
            lon = float(element["center"]["lon"])
            compressed_element["position"] = f"POINT({lon} {lat})"
        elif "lat" in element and "lon" in element:
            lat = float(element["lat"])
            lon = float(element["lon"])
            compressed_element["position"] = f"POINT({lon} {lat})"
        elif "geometry" in element:
            # Calculer le centre à partir de la geometry
            geometry = element.get("geometry", [])
            if geometry:
                lats = [float(p["lat"]) for p in geometry if "lat" in p]
                lons = [float(p["lon"]) for p in geometry if "lon" in p]
                if lats and lons:
                    lat = sum(lats) / len(lats)
                    lon = sum(lons) / len(lons)
                    compressed_element["position"] = f"POINT({lon} {lat})"
                else:
                    return None
            else:
                return None
        else:
            return None  # Not a point
    except (KeyError, TypeError, ValueError) as e:
        print(f"⚠️ Erreur extraction coordonnées point: {e}")
        return None
    
    tags = element.get("tags", {})
    
    # Catégorisation
    category, subcategory = get_category_from_tags(tags, Field_Name_Mapping_Point)
    compressed_element["category"] = category if category else "autre"
    compressed_element["subcategory"] = subcategory if subcategory else "non classé"
    
    # Informations de base
    compressed_element["name"] = tags.get("name", tags.get("official_name", "unknown"))
    
    # Description enrichie (inclut l'adresse)
    description_parts = []
    address = build_address(tags)
    if address != "unknown":
        description_parts.append(f"Adresse: {address}")
    if "cuisine" in tags:
        description_parts.append(f"Cuisine: {tags['cuisine']}")
    if "opening_hours" in tags:
        description_parts.append(f"Horaires: {tags['opening_hours']}")
    if "phone" in tags:
        description_parts.append(f"Tél: {tags['phone']}")
    if "website" in tags:
        description_parts.append(f"Web: {tags['website']}")
    if "operator" in tags:
        description_parts.append(f"Opérateur: {tags['operator']}")
    if "iata" in tags:
        description_parts.append(f"IATA: {tags['iata']}")
    if "icao" in tags:
        description_parts.append(f"ICAO: {tags['icao']}")
    
    compressed_element["description"] = "; ".join(description_parts) if description_parts else None
    
    return compressed_element


def process_area(element):
    """Traite un élément de type zone/area."""
    if element is None:
        return None
        
    compressed_element = {}
    
    if "geometry" not in element:
        return None
    
    try:
        geometry = element["geometry"]
        if not isinstance(geometry, list) or len(geometry) < 3:
            return None
        coords = [(float(point["lon"]), float(point["lat"])) for point in geometry]
        
        # Fermer le polygone si nécessaire (le premier et dernier point doivent être identiques)
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        
        coords_str = ', '.join([f'{lon} {lat}' for lon, lat in coords])
        compressed_element["zone"] = f"POLYGON(({coords_str}))"
    except (KeyError, TypeError, ValueError) as e:
        print(f"⚠️ Erreur extraction géométrie zone: {e}")
        return None
    
    tags = element.get("tags", {})
    
    # Catégorisation
    category, subcategory = get_category_from_tags(tags, Field_Name_Mapping_Area)
    compressed_element["category"] = category if category else "autre"
    compressed_element["subcategory"] = subcategory if subcategory else "non classé"
    
    # Informations de base
    compressed_element["name"] = tags.get("name", tags.get("official_name", "unknown"))
    
    # Description (inclut l'adresse)
    description_parts = []
    address = build_address(tags)
    if address != "unknown":
        description_parts.append(f"Adresse: {address}")
    if "landuse" in tags:
        description_parts.append(f"Usage: {tags['landuse']}")
    if "surface" in tags:
        description_parts.append(f"Surface: {tags['surface']}")
    
    compressed_element["description"] = "; ".join(description_parts) if description_parts else None
    
    return compressed_element


def main(input_json):
    """
    Fonction principale de traitement.
    
    Args:
        input_json: JSON string ou dict (obligatoire).
    
    Returns:
        Tuple (points_df, areas_df) ou (None, None) en cas d'erreur.
    """
    # Créer la session Spark avec configuration optimisée
    spark = SparkSession.builder \
        .appName("MapDataProcess") \
        .master("spark://spark-master:7077") \
        .config("spark.sql.shuffle.partitions", "8") \
        .config("spark.default.parallelism", "8") \
        .getOrCreate()
    
    print("[Job] 🚀 Démarrage du job MapDataProcess")

    # Récupération des données JSON
    data = None
    
    if isinstance(input_json, dict):
        data = input_json
    else:
        try:
            data = json.loads(input_json)
        except json.JSONDecodeError as e:
            print(f"❌ Erreur de parsing JSON: {e}")
            spark.stop()
            return None, None

    if data is None:
        print("⚠️ Aucune donnée valide")
        spark.stop()
        return None, None

    elements = data.get("elements", [])

    if not elements:
        print("⚠️ Aucun élément à traiter")
        spark.stop()
        return None, None

    print(f"[Job] 📊 Nombre d'éléments à traiter: {len(elements)}")

    # Séparer les éléments en points et zones AVANT la parallélisation
    point_elements = [e for e in elements if is_point(e)]
    area_elements = [e for e in elements if is_area(e)]

    # Log des types détectés pour debug
    types_count = {}
    for e in elements:
        t = e.get("type", "unknown")
        has_center = "center" in e
        has_geometry = "geometry" in e
        has_latlon = "lat" in e and "lon" in e
        key = f"{t}(center={has_center},geom={has_geometry},latlon={has_latlon})"
        types_count[key] = types_count.get(key, 0) + 1
    print(f"[Job] 📋 Types détectés: {types_count}")

    print(f"[Job] 📍 Points détectés: {len(point_elements)}")
    print("ça fonctionne...")
    print(f"[Job] 🗺️ Zones détectées: {len(area_elements)}")

    points_df = None
    areas_df = None

    # Traitement des points
    if point_elements:
        num_slices = max(1, min(len(point_elements) // 100 + 1, 8))
        points_rdd = spark.sparkContext.parallelize(point_elements, numSlices=num_slices)
        points_rdd = points_rdd.map(process_point).filter(lambda x: x is not None)
        
        if not points_rdd.isEmpty():
            points_df = spark.createDataFrame(points_rdd, schema=POINT_SCHEMA)
            points_df.cache()
            points_count = points_df.count()
            print(f"✅ Points traités avec succès: {points_count}")

    # Traitement des zones
    if area_elements:
        num_slices = max(1, min(len(area_elements) // 100 + 1, 8))
        areas_rdd = spark.sparkContext.parallelize(area_elements, numSlices=num_slices)
        areas_rdd = areas_rdd.map(process_area).filter(lambda x: x is not None)
        
        if not areas_rdd.isEmpty():
            areas_df = spark.createDataFrame(areas_rdd, schema=AREA_SCHEMA)
            areas_df.cache()
            areas_count = areas_df.count()
            print(f"✅ Zones traitées avec succès: {areas_count}")

    print("[Job] 🏁 Job terminé avec succès")
    
    return points_df, areas_df


def save_to_postgres(points_df, areas_df, db_config):
    """
    Sauvegarde les DataFrames dans PostgreSQL/PostGIS.
    
    - points_df -> table 'poi' (nom, position, type, subtype, description)
    - areas_df -> table 'zone' (geom, type, subtype, description)
    """
    import psycopg2
    from psycopg2.extras import execute_batch
    
    conn = None
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"]
        )
        cursor = conn.cursor()
        
        points_inserted = 0
        zones_inserted = 0
        
        # Insérer les points dans la table 'poi'
        if points_df is not None:
            points_data = points_df.collect()
            if points_data:
                print(f"[DB] 📍 Insertion de {len(points_data)} points dans la table 'poi'...")
                
                insert_query = """
                    INSERT INTO poi (nom, position, type, subtype, description)
                    VALUES (%s, ST_GeomFromText(%s, 4326), %s, %s, %s)
                """
                
                batch_data = [
                    (
                        row["name"],
                        row["position"],
                        row["category"],
                        row["subcategory"],
                        row["description"]
                    )
                    for row in points_data
                ]
                
                execute_batch(cursor, insert_query, batch_data, page_size=100)
                points_inserted = len(batch_data)
                print(f"[DB] ✅ {points_inserted} points insérés avec succès")
        
        # Insérer les zones dans la table 'zone'
        if areas_df is not None:
            areas_data = areas_df.collect()
            if areas_data:
                print(f"[DB] 🗺️ Insertion de {len(areas_data)} zones dans la table 'zone'...")
                
                insert_query = """
                    INSERT INTO zone (geom, type, subtype, description)
                    VALUES (ST_GeomFromText(%s, 4326), %s, %s, %s)
                """
                
                batch_data = [
                    (
                        row["zone"],
                        row["category"],
                        row["subcategory"],
                        row["description"]
                    )
                    for row in areas_data
                ]
                
                execute_batch(cursor, insert_query, batch_data, page_size=100)
                zones_inserted = len(batch_data)
                print(f"[DB] ✅ {zones_inserted} zones insérées avec succès")
        
        conn.commit()
        print(f"[DB] 🎉 Sauvegarde terminée: {points_inserted} POI, {zones_inserted} zones")
        return True
        
    except Exception as e:
        print(f"[DB] ❌ Erreur lors de la sauvegarde: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    import os
    import argparse

    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description='Traitement des données de carte Overpass')
    parser.add_argument('--input', type=str, required=True, help='Chemin vers le fichier JSON d\'entrée')
    parser.add_argument('--job-id', type=str, default='unknown', help='Identifiant du job')
    args = parser.parse_args()

    print(f"🚀 Lancement du traitement des données de la carte")
    print(f"   Job ID: {args.job_id}")
    print(f"   Fichier d'entrée: {args.input}")
    
    # Lire le fichier JSON d'entrée
    if not os.path.exists(args.input):
        print(f"❌ Fichier d'entrée non trouvé: {args.input}")
        sys.exit(1)
    
    with open(args.input, 'r') as f:
        input_json = f.read()
    
    points_df, areas_df = main(input_json)

    # Afficher un aperçu des données traitées
    if points_df is not None:
        count = points_df.count()
        if count > 0:
            print(f"\n📍 Aperçu des {count} points traités:")
            points_df.show(5, truncate=50)
    
    if areas_df is not None:
        count = areas_df.count()
        if count > 0:
            print(f"\n🗺️ Aperçu des {count} zones traitées:")
            areas_df.show(5, truncate=50)

    # Sauvegarde en base de données PostgreSQL/PostGIS
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "db"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "database": os.getenv("POSTGRES_DB", "mobilite_urbaine"),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "admin")
    }
    
    print(f"\n[DB] 💾 Connexion à PostgreSQL ({db_config['host']}:{db_config['port']})...")
    
    if points_df is not None or areas_df is not None:
        success = save_to_postgres(points_df, areas_df, db_config)
        if success:
            print("[Job] ✅ Données sauvegardées en base avec succès")
        else:
            print("[Job] ⚠️ Erreur lors de la sauvegarde en base")
    else:
        print("[Job] ℹ️ Aucune donnée à sauvegarder")

    # Nettoyage du fichier d'entrée après traitement réussi
    try:
        os.remove(args.input)
        print(f"[Job] 🗑️ Fichier d'entrée supprimé: {args.input}")
    except Exception as e:
        print(f"[Job] ⚠️ Impossible de supprimer le fichier d'entrée: {e}")

    print("[Job] 🏁 Phase de calcul terminée.")

    # Arrêter Spark proprement
    SparkSession.builder.getOrCreate().stop()

