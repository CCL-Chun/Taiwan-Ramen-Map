from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import logging
import pytz
import json
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_map.txt',filemode='a',
    format='%(asctime)s %(filename)s %(levelname)s:%(message)s')

timezone = pytz.timezone('Asia/Taipei')
weekDaysMapping = ("星期一", "星期二", 
                   "星期三", "星期四",
                   "星期五", "星期六",
                   "星期日")
def weekday():
    # will return 0 when Monday
    return datetime.weekday(datetime.now(pytz.utc).astimezone(timezone))


## connect to cloud MongoDB
try:
    load_dotenv()
    username = os.getenv("MongoDB_user")
    password = os.getenv("MongoDB_password")
    cluster_url = os.getenv("MongoDB_cluster_url")
    uri = f"mongodb+srv://{username}:{password}@{cluster_url}?retryWrites=true&w=majority&appName=ramen-taiwan"
    client = MongoClient(uri, server_api=ServerApi('1')) # Create a new client and connect to the server
    db = client['ramen-taiwan']
    collection_ramen = db['ramen_info']
    collection_parking = db['parking_info']

except Exception as e:
    logging.error(f"Cannot connect to MongoDB!{e}")

app = Flask(__name__)

@app.route("/")
def first_view():
    # find ramen records
    ramen_data = list(collection_ramen.find({}).limit(100))
    # initialize GeoJSON format
    ramen_geojson = {"type":"FeatrureCollection"} 
    # put data into features list
    ramen_geojson["features"] = [{
        "type": "Feature",
        "geometry": 
        {
            "type": "Point",
            "coordinates": [ramen["longitude"],ramen["latitude"]]
        },
        "properties": 
        {
            "name": ramen["name"],
            "address": ramen["address"],
            "weekday": weekDaysMapping[weekday()],
            "open": ramen["open_time"][weekDaysMapping[weekday()]],
            "overall": ramen["overall_rating"]["mean"]
        }
    } for ramen in ramen_data]

    print(len(ramen_geojson))

    return render_template('leaflet_map.html',ramen_geojson = ramen_geojson)


@app.route("/get_parking")
def mapview():
    # find parking lot records
    parking_lots = list(collection_parking.find().limit(10000))
    # initialize GeoJSON format
    parking_data = {"type":"FeatrureCollection"} 
    # put data into features list
    parking_data["features"] = [{
        "type": "Feature",
        "geometry": lot['geometry'],
        "properties": lot["properties"]
    } for lot in parking_lots]
    print(len(parking_lots))

    # print(parking_data[1:3])

    return render_template('leaflet_map.html',parking_data = parking_data)


if __name__ == "__main__":
    app.run(debug=True,port=5000)
