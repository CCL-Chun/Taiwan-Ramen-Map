from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime
import requests
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
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)


@app.route("/")
def first_view():
    return render_template('leaflet_map.html')

@app.route("/ramen/api/v1.0/restaurants", methods=["GET"])
def get_ramens():
    center_received = request.args.get('center')
    lng, lat = map(float, center_received.split(','))
    # find ramen records
    ramen_data = list(collection_ramen.find({
        "location":{
            "$geoWithin":{
                "$centerSphere":[
                        [lng, lat],
                        1.5 / 6378.1 # equatorial radius of Earth is approximately 6,378.1 kilometers
                ]
            }
        }
    }).limit(50))
    # initialize GeoJSON format
    ramen_geojson = {"type":"FeatrureCollection"}
    # put data into features list
    ramen_geojson["features"] = [{
        "type": "Feature",
        "geometry": ramen["location"],
        "properties":
        {
            "name": ramen["name"],
            "address": ramen["address"],
            "weekday": weekDaysMapping[weekday()],
            "open": ramen["open_time"][weekDaysMapping[weekday()]] if ramen["open_time"] else "不定",
            "overall": ramen["overall_rating"]["mean"]
        }
    } for ramen in ramen_data]

    print(len(ramen_data))

    return jsonify(ramen_geojson)


@app.route("/traffic/api/v1.0/parking", methods=["GET"])
def get_parking():
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    # find parking lot records
    parking_lots = list(collection_parking.find({
        "geometry":{
            "$geoWithin":{
                "$centerSphere":[
                        [lng, lat],
                        0.8 / 6378.1 # equatorial radius of Earth is approximately 6,378.1 kilometers
                ]
            }
        }
    }))
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

    return jsonify(parking_data)

# Handle the connection
@socketio.on('connect')
def handle_connect():
    print('Client connected')

# Handle custom connect event from client
@socketio.on('connect_event')
def handle_custom_connect_event(json):
    print('Received connect_event: ' + str(json))
    emit('server_response', {'data': 'Server connected!'},broadcast=True)

# Handle client event
@socketio.on('client_event')
def handle_client_event(json):
    print('Received data: ' + str(json))
    emit('server_response', {'data': 'Server received: ' + str(json['data'])},broadcast=True)


if __name__ == "__main__":
    socketio.run(app,debug=True,port=5000)
