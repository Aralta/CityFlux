"""
Traitement des données de carte Overpass avec Spark.
Transforme les données OSM en POI et zones pour PostgreSQL/PostGIS.
"""
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType
import sys
import json
import os


# =============================================================================
# CONFIGURATION DES MAPPINGS
# =============================================================================

# Mapping des valeurs de tags OSM vers (category, subcategory) pour les points
POINT_CATEGORY_MAPPING = {
    # Education
    "school": ("education", "ecole primaire"),
    "university": ("education", "universite"),
    "kindergarten": ("education", "maternelle"),
    "college": ("education", "college"),
    "library": ("education", "bibliotheque"),
    # Santé
    "hospital": ("santé", "hopital"),
    "clinic": ("santé", "clinique"),
    "pharmacy": ("santé", "pharmacie"),
    "doctors": ("santé", "medecin"),
    # Restauration
    "restaurant": ("restauration", "restaurant"),
    "cafe": ("restauration", "cafe"),
    "fast_food": ("restauration", "restauration rapide"),
    # Transport
    "station": ("transport", "gare"),
    "halt": ("transport", "halte ferroviaire"),
    "ferry_terminal": ("transport", "terminal de ferry"),
    "bus_station": ("transport", "gare routière"),
    "aerodrome": ("transport", "aerodrome"),
    # Commerce
    "supermarket": ("commerce", "supermarche"),
    "mall": ("commerce", "centre commercial"),
    "bakery": ("commerce", "boulangerie"),
    "butcher": ("commerce", "boucherie"),
    "convenience": ("commerce", "supérette"),
    # Loisirs
    "sports_centre": ("loisirs", "centre sportif"),
    "fitness_centre": ("loisirs", "centre de fitness"),
    "stadium": ("loisirs", "stade"),
    "cinema": ("loisirs", "cinema"),
    "theatre": ("loisirs", "theatre"),
    "museum": ("loisirs", "musee"),
    "park": ("loisirs", "parc"),
    "music_venue": ("loisirs", "salle de concert"),
    # Industrie
    "industrial": ("industrie", "site industriel"),
    "warehouse": ("industrie", "entrepot"),
    # Sécurité
    "fire_station": ("sécurité", "caserne de pompiers"),
    "police": ("sécurité", "poste de police"),
}

# Mapping pour les zones
AREA_CATEGORY_MAPPING = {
    "residential": ("habitation", "résidentiel"),
    "commercial": ("commerce", "commercial"),
    "industrial": ("industrie", "industriel"),
    "forest": ("nature", "forêt"),
    "farmland": ("nature", "terre agricole"),
    "aerodrome": ("transport", "aerodrome"),
}

# Tags OSM à vérifier pour la catégorisation
TAGS_TO_CHECK = ["amenity", "shop", "leisure", "tourism", "railway", "aeroway", "landuse", "industrial"]

# Champs d'adresse OSM
ADDRESS_FIELDS = ["addr:housenumber", "addr:street", "addr:city", "addr:postcode", "addr:country"]

# Champs de description pour les points
POINT_DESCRIPTION_FIELDS = {
    "cuisine": "Cuisine",
    "opening_hours": "Horaires",
    "phone": "Tél",
    "website": "Web",
    "operator": "Opérateur",
    "iata": "IATA",
    "icao": "ICAO"
}

# Schémas Spark
POINT_SCHEMA = StructType([
    StructField("position", StringType(), True),
    StructField("category", StringType(), True),
    StructField("subcategory", StringType(), True),
    StructField("name", StringType(), True),
    StructField("description", StringType(), True)
])

AREA_SCHEMA = StructType([
    StructField("zone", StringType(), True),
    StructField("category", StringType(), True),
    StructField("subcategory", StringType(), True),
    StructField("name", StringType(), True),
    StructField("description", StringType(), True)
])


# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def get_category(tags, mapping):
    """Cherche dans les tags une valeur correspondant au mapping."""
    if not tags:
        return ("autre", "non classé")
    
    for tag_key in TAGS_TO_CHECK:
        tag_value = tags.get(tag_key)
        if tag_value and tag_value in mapping:
            return mapping[tag_value]
    
    return ("autre", "non classé")


def build_address(tags):
    """Construit une adresse à partir des tags disponibles."""
    if not tags:
        return None
    
    parts = [tags.get(field) for field in ADDRESS_FIELDS if tags.get(field)]
    return ", ".join(parts) if parts else None


def extract_coords_from_geometry(geometry):
    """Extrait lat/lon moyens d'une liste de points de géométrie."""
    if not geometry:
        return None, None
    
    lats = [float(p["lat"]) for p in geometry if "lat" in p]
    lons = [float(p["lon"]) for p in geometry if "lon" in p]
    
    if not lats or not lons:
        return None, None
    
    return sum(lats) / len(lats), sum(lons) / len(lons)


def is_closed_polygon(geometry):
    """Vérifie si une géométrie est un polygone fermé."""
    if not isinstance(geometry, list) or len(geometry) < 3:
        return False
    
    first, last = geometry[0], geometry[-1]
    return (abs(first.get("lat", 0) - last.get("lat", 0)) < 0.0001 and
            abs(first.get("lon", 0) - last.get("lon", 0)) < 0.0001)


def is_point(element):
    """Vérifie si l'élément est un point."""
    elem_type = element.get("type")
    
    if elem_type == "node":
        return "lat" in element and "lon" in element
    
    if "geometry" in element:
        if is_closed_polygon(element["geometry"]):
            return False
        return "center" in element or element["geometry"]
    
    return "center" in element or ("lat" in element and "lon" in element)


def is_area(element):
    """Vérifie si l'élément est une zone (polygone fermé)."""
    return "geometry" in element and is_closed_polygon(element["geometry"])


# =============================================================================
# FONCTIONS DE TRAITEMENT
# =============================================================================

def process_point(element):
    """Traite un élément de type point."""
    if element is None:
        return None
    
    try:
        # Extraction des coordonnées
        lat, lon = None, None
        
        if "center" in element:
            lat = float(element["center"]["lat"])
            lon = float(element["center"]["lon"])
        elif "lat" in element and "lon" in element:
            lat = float(element["lat"])
            lon = float(element["lon"])
        elif "geometry" in element:
            lat, lon = extract_coords_from_geometry(element["geometry"])
        
        if lat is None or lon is None:
            return None
        
        tags = element.get("tags", {})
        category, subcategory = get_category(tags, POINT_CATEGORY_MAPPING)
        
        # Construction de la description
        desc_parts = []
        address = build_address(tags)
        if address:
            desc_parts.append(f"Adresse: {address}")
        
        for field, label in POINT_DESCRIPTION_FIELDS.items():
            if field in tags:
                desc_parts.append(f"{label}: {tags[field]}")
        
        return {
            "position": f"POINT({lon} {lat})",
            "category": category,
            "subcategory": subcategory,
            "name": tags.get("name", tags.get("official_name", "unknown")),
            "description": "; ".join(desc_parts) if desc_parts else None
        }
        
    except (KeyError, TypeError, ValueError):
        return None


def process_area(element):
    """Traite un élément de type zone/area."""
    if element is None or "geometry" not in element:
        return None
    
    try:
        geometry = element["geometry"]
        if not isinstance(geometry, list) or len(geometry) < 3:
            return None
        
        coords = [(float(p["lon"]), float(p["lat"])) for p in geometry]
        
        # Fermer le polygone si nécessaire
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        
        tags = element.get("tags", {})
        category, subcategory = get_category(tags, AREA_CATEGORY_MAPPING)
        
        # Construction de la description
        desc_parts = []
        address = build_address(tags)
        if address:
            desc_parts.append(f"Adresse: {address}")
        if "landuse" in tags:
            desc_parts.append(f"Usage: {tags['landuse']}")
        if "surface" in tags:
            desc_parts.append(f"Surface: {tags['surface']}")
        
        coords_str = ', '.join([f'{lon} {lat}' for lon, lat in coords])
        
        return {
            "zone": f"POLYGON(({coords_str}))",
            "category": category,
            "subcategory": subcategory,
            "name": tags.get("name", tags.get("official_name", "unknown")),
            "description": "; ".join(desc_parts) if desc_parts else None
        }
        
    except (KeyError, TypeError, ValueError):
        return None


# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main(input_json):
    """
    Fonction principale de traitement Spark.
    
    Returns:
        Tuple (points_df, areas_df) ou (None, None) en cas d'erreur.
    """
    spark = SparkSession.builder \
        .appName("MapDataProcess") \
        .master("spark://spark-master:7077") \
        .config("spark.sql.shuffle.partitions", "8") \
        .config("spark.default.parallelism", "8") \
        .getOrCreate()
    
    # Parse du JSON
    data = input_json if isinstance(input_json, dict) else None
    if data is None:
        try:
            data = json.loads(input_json)
        except json.JSONDecodeError:
            spark.stop()
            return None, None

    elements = data.get("elements", []) if data else []
    if not elements:
        spark.stop()
        return None, None

    # Séparation points/zones
    point_elements = [e for e in elements if is_point(e)]
    area_elements = [e for e in elements if is_area(e)]

    points_df, areas_df = None, None

    # Traitement des points
    if point_elements:
        num_slices = max(1, min(len(point_elements) // 100 + 1, 8))
        points_rdd = spark.sparkContext.parallelize(point_elements, numSlices=num_slices)
        points_rdd = points_rdd.map(process_point).filter(lambda x: x is not None)
        
        if not points_rdd.isEmpty():
            points_df = spark.createDataFrame(points_rdd, schema=POINT_SCHEMA)
            points_df.cache()

    # Traitement des zones
    if area_elements:
        num_slices = max(1, min(len(area_elements) // 100 + 1, 8))
        areas_rdd = spark.sparkContext.parallelize(area_elements, numSlices=num_slices)
        areas_rdd = areas_rdd.map(process_area).filter(lambda x: x is not None)
        
        if not areas_rdd.isEmpty():
            areas_df = spark.createDataFrame(areas_rdd, schema=AREA_SCHEMA)
            areas_df.cache()

    return points_df, areas_df


def save_to_postgres(points_df, areas_df, db_config):
    """Sauvegarde les DataFrames dans PostgreSQL/PostGIS."""
    import psycopg2
    from psycopg2.extras import execute_batch
    
    conn = None
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Insérer les points
        if points_df is not None:
            points_data = points_df.collect()
            if points_data:
                execute_batch(
                    cursor,
                    "INSERT INTO poi (nom, position, type, subtype, description) VALUES (%s, ST_GeomFromText(%s, 4326), %s, %s, %s)",
                    [(r["name"], r["position"], r["category"], r["subcategory"], r["description"]) for r in points_data],
                    page_size=100
                )
        
        # Insérer les zones
        if areas_df is not None:
            areas_data = areas_df.collect()
            if areas_data:
                execute_batch(
                    cursor,
                    "INSERT INTO zone (geom, type, subtype, description) VALUES (ST_GeomFromText(%s, 4326), %s, %s, %s)",
                    [(r["zone"], r["category"], r["subcategory"], r["description"]) for r in areas_data],
                    page_size=100
                )
        
        conn.commit()
        return True
        
    except Exception:
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Traitement des données Overpass')
    parser.add_argument('--input', type=str, required=True, help='Fichier JSON d\'entrée')
    parser.add_argument('--job-id', type=str, default='unknown', help='ID du job')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        sys.exit(1)
    
    with open(args.input, 'r') as f:
        input_json = f.read()
    
    points_df, areas_df = main(input_json)

    # Sauvegarde en base
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "db"),
        "port": os.getenv("POSTGRES_PORT", "5432"),
        "database": os.getenv("POSTGRES_DB", "mobilite_urbaine"),
        "user": os.getenv("POSTGRES_USER", "admin"),
        "password": os.getenv("POSTGRES_PASSWORD", "admin")
    }
    
    if points_df is not None or areas_df is not None:
        save_to_postgres(points_df, areas_df, db_config)

    # Nettoyage
    try:
        os.remove(args.input)
    except Exception:
        pass

    SparkSession.builder.getOrCreate().stop()

