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

load_dotenv()
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
# app.config['SECRET_KEY'] = 'secret!'
# socketio = SocketIO(app)


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
    lat = request.args.get('lat',type=float)
    lng = request.args.get('lng',type=float)
    # find parking lot records
    parking_lots = list(collection_parking.find({
        "geometry":{
            "$geoWithin":{
                "$centerSphere":[
                        [lng, lat],
                        0.5 / 6378.1 # equatorial radius of Earth is approximately 6,378.1 kilometers
                ]
            }
        },
        "$or":[
            {"properties.gatename": { "$exists": "true" }}, 
            {"properties.pktype": { "$in": ["01","02","03","04","09","10","11","15","18","19","20","22","23"] }}
        ]
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

    return jsonify(parking_data)

@app.route("/traffic/api/v1.0/routes", methods=['GET'])
def route_plan():
    start_lat = request.args.get('start_lat')
    start_lng = request.args.get('start_lng')
    end_lat = request.args.get('end_lat')
    end_lng = request.args.get('end_lng')
    try:
        googlemap_api_key = os.getenv("googlemaps_API_Key")
    except Exception as e:
        logging.error(f"Cannot get API KEY from env!{e}")

    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': googlemap_api_key,
        'X-Goog-FieldMask': (
            'routes.polyline,'
            'routes.routeLabels,'
            'routes.duration,'
            'routes.distanceMeters,'
            'routes.localizedValues,'
            'routes.legs.distanceMeters,'
            'routes.legs.stepsOverview,'
            'routes.legs.steps.staticDuration,'
            'routes.legs.steps.transitDetails,'
            'routes.legs.steps.navigationInstruction,'
            'routes.legs.steps.localizedValues,'
            'routes.legs.steps.travelMode,'
            'routes.legs.steps.polyline') # option 1
    }
    payload = {
        "origin": {
            "location": {"latLng": {"latitude":start_lat,"longitude":start_lng}} # option 2
        },
        "destination": {
            "location": {"latLng": {"latitude":end_lat,"longitude":end_lng}} # option 3
        },
        "travelMode": "TRANSIT", # option 4
        "computeAlternativeRoutes": "true",
        "polylineEncoding": "GEO_JSON_LINESTRING", # specifying GeoJSON line string
        "transitPreferences": {
            "routingPreference": "LESS_WALKING", # option 5
            "allowedTravelModes": ["BUS","RAIL"] # option 6
        },
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        result = response.json()
        print(result)
        return result
    except Exception as e:
        print(e)
        return e, 500    
        

# Handle the connection
# @socketio.on('connect')
# def handle_connect():
#     print('Client connected')

# # Handle custom connect event from client
# @socketio.on('connect_event')
# def handle_custom_connect_event(json):
#     print('Received connect_event: ' + str(json))
#     emit('server_response', {'data': 'Server connected!'},broadcast=True)

# # Handle client event
# @socketio.on('client_event')
# def handle_client_event(json):
#     print('Received data: ' + str(json))
#     emit('server_response', {'data': 'Server received: ' + str(json['data'])},broadcast=True)


if __name__ == "__main__":
    app.run(debug=True,port=5000)
