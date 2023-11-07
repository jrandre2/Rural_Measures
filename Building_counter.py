import geopandas as gpd
import shapely.geometry as sg
import geopy.distance as gd
import pandas as pd
import pyproj
import os
import pyproj.datadir
from geopy.distance import geodesic as distance

pyproj.datadir.set_data_dir("/Users/jesseandrews/Documents/Code")

# read JSON file 
buildings = gpd.read_file("/Users/jesseandrews/Documents/Code/Nebraska.geojson")

# read points from processed survey data CSV file
points = pd.read_csv("/Users/jesseandrews/Documents/Code/processed_data.csv", header=0)

# Loop through all points
for i, row in points.iterrows():
    point = sg.Point(row["LocationLongitude"], row["LocationLatitude"])

    # Create a buffer of 3 km around the current point
    buffer = point.buffer(3 / 111)  # Roughly 3 km in degrees

    # Use spatial index to find buildings that intersect the buffer
    possible_matches_index = list(buildings.sindex.intersection(buffer.bounds))
    possible_matches = buildings.iloc[possible_matches_index]
    precise_matches = possible_matches[possible_matches.intersects(buffer)]

    # Now, `precise_matches` is a subset of buildings that are within 3 km of current point
    # Calculate distances for this subset
    distances = [distance((point.y, point.x), (geom.centroid.y, geom.centroid.x)).km for geom in precise_matches.geometry]

    # Count structures for each point and each distance
    structures_250m = sum(d <= 0.25 for d in distances)  # Adding 250m distance count
    structures_500m = sum(d <= 0.5 for d in distances)  # Adding 500m distance count
    structures_1km = sum(d <= 1 for d in distances)
    structures_2km = sum(d <= 2 for d in distances)
    structures_3km = sum(d <= 3 for d in distances)

    # Append to results DataFrame
    points.loc[i, "structures_250m"] = structures_250m
    points.loc[i, "structures_500m"] = structures_500m
    points.loc[i, "structures_1km"] = structures_1km
    points.loc[i, "structures_2km"] = structures_2km
    points.loc[i, "structures_3km"] = structures_3km

# Save to same CSV file
points.to_csv('/Users/jesseandrews/Documents/Code/processed_data.csv', index=False)
