# trip_purpose_guesser.py
"""
Spark script to guess trip purpose from GNSS trajectory data.

For each trajectory:
1. Finds the departure point (first timestamp) and arrival point (last timestamp)
2. Queries nearby POIs and zones using PostGIS spatial functions
3. Classifies the trip purpose based on destination type

Trip purpose categories:
- domicile: residential areas
- travail: offices, commercial, industrial
- courses: supermarket, bakery, shops
- loisirs: cinema, restaurant, park
- sante: hospital, pharmacy
- education: school, university
- transport: station, bus stop
- autre: unknown
"""

import argparse
import json
import os
import redis
import math

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, first, last, min as spark_min, max as spark_max


# Trip purpose classification based on POI/zone types
# Updated to match actual database values
PURPOSE_MAPPING = {
    # ========== DOMICILE (Residential) ==========
    'residential': 'domicile',
    'résidentiel': 'domicile',
    'habitation': 'domicile',
    'house': 'domicile',
    'apartment': 'domicile',
    'home': 'domicile',
    'maison': 'domicile',
    'appartement': 'domicile',
    
    # ========== TRAVAIL (Work) ==========
    'office': 'travail',
    'commercial': 'travail',
    'industrial': 'travail',
    'industriel': 'travail',
    'industrie': 'travail',
    'business': 'travail',
    'bureau': 'travail',
    'entreprise': 'travail',
    'mairie': 'travail',
    'administration': 'travail',
    
    # ========== COURSES (Shopping) ==========
    'supermarket': 'courses',
    'supermarche': 'courses',
    'supermarché': 'courses',
    'bakery': 'courses',
    'boulangerie': 'courses',
    'shop': 'courses',
    'mall': 'courses',
    'market': 'courses',
    'grocery': 'courses',
    'magasin': 'courses',
    'commerce': 'courses',
    
    # ========== LOISIRS (Leisure) ==========
    'cinema': 'loisirs',
    'cinéma': 'loisirs',
    'restaurant': 'loisirs',
    'restauration': 'loisirs',
    'bar': 'loisirs',
    'cafe': 'loisirs',
    'café': 'loisirs',
    'park': 'loisirs',
    'parc': 'loisirs',
    'museum': 'loisirs',
    'musée': 'loisirs',
    'theatre': 'loisirs',
    'théâtre': 'loisirs',
    'sport': 'loisirs',
    'gym': 'loisirs',
    'culture': 'loisirs',
    'danse': 'loisirs',
    'nature': 'loisirs',
    
    # ========== SANTE (Health) ==========
    'hospital': 'sante',
    'hopital': 'sante',
    'hôpital': 'sante',
    'pharmacy': 'sante',
    'pharmacie': 'sante',
    'clinic': 'sante',
    'clinique': 'sante',
    'doctor': 'sante',
    'medecin': 'sante',
    'médecin': 'sante',
    'santé': 'sante',
    'sante': 'sante',
    
    # ========== EDUCATION ==========
    'school': 'education',
    'ecole': 'education',
    'école': 'education',
    'ecole primaire': 'education',
    'maternelle': 'education',
    'university': 'education',
    'universite': 'education',
    'université': 'education',
    'college': 'education',
    'collège': 'education',
    'lycée': 'education',
    'lycee': 'education',
    'library': 'education',
    'bibliotheque': 'education',
    'bibliothèque': 'education',
    'education': 'education',
    
    # ========== TRANSPORT ==========
    'station': 'transport',
    'gare': 'transport',
    'bus_stop': 'transport',
    'arret de bus': 'transport',
    'airport': 'transport',
    'aeroport': 'transport',
    'aéroport': 'transport',
    'aerodrome': 'transport',
    'train': 'transport',
    'metro': 'transport',
    'métro': 'transport',
    'transport': 'transport',
    'terminal de ferry': 'transport',
    'ferry': 'transport',
    
    # ========== SECURITE ==========
    'police': 'travail',
    'poste de police': 'travail',
    'sécurité': 'travail',
    'securite': 'travail',
}

PURPOSE_ICONS = {
    'domicile': '🏠',
    'travail': '💼',
    'courses': '🛒',
    'loisirs': '🎭',
    'sante': '🏥',
    'education': '📚',
    'transport': '🚉',
    'autre': '❓'
}


def classify_purpose(poi_types, zone_types):
    """
    Classify the trip purpose based on POI and zone types found near the point.
    Returns the most likely purpose.
    """
    all_types = [t.lower() for t in (poi_types + zone_types) if t]
    
    purpose_counts = {}
    for type_name in all_types:
        for key, purpose in PURPOSE_MAPPING.items():
            if key in type_name:
                purpose_counts[purpose] = purpose_counts.get(purpose, 0) + 1
                break
    
    if purpose_counts:
        return max(purpose_counts, key=purpose_counts.get)
    
    return 'autre'


def find_nearby_features(cursor, lat, lon, radius_m=500):
    """
    Find POIs and zones near a given point.
    Returns dict with nearest_pois and containing_zones.
    """
    results = {
        'nearest_pois': [],
        'containing_zones': [],
        'nearest_poi_name': None,
        'nearest_poi_type': None,
        'nearest_poi_distance': None,
        'zone_name': None,
        'zone_type': None
    }
    
    poi_query = f"""
    SELECT nom, type, subtype, 
           ST_Distance(
               position::geography, 
               ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
           ) as distance_m
    FROM poi
    WHERE ST_DWithin(
        position::geography, 
        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 
        %s
    )
    ORDER BY distance_m
    LIMIT 5
    """
    
    try:
        cursor.execute(poi_query, (lon, lat, lon, lat, radius_m))
        pois = cursor.fetchall()
        
        for poi in pois:
            results['nearest_pois'].append({
                'name': poi[0],
                'type': poi[1],
                'subtype': poi[2],
                'distance_m': round(poi[3], 1)
            })
        
        if pois:
            results['nearest_poi_name'] = pois[0][0]
            results['nearest_poi_type'] = pois[0][1]
            results['nearest_poi_distance'] = round(pois[0][3], 1)
    except Exception as e:
        print(f"Error finding POIs: {e}")
    
    zone_query = """
    SELECT nom, type, subtype
    FROM zone
    WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
    LIMIT 3
    """
    
    try:
        cursor.execute(zone_query, (lon, lat))
        zones = cursor.fetchall()
        
        for zone in zones:
            results['containing_zones'].append({
                'name': zone[0],
                'type': zone[1],
                'subtype': zone[2]
            })
        
        if zones:
            results['zone_name'] = zones[0][0]
            results['zone_type'] = zones[0][1]
    except Exception as e:
        print(f"Error finding zones: {e}")
    
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to config JSON file")
    parser.add_argument("--job-id", required=False, help="Job identifier")
    args, _ = parser.parse_known_args()

    with open(args.input, "r") as f:
        config = json.load(f)

    trajectory_ids = config.get("trajectory_ids", [])
    radius_m = config.get("radius_m", 500)
    job_uuid = config.get("job_uuid", args.job_id)

    if not trajectory_ids:
        print("No trajectory IDs provided")
        return

    print(f"Processing {len(trajectory_ids)} trajectories with {radius_m}m search radius...")

    spark = SparkSession.builder \
        .appName("TripPurposeGuesser") \
        .getOrCreate()

    jdbc_url = "jdbc:postgresql://db:5432/mobility"
    jdbc_properties = {
        "user": os.environ.get("POSTGRES_USER", "user"),
        "password": os.environ.get("POSTGRES_PASSWORD", "password"),
        "driver": "org.postgresql.Driver"
    }

    ids_str = ", ".join([f"'{tid}'" for tid in trajectory_ids])
    query = f"""
    (SELECT trajectory_id, latitude, longitude, timestamp 
     FROM trajectory_gnss 
     WHERE trajectory_id IN ({ids_str}) 
     ORDER BY trajectory_id, timestamp) as traj
    """

    df = spark.read.jdbc(url=jdbc_url, table=query, properties=jdbc_properties)
    print(f"Loaded {df.count()} points from database")

    from pyspark.sql.window import Window
    from pyspark.sql.functions import row_number, desc

    window_asc = Window.partitionBy("trajectory_id").orderBy("timestamp")
    window_desc = Window.partitionBy("trajectory_id").orderBy(desc("timestamp"))

    df_with_row = df.withColumn("row_asc", row_number().over(window_asc)) \
                    .withColumn("row_desc", row_number().over(window_desc))

    first_points = df_with_row.filter(col("row_asc") == 1) \
        .select("trajectory_id", 
                col("latitude").alias("dep_lat"), 
                col("longitude").alias("dep_lon"),
                col("timestamp").alias("dep_time"))

    last_points = df_with_row.filter(col("row_desc") == 1) \
        .select("trajectory_id",
                col("latitude").alias("arr_lat"),
                col("longitude").alias("arr_lon"),
                col("timestamp").alias("arr_time"))

    endpoints = first_points.join(last_points, "trajectory_id")
    endpoints_data = endpoints.collect()

    print(f"Found {len(endpoints_data)} trajectories with endpoints")

    import psycopg2
    
    conn = psycopg2.connect(
        host="db",
        port=5432,
        database="mobility",
        user=os.environ.get("POSTGRES_USER", "user"),
        password=os.environ.get("POSTGRES_PASSWORD", "password")
    )
    cursor = conn.cursor()

    results = []
    for row in endpoints_data:
        traj_id = row["trajectory_id"]
        dep_lat = float(row["dep_lat"])
        dep_lon = float(row["dep_lon"])
        dep_time = str(row["dep_time"]) if row["dep_time"] else None
        arr_lat = float(row["arr_lat"])
        arr_lon = float(row["arr_lon"])
        arr_time = str(row["arr_time"]) if row["arr_time"] else None

        print(f"\nProcessing {traj_id}:")
        print(f"  Departure: ({dep_lat:.5f}, {dep_lon:.5f}) at {dep_time}")
        print(f"  Arrival: ({arr_lat:.5f}, {arr_lon:.5f}) at {arr_time}")

        dep_features = find_nearby_features(cursor, dep_lat, dep_lon, radius_m)
        print(f"  Departure POIs: {len(dep_features['nearest_pois'])}, Zones: {len(dep_features['containing_zones'])}")

        arr_features = find_nearby_features(cursor, arr_lat, arr_lon, radius_m)
        print(f"  Arrival POIs: {len(arr_features['nearest_pois'])}, Zones: {len(arr_features['containing_zones'])}")

        dep_poi_types = [p['type'] for p in dep_features['nearest_pois']] + \
                        [p['subtype'] for p in dep_features['nearest_pois']]
        dep_zone_types = [z['type'] for z in dep_features['containing_zones']] + \
                         [z['subtype'] for z in dep_features['containing_zones']]
        dep_purpose = classify_purpose(dep_poi_types, dep_zone_types)

        arr_poi_types = [p['type'] for p in arr_features['nearest_pois']] + \
                        [p['subtype'] for p in arr_features['nearest_pois']]
        arr_zone_types = [z['type'] for z in arr_features['containing_zones']] + \
                         [z['subtype'] for z in arr_features['containing_zones']]
        arr_purpose = classify_purpose(arr_poi_types, arr_zone_types)

        trip_purpose = arr_purpose
        trip_purpose_icon = PURPOSE_ICONS.get(trip_purpose, '❓')

        trip_description = f"{PURPOSE_ICONS.get(dep_purpose, '❓')} → {trip_purpose_icon}"
        if dep_purpose != 'autre' and arr_purpose != 'autre':
            if dep_purpose == 'domicile' and arr_purpose == 'travail':
                trip_description = "🏠 → 💼 Aller au travail"
            elif dep_purpose == 'travail' and arr_purpose == 'domicile':
                trip_description = "💼 → 🏠 Retour à la maison"
            elif arr_purpose == 'courses':
                trip_description = f"{PURPOSE_ICONS.get(dep_purpose, '❓')} → 🛒 Faire des courses"
            elif arr_purpose == 'loisirs':
                trip_description = f"{PURPOSE_ICONS.get(dep_purpose, '❓')} → 🎭 Sortie loisirs"

        result = {
            "trajectory_id": traj_id,
            "departure": {
                "lat": round(dep_lat, 6),
                "lon": round(dep_lon, 6),
                "time": dep_time,
                "nearest_poi": dep_features['nearest_poi_name'],
                "poi_type": dep_features['nearest_poi_type'],
                "poi_distance_m": dep_features['nearest_poi_distance'],
                "zone": dep_features['zone_name'],
                "zone_type": dep_features['zone_type'],
                "purpose": dep_purpose,
                "purpose_icon": PURPOSE_ICONS.get(dep_purpose, '❓')
            },
            "arrival": {
                "lat": round(arr_lat, 6),
                "lon": round(arr_lon, 6),
                "time": arr_time,
                "nearest_poi": arr_features['nearest_poi_name'],
                "poi_type": arr_features['nearest_poi_type'],
                "poi_distance_m": arr_features['nearest_poi_distance'],
                "zone": arr_features['zone_name'],
                "zone_type": arr_features['zone_type'],
                "purpose": arr_purpose,
                "purpose_icon": PURPOSE_ICONS.get(arr_purpose, '❓')
            },
            "trip_purpose": trip_purpose,
            "trip_purpose_icon": trip_purpose_icon,
            "trip_description": trip_description
        }
        results.append(result)
        print(f"  Trip: {trip_description}")

    cursor.close()
    conn.close()

    output_dir = "/opt/spark/data/results"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"trip_purpose_{job_uuid}.json")

    with open(output_file, "w") as f:
        json.dump({
            "job_id": job_uuid,
            "status": "completed",
            "results": results
        }, f, indent=2)

    print(f"\nResults saved to {output_file}")

    try:
        redis_client = redis.Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=0
        )
        redis_client.set(
            f"trip_purpose:{job_uuid}",
            json.dumps({
                "status": "completed",
                "results": results
            }),
            ex=3600
        )
        print("Results published to Redis")
    except Exception as e:
        print(f"Warning: Could not publish to Redis: {e}")

    spark.stop()
    print("Job completed successfully!")


if __name__ == "__main__":
    main()
