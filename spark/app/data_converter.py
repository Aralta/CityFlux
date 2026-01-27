# data_converter.py
"""
Spark data conversion script with OSRM routing for OD data.
Supports three data types:
- gnss: direct load to trajectory_gnss
- telecom: antenna projection to GNSS
- od: route along real roads using OSRM and interpolate points every 15 minutes.
"""

import argparse
import json
import sys
import requests
from datetime import datetime, timedelta

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lit, current_timestamp, concat_ws, expr
from pyspark.sql.types import (
    StringType,
    DoubleType,
    TimestampType,
)

# Shapely for geometry interpolation
from shapely.geometry import LineString

# ------------------- Helper Functions -------------------

def get_osrm_route(origin_lat, origin_lon, dest_lat, dest_lon):
    """Call the public OSRM demo server to retrieve a route.
    Returns a list of (lon, lat) tuples representing the route geometry.
    """
    url = (
        f"http://router.project-osrm.org/route/v1/driving/"
        f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}?geometries=geojson&overview=full"
    )
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data.get("code") != "Ok":
            raise ValueError(f"OSRM error: {data.get('message')}")
        coords = data["routes"][0]["geometry"]["coordinates"]  # list of [lon, lat]
        return [(lon, lat) for lon, lat in coords]
    except Exception as e:
        print(f"[OSRM] Failed to get route: {e}")
        return []


def interpolate_route(coords, interval_minutes=15, start_time=None):
    """Given a list of (lon, lat) coordinates, interpolate points every `interval_minutes`.
    Returns a list of dicts with latitude, longitude, timestamp.
    """
    if not coords:
        return []
    line = LineString(coords)
    length = line.length  # in degrees (approx), we'll use proportion for time.
    # Estimate travel time: assume average speed 50 km/h (~0.5 degree per hour approx).
    # For simplicity, we use number of points = max(2, int(total_minutes / interval_minutes)).
    # Compute total minutes based on length * factor (rough). Here we just use number of segments.
    total_minutes = max(15, int(len(coords) * interval_minutes))
    points = []
    num_steps = max(2, int(total_minutes / interval_minutes) + 1)
    for i in range(num_steps):
        fraction = i / (num_steps - 1)
        lon, lat = line.interpolate(fraction, normalized=True).coords[0]
        ts = (
            start_time + timedelta(minutes=i * interval_minutes)
            if start_time
            else datetime.utcnow()
        )
        points.append({"latitude": lat, "longitude": lon, "timestamp": ts})
    return points

# ------------------- Main -------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to config JSON file")
    parser.add_argument("--job-id", required=False, help="Job identifier")
    args, _ = parser.parse_known_args()

    # Load configuration JSON produced by Django/Celery
    with open(args.input, "r") as f:
        config = json.load(f)

    input_file = config["input_file"]
    data_type = config["data_type"]
    action = config["action"]
    job_uuid = config.get("job_uuid", args.job_id)

    spark = SparkSession.builder.appName("DataConverter").getOrCreate()
    df = spark.read.option("header", "true").csv(input_file)
    df.printSchema()
    print(f"Rows detected: {df.count()}")

    final_df = None

    if data_type == "gnss":
        final_df = df.select(
            col("user_id").cast(StringType()),
            col("timestamp").cast(TimestampType()),
            col("latitude").cast(DoubleType()),
            col("longitude").cast(DoubleType()),
            lit(0.0).alias("speed"),
            col("trajectory_id").cast(StringType()),
        )
    elif data_type == "telecom":
        final_df = df.select(
            col("user_id").cast(StringType()),
            col("timestamp").cast(TimestampType()),
            col("antenna_lat").alias("latitude").cast(DoubleType()),
            col("antenna_lon").alias("longitude").cast(DoubleType()),
            lit(0.0).alias("speed"),
            col("antenna_id").alias("trajectory_id").cast(StringType()),
        )
    elif data_type == "od":
        # Expect columns: origin_lat, origin_lon, dest_lat, dest_lon, origin_zone, dest_zone, count, time_slot
        rows = []
        od_rows = df.collect()
        for r in od_rows:
            try:
                origin_lat = float(r["origin_lat"])
                origin_lon = float(r["origin_lon"])
                dest_lat = float(r["dest_lat"])
                dest_lon = float(r["dest_lon"])
                start_time = datetime.utcnow()
                route_coords = get_osrm_route(origin_lat, origin_lon, dest_lat, dest_lon)
                points = interpolate_route(
                    route_coords, interval_minutes=15, start_time=start_time
                )
                for p in points:
                    rows.append(
                        (
                            "od_user",
                            p["timestamp"],
                            p["latitude"],
                            p["longitude"],
                            10.0,
                            f"{r['origin_zone']}_{r['dest_zone']}",
                        )
                    )
            except Exception as e:
                print(f"[OD] Failed processing row: {e}")
        # Create DataFrame from generated rows
        schema = (
            "user_id STRING, timestamp TIMESTAMP, latitude DOUBLE, longitude DOUBLE, speed DOUBLE, trajectory_id STRING"
        )
        final_df = spark.createDataFrame(rows, schema=schema)
    else:
        print(f"Unsupported data_type: {data_type}")
        sys.exit(1)

    if final_df is None:
        print("No data to write.")
        sys.exit(1)

    # Write to PostgreSQL (same as before)
    jdbc_url = "jdbc:postgresql://db:5432/mobility"
    jdbc_properties = {
        "user": "user",
        "password": "password",
        "driver": "org.postgresql.Driver",
    }
    table_name = "trajectory_gnss"
    final_df.write.mode("append").jdbc(url=jdbc_url, table=table_name, properties=jdbc_properties)
    print("Data inserted successfully.")

if __name__ == "__main__":
    main()
