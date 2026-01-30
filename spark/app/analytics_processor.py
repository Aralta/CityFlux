"""
Spark script to compute analytics statistics on mobility data.
Calculates:
- POI distribution by type/subtype
- Zone distribution by category
- Maximum distance trajectory
- Maximum speed recorded
- Central point (centroid) of all data
- Total counts (trajectories, POI, zones)
- Temporal coverage
"""

import os
import sys
import json
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, avg, max as spark_max, min as spark_min, count, sum as spark_sum,
    unix_timestamp, sqrt, radians, sin, cos, atan2, first, last, lag,
    collect_list, struct, lit
)
from pyspark.sql.window import Window
from pyspark.sql.types import DoubleType


# Database configuration
DB_HOST = os.getenv('POSTGRES_HOST', 'db')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'mobiflux')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'postgres')


def get_jdbc_url():
    """Get JDBC connection URL."""
    return f"jdbc:postgresql://{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_jdbc_properties():
    """Get JDBC connection properties."""
    return {
        "user": DB_USER,
        "password": DB_PASSWORD,
        "driver": "org.postgresql.Driver"
    }


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate great circle distance between two points.
    Returns distance in kilometers.
    """
    R = 6371  # Earth radius in km
    
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c


def compute_trajectory_stats(spark, jdbc_url, jdbc_props):
    """Compute statistics for trajectories."""
    trajectories_df = spark.read.jdbc(
        jdbc_url, 
        "(SELECT trajectory_id, latitude, longitude, timestamp, speed FROM trajectory_gnss) as t",
        properties=jdbc_props
    )
    
    if trajectories_df.count() == 0:
        return {
            "total_trajectories": 0,
            "max_distance_km": 0,
            "max_speed_kmh": 0,
            "longest_trajectory_id": None,
            "avg_speed_kmh": 0,
            "total_points": 0,
            "time_range": {"start": None, "end": None}
        }
    
    total_trajectories = trajectories_df.select("trajectory_id").distinct().count()
    total_points = trajectories_df.count()
    
    max_speed = trajectories_df.agg(spark_max("speed")).collect()[0][0] or 0
    avg_speed = trajectories_df.agg(avg("speed")).collect()[0][0] or 0
    
    time_stats = trajectories_df.agg(
        spark_min("timestamp").alias("min_time"),
        spark_max("timestamp").alias("max_time")
    ).collect()[0]
    
    window_spec = Window.partitionBy("trajectory_id").orderBy("timestamp")
    
    trajectories_with_prev = trajectories_df.withColumn(
        "prev_lat", lag("latitude").over(window_spec)
    ).withColumn(
        "prev_lon", lag("longitude").over(window_spec)
    )
    
    trajectories_with_prev = trajectories_with_prev.filter(
        col("prev_lat").isNotNull()
    )
    
    trajectories_with_dist = trajectories_with_prev.withColumn(
        "segment_distance",
        haversine_distance(
            col("prev_lat"), col("prev_lon"),
            col("latitude"), col("longitude")
        )
    )
    
    distance_per_traj = trajectories_with_dist.groupBy("trajectory_id").agg(
        spark_sum("segment_distance").alias("total_distance")
    )
    
    longest = distance_per_traj.orderBy(col("total_distance").desc()).first()
    
    return {
        "total_trajectories": total_trajectories,
        "total_points": total_points,
        "max_distance_km": round(longest["total_distance"], 2) if longest else 0,
        "longest_trajectory_id": longest["trajectory_id"] if longest else None,
        "max_speed_kmh": round(max_speed, 2),
        "avg_speed_kmh": round(avg_speed, 2),
        "time_range": {
            "start": str(time_stats["min_time"]) if time_stats["min_time"] else None,
            "end": str(time_stats["max_time"]) if time_stats["max_time"] else None
        }
    }


def compute_poi_stats(spark, jdbc_url, jdbc_props):
    """Compute POI distribution statistics."""
    poi_df = spark.read.jdbc(
        jdbc_url,
        "(SELECT id, type, subtype, ST_X(position::geometry) as lon, ST_Y(position::geometry) as lat FROM poi) as p",
        properties=jdbc_props
    )
    
    total_pois = poi_df.count()
    
    if total_pois == 0:
        return {
            "total_pois": 0,
            "distribution_by_type": [],
            "centroid": {"lat": None, "lon": None}
        }
    
    type_counts = poi_df.groupBy("type").agg(
        count("*").alias("count")
    ).collect()
    
    distribution = []
    for row in type_counts:
        distribution.append({
            "type": row["type"] or "unknown",
            "count": row["count"],
            "percentage": round((row["count"] / total_pois) * 100, 1)
        })
    
    distribution.sort(key=lambda x: x["count"], reverse=True)
    
    centroid = poi_df.agg(
        avg("lat").alias("avg_lat"),
        avg("lon").alias("avg_lon")
    ).collect()[0]
    
    return {
        "total_pois": total_pois,
        "distribution_by_type": distribution,
        "centroid": {
            "lat": round(centroid["avg_lat"], 6) if centroid["avg_lat"] else None,
            "lon": round(centroid["avg_lon"], 6) if centroid["avg_lon"] else None
        }
    }


def compute_zone_stats(spark, jdbc_url, jdbc_props):
    """Compute zone distribution statistics."""
    zone_df = spark.read.jdbc(
        jdbc_url,
        "(SELECT id, type, subtype, ST_X(ST_Centroid(geom::geometry)) as lon, ST_Y(ST_Centroid(geom::geometry)) as lat FROM zone) as z",
        properties=jdbc_props
    )
    
    total_zones = zone_df.count()
    
    if total_zones == 0:
        return {
            "total_zones": 0,
            "distribution_by_type": [],
            "centroid": {"lat": None, "lon": None}
        }
    
    type_counts = zone_df.filter(~col("type").isin(["autre", "autres", "Autre", "Autres", "other", "Other"])).groupBy("type").agg(
        count("*").alias("count")
    ).collect()
    
    total_without_autres = sum(row["count"] for row in type_counts)
    
    distribution = []
    for row in type_counts:
        distribution.append({
            "type": row["type"] or "unknown",
            "count": row["count"],
            "percentage": round((row["count"] / total_without_autres) * 100, 1) if total_without_autres > 0 else 0
        })
    
    distribution.sort(key=lambda x: x["count"], reverse=True)
    
    centroid = zone_df.agg(
        avg("lat").alias("avg_lat"),
        avg("lon").alias("avg_lon")
    ).collect()[0]
    
    return {
        "total_zones": total_zones,
        "distribution_by_type": distribution,
        "centroid": {
            "lat": round(centroid["avg_lat"], 6) if centroid["avg_lat"] else None,
            "lon": round(centroid["avg_lon"], 6) if centroid["avg_lon"] else None
        }
    }


def compute_transport_stats(spark, jdbc_url, jdbc_props):
    """Compute transport network statistics."""
    stops_df = spark.read.jdbc(jdbc_url, "arret", properties=jdbc_props)
    total_stops = stops_df.count()
    
    lines_df = spark.read.jdbc(jdbc_url, "ligne", properties=jdbc_props)
    total_lines = lines_df.count()
    
    types_df = spark.read.jdbc(jdbc_url, "type_transport", properties=jdbc_props)
    transport_types = [row["nom"] for row in types_df.collect()]
    
    return {
        "total_stops": total_stops,
        "total_lines": total_lines,
        "transport_types": transport_types
    }


def main():
    """Main entry point."""
    print("=" * 50)
    print("Analytics Processor - Starting")
    print("=" * 50)
    
    import argparse
    parser = argparse.ArgumentParser(description='Analytics Processor')
    parser.add_argument('--input', '-i', type=str, help='Input JSON file path')
    parser.add_argument('--job-id', type=str, help='Job ID')
    args, unknown = parser.parse_known_args()
    
    input_file = args.input
    job_uuid = args.job_id or "manual"
    
    if input_file and os.path.exists(input_file):
        print(f"Input file: {input_file}")
        with open(input_file, 'r') as f:
            job_data = json.load(f)
        job_uuid = job_data.get("job_uuid", job_uuid)
    else:
        print("No input file specified or file not found, using default analysis")
    
    print(f"Job UUID: {job_uuid}")
    
    spark = SparkSession.builder \
        .appName(f"Analytics-{job_uuid}") \
        .config("spark.jars", "/opt/spark/jars/postgresql-42.7.4.jar") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    
    jdbc_url = get_jdbc_url()
    jdbc_props = get_jdbc_properties()
    
    print("Computing trajectory statistics...")
    trajectory_stats = compute_trajectory_stats(spark, jdbc_url, jdbc_props)
    
    print("Computing POI statistics...")
    poi_stats = compute_poi_stats(spark, jdbc_url, jdbc_props)
    
    print("Computing zone statistics...")
    zone_stats = compute_zone_stats(spark, jdbc_url, jdbc_props)
    
    print("Computing transport statistics...")
    transport_stats = compute_transport_stats(spark, jdbc_url, jdbc_props)
    
    centroids = []
    if poi_stats["centroid"]["lat"]:
        centroids.append((poi_stats["centroid"]["lat"], poi_stats["centroid"]["lon"]))
    if zone_stats["centroid"]["lat"]:
        centroids.append((zone_stats["centroid"]["lat"], zone_stats["centroid"]["lon"]))
    
    if centroids:
        global_centroid = {
            "lat": round(sum(c[0] for c in centroids) / len(centroids), 6),
            "lon": round(sum(c[1] for c in centroids) / len(centroids), 6)
        }
    else:
        global_centroid = {"lat": 43.5297, "lon": 5.4474} 
    
    result = {
        "status": "completed",
        "job_uuid": job_uuid,
        "trajectories": trajectory_stats,
        "pois": poi_stats,
        "zones": zone_stats,
        "transport": transport_stats,
        "global_centroid": global_centroid
    }
    
    # Save result
    results_dir = "/opt/spark/data/results"
    os.makedirs(results_dir, exist_ok=True)
    
    result_file = os.path.join(results_dir, f"analytics_{job_uuid}.json")
    with open(result_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Results saved to: {result_file}")
    print("=" * 50)
    print("Analytics completed successfully!")
    print("=" * 50)
    
    spark.stop()


if __name__ == "__main__":
    main()
