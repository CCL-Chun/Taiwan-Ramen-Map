from osgeo import ogr
from pyproj import Transformer
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import logging
import json
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_convert_shp.txt',filemode='a',
    format='%(asctime)s %(filename)s %(levelname)s:%(message)s')

## connect to cloud MongoDB
try:
    load_dotenv()
    username = os.getenv("MongoDB_user")
    password = os.getenv("MongoDB_password")
    cluster_url = os.getenv("MongoDB_cluster_url")
    uri = f"mongodb+srv://{username}:{password}@{cluster_url}?retryWrites=true&w=majority&appName=ramen-taiwan"
    client = MongoClient(uri, server_api=ServerApi('1')) # create a new client and connect to the server
    db = client['ramen-taiwan']
    collection = db['parking_info']
    collection.create_index([("geometry", "2dsphere")])
except Exception as e:
    logging.error(f"Cannot connect to MongoDB!{e}")


# enable OGR exceptions as official recommend
ogr.UseExceptions()

# initialize the transformer for TWD97 to WGS84 conversion
transformer = Transformer.from_crs("EPSG:3826", "EPSG:4326")

# batch insert for RAM management
# batch size 3000 need 9 mins on Mac M1
batch_size = 3000

try:
    driver = ogr.GetDriverByName('ESRI Shapefile')
    # file download from https://data.gov.tw/dataset/128290 and https://data.gov.tw/dataset/128288
    shapefile = driver.Open('')
    if shapefile is None:
        raise ValueError("Could not open the input shapefile.")
    layer = shapefile.GetLayer()

    features = []
    loop_counter = 0

    # Geodetic transformer loop through data
    for feature in layer:
        # convert layer feature's geometry as JSON to read
        geometry = json.loads(feature.GetGeometryRef().ExportToJson())

        # transform the coordinates
        # handle Point location
        if geometry['type'] == 'MultiPoint':
            geometry['type'] = "Point"
            for coords in geometry['coordinates']:
                x, y = coords
                lat, lon = transformer.transform(x, y)
                new_coords = [lon, lat]
            geometry['coordinates'] = new_coords

        # handle Polygon location
        if geometry['type'] == 'Polygon':
            new_polygon = []
            new_polygon.append([])
            for polygon in geometry['coordinates']:
                for coords in polygon:
                    x, y = coords
                    lat, lon = transformer.transform(x, y)
                    new_polygon[0].append([lon, lat])
            geometry['coordinates'] = new_polygon

        # handle MultiPolygon location
        if geometry['type'] == 'MultiPolygon':
            new_multipolygon = []
            for multipolygon in geometry['coordinates']:
                new_polygon = []
                new_polygon.append([])
                for polygon in multipolygon:
                    for coords in polygon:
                        x, y = coords
                        lat, lon = transformer.transform(x, y)
                        new_polygon[0].append([lon, lat])
                new_multipolygon.append(new_polygon)
            geometry['coordinates'] = new_multipolygon

        # get the feature's attributes (other info)
        properties = {}
        for i in range(feature.GetFieldCount()):
            properties[feature.GetFieldDefnRef(i).GetName()] = feature.GetField(i)

        # create a GeoJSON feature
        geojson_feature = {
            'type': 'Feature', # must be Feature here for GeoJSON
            'geometry': geometry,
            'properties': properties
        }

        # append to list for bulk insertion
        features.append(geojson_feature)
        loop_counter += 1

        if loop_counter % batch_size == 0:
            try:
                collection.insert_many(features)
                logging.info(f"Inserted {len(features)} parking features into MongoDB. Total {loop_counter} features")
                features = []
            except Exception as e:
                logging.error(f"Insert error: {e}")

    # final check bulk insert into MongoDB
    if features:
        try:
            collection.insert_many(features)
            logging.info(f"Inserted {len(features)} parking features into MongoDB. Total {loop_counter} features")
        except Exception as e:
            logging.error(f"Insert error: {e}")

except Exception as e:
    logging.error(f"An error occurred: {e}")

finally:
    if shapefile is not None:
        shapefile = None
    client.close()
    logging.error("MongoDB connection closed.")
