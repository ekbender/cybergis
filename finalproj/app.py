# app.py
import streamlit as st
import geopandas as gpd
import pandas as pd
import osmnx as ox
import folium
from shapely.geometry import Point
from streamlit_folium import st_folium

# Sidebar: User Input
st.sidebar.header("CyberGIS Dashboard")

# 1. Select Place
place = st.sidebar.text_input("Enter place (e.g. 'Berkeley, California, USA')", "Berkeley, California, USA")

# 2. Select Feature Type
feature_type = st.sidebar.selectbox("Select feature type", ['school', 'hospital', 'park'])

# 3. Number of user points
num_users = st.sidebar.slider("Number of random user points", 5, 50, 10)

# 4. Buffer radius
user_buffer = st.sidebar.slider("User buffer radius (m)", 50, 500, 150)
feature_buffer = st.sidebar.slider(f"{feature_type.capitalize()} buffer radius (m)", 100, 1000, 300)

st.title("🗺️ CyberGIS Interactive Dashboard")

# -- Get Features from OSM
with st.spinner("Loading OpenStreetMap data..."):
    tags = {'amenity': feature_type} if feature_type != 'park' else {'leisure': 'park'}
    features = ox.features_from_place(place, tags=tags)
    features = features.to_crs(epsg=3857)

# -- Generate Random Users
import numpy as np
np.random.seed(42)
bounds = features.total_bounds  # [minx, miny, maxx, maxy]
xs = np.random.uniform(bounds[0], bounds[2], num_users)
ys = np.random.uniform(bounds[1], bounds[3], num_users)
user_points = gpd.GeoDataFrame({
    'name': [f'User{i}' for i in range(num_users)],
    'geometry': [Point(x, y) for x, y in zip(xs, ys)]
}, crs='EPSG:3857')

# -- Buffer zones
features['buffer'] = features.geometry.buffer(feature_buffer)
user_points['buffer'] = user_points.geometry.buffer(user_buffer)

# -- Nearest Feature Analysis
user_points['nearest_feature'] = user_points.geometry.apply(
    lambda user_geom: features.distance(user_geom).sort_values().index[0]
)
user_points['distance_m'] = user_points.apply(
    lambda row: row.geometry.distance(features.loc[row['nearest_feature']].geometry), axis=1
)

# -- Map with Folium
m = folium.Map(location=[features.to_crs(epsg=4326).geometry.centroid.y.mean(),
                         features.to_crs(epsg=4326).geometry.centroid.x.mean()],
               zoom_start=14, tiles="CartoDB Positron")

# Plot Features
for _, row in features.to_crs(4326).iterrows():
    folium.CircleMarker(location=[row.geometry.centroid.y, row.geometry.centroid.x],
                        radius=6, color='green', fill=True,
                        popup=f"{feature_type.capitalize()}").add_to(m)

# Plot Users
for _, row in user_points.to_crs(4326).iterrows():
    folium.CircleMarker(location=[row.geometry.y, row.geometry.x],
                        radius=4, color='blue', fill=True,
                        popup=f"{row['name']}<br>Distance: {int(row['distance_m'])} m").add_to(m)

# Show Map
st.subheader("Map Visualization")
st_folium(m, width=800, height=600)

# Data Table
if st.checkbox("Show raw user data"):
    st.write(user_points[['name', 'distance_m']])
