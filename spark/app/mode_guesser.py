"""
Spark script to guess transportation mode from GNSS trajectory data.
Classification based on:
- Average speed
- Maximum speed
- Trip duration
- Distance traveled

Transport modes:
- Walking: avg_speed < 7 km/h, max_speed < 15 km/h
- Cycling: 7 <= avg_speed < 25 km/h, max_speed < 40 km/h
- Public Transport: 15 <= avg_speed < 50 km/h
- Car: avg_speed >= 25 km/h OR max_speed >= 50 km/h

Anomaly detection:
- Speed > 200 km/h (unrealistic for ground transport)
- Duration > 24 hours (likely synthetic or multi-day)
- Distance > 1000 km (unrealistic for single trip)
- Average speed inconsistent with distance/duration
"""

import argparse
import json
import os
import redis
import math

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, avg, max as spark_max, min as spark_min,
    unix_timestamp, lit, count, first, last, lag, sqrt, radians, sin, cos, atan2
)
from pyspark.sql.window import Window


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees).
    Returns distance in kilometers.
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 0.0
    
    R = 6371
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def detect_anomalies(avg_speed, max_speed, duration_minutes, distance_km):
    """
    Detect if the data seems synthetic or has anomalies.
    Returns a tuple: (list of detected anomalies, calculated_speed or None)
    """
    anomalies = []
    calculated_speed = None
    
    if max_speed > 200:
        anomalies.append("vitesse_max_irrealiste")
    
    if avg_speed > 150:
        anomalies.append("vitesse_moy_irrealiste")
    
    if duration_minutes > 1440:
        anomalies.append("duree_excessive")
    
    if distance_km > 1000:
        anomalies.append("distance_excessive")
    
    if duration_minutes > 0 and distance_km > 0:
        calculated_speed = distance_km / (duration_minutes / 60)
        
        if avg_speed > 0:
            relative_diff = abs(calculated_speed - avg_speed) / avg_speed
            if relative_diff > 0.5:
                anomalies.append("incoherence_vitesse_distance")
        elif calculated_speed > 5:
            anomalies.append("incoherence_vitesse_distance")
    
    if avg_speed < 0 or max_speed < 0 or duration_minutes < 0 or distance_km < 0:
        anomalies.append("valeurs_negatives")
    
    if duration_minutes == 0 and distance_km > 0:
        anomalies.append("duree_nulle")
    
    return anomalies, calculated_speed


def classify_transport_mode(avg_speed, max_speed, duration_minutes):
    """
    Classify the transport mode based on speed and duration metrics.
    Returns one of: 'walking', 'cycling', 'public_transport', 'car', 'unknown'
    """
    if avg_speed is None or max_speed is None:
        return 'unknown'
    
    if avg_speed < 7 and max_speed < 15:
        return 'walking'
    
    if 7 <= avg_speed < 25 and max_speed < 40:
        return 'cycling'
    
    if avg_speed >= 25 or max_speed >= 50:
        return 'car'
    
    if 15 <= avg_speed < 50:
        return 'public_transport'
    
    if avg_speed >= 7:
        return 'cycling'
    
    return 'unknown'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to config JSON file")
    parser.add_argument("--job-id", required=False, help="Job identifier")
    args, _ = parser.parse_known_args()

    with open(args.input, "r") as f:
        config = json.load(f)

    trajectory_ids = config.get("trajectory_ids", [])
    job_uuid = config.get("job_uuid", args.job_id)

    if not trajectory_ids:
        print("No trajectory IDs provided")
        return

    print(f"Processing {len(trajectory_ids)} trajectories...")

    spark = SparkSession.builder \
        .appName("TransportModeGuesser") \
        .getOrCreate()
    jdbc_url = "jdbc:postgresql://db:5432/mobility"
    jdbc_properties = {
        "user": os.environ.get("POSTGRES_USER", "user"),
        "password": os.environ.get("POSTGRES_PASSWORD", "password"),
        "driver": "org.postgresql.Driver"
    }

    ids_str = ", ".join([f"'{tid}'" for tid in trajectory_ids])
    query = f"(SELECT trajectory_id, speed, timestamp, latitude, longitude FROM trajectory_gnss WHERE trajectory_id IN ({ids_str}) ORDER BY trajectory_id, timestamp) as traj"

    df = spark.read.jdbc(url=jdbc_url, table=query, properties=jdbc_properties)
    
    print(f"Loaded {df.count()} points from database")
    df.printSchema()

    metrics_df = df.groupBy("trajectory_id").agg(
        avg("speed").alias("avg_speed"),
        spark_max("speed").alias("max_speed"),
        spark_min("timestamp").alias("start_time"),
        spark_max("timestamp").alias("end_time"),
        count("*").alias("point_count")
    )

    metrics_df = metrics_df.withColumn(
        "duration_minutes",
        (unix_timestamp(col("end_time")) - unix_timestamp(col("start_time"))) / 60.0
    )
    
    all_points = df.collect()
    
    trajectory_points = {}
    for row in all_points:
        traj_id = row["trajectory_id"]
        if traj_id not in trajectory_points:
            trajectory_points[traj_id] = []
        trajectory_points[traj_id].append({
            "lat": float(row["latitude"]) if row["latitude"] else None,
            "lon": float(row["longitude"]) if row["longitude"] else None,
            "timestamp": row["timestamp"]
        })
    
    trajectory_distances = {}
    for traj_id, points in trajectory_points.items():
        points.sort(key=lambda x: x["timestamp"] if x["timestamp"] else "")
        
        total_distance = 0.0
        for i in range(1, len(points)):
            prev = points[i-1]
            curr = points[i]
            if prev["lat"] and prev["lon"] and curr["lat"] and curr["lon"]:
                dist = haversine_distance(prev["lat"], prev["lon"], curr["lat"], curr["lon"])
                total_distance += dist
        
        trajectory_distances[traj_id] = total_distance

    results = []
    for row in metrics_df.collect():
        traj_id = row["trajectory_id"]
        avg_speed = float(row["avg_speed"]) if row["avg_speed"] else 0.0
        max_speed = float(row["max_speed"]) if row["max_speed"] else 0.0
        duration = float(row["duration_minutes"]) if row["duration_minutes"] else 0.0
        point_count = int(row["point_count"]) if row["point_count"] else 0
        distance_km = trajectory_distances.get(traj_id, 0.0)

        mode = classify_transport_mode(avg_speed, max_speed, duration)
        anomalies, calculated_speed = detect_anomalies(avg_speed, max_speed, duration, distance_km)
        is_synthetic = len(anomalies) > 0

        results.append({
            "trajectory_id": traj_id,
            "avg_speed": round(avg_speed, 2),
            "max_speed": round(max_speed, 2),
            "calculated_speed": round(calculated_speed, 2) if calculated_speed else None,
            "duration_minutes": round(duration, 2),
            "distance_km": round(distance_km, 2),
            "point_count": point_count,
            "guessed_mode": mode,
            "is_synthetic": is_synthetic,
            "anomalies": anomalies
        })
        
        calc_spd_str = f", calc={calculated_speed:.1f}km/h" if calculated_speed else ""
        anomaly_str = f" ⚠️ SYNTHETIC: {', '.join(anomalies)}" if is_synthetic else ""
        print(f"  {traj_id}: avg={avg_speed:.1f}km/h{calc_spd_str}, max={max_speed:.1f}km/h, dist={distance_km:.1f}km, dur={duration:.1f}min -> {mode}{anomaly_str}")

    output_dir = "/opt/spark/data/results"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"mode_guesser_{job_uuid}.json")

    with open(output_file, "w") as f:
        json.dump({
            "job_id": job_uuid,
            "status": "completed",
            "results": results
        }, f, indent=2)

    print(f"Results saved to {output_file}")

    try:
        redis_client = redis.Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            db=0
        )
        redis_client.set(
            f"mode_guesser:{job_uuid}",
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
