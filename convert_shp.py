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
    client = MongoClient(uri, server_api=ServerApi('1')) # Create a new client and connect to the server
    db = client['ramen-taiwan']
    collection = db['parking_info']
    collection.create_index([("geometry", "2dsphere")])
except Exception as e:
    logging.error(f"Cannot connect to MongoDB!{e}")


# enable OGR exceptions as official recommend
ogr.UseExceptions()

# initialize the transformer for TWD97 to WGS84 conversion
transformer = Transformer.from_crs("EPSG:3826", "EPSG:4326")

try:
    driver = ogr.GetDriverByName('ESRI Shapefile')
    # file download from https://data.gov.tw/dataset/128290
    shapefile = driver.Open('')
    if shapefile is None:
        raise ValueError("Could not open the input shapefile.")
    layer = shapefile.GetLayer()

    features = []

    for feature in layer:
        # convert layer feature's geometry as JSON to read
        geometry = json.loads(feature.GetGeometryRef().ExportToJson())

        # transform the coordinates
        if geometry['type'] == 'MultiPoint':
            new_coords = []
            for coords in geometry['coordinates']:
                x, y = coords
                lat, lon = transformer.transform(x, y)
                new_coords.append([lon, lat])
            geometry['coordinates'] = new_coords

        # get the feature's attributes (other info)
        properties = {}
        for i in range(feature.GetFieldCount()):
            properties[feature.GetFieldDefnRef(i).GetName()] = feature.GetField(i)

        # create a GeoJSON feature
        geojson_feature = {
            'type': 'parking_lot',
            'geometry': geometry,
            'properties': properties
        }

        # append to list for bulk insertion
        features.append(geojson_feature)

    # bulk insert into MongoDB
    if features:
        try:
            collection.insert_many(features)
            logging.info(f"Inserted {len(features)} parking features into MongoDB.")
        except Exception as e:
            logging.error(f"Insert error: {e}")

except Exception as e:
    logging.error(f"An error occurred: {e}")

finally:
    if shapefile is not None:
        shapefile = None
    client.close()
    logging.error("MongoDB connection closed.")
