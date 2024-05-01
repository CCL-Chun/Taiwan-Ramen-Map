from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit, join_room, leave_room
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
    collection_youbike = db['youbike_info']

except Exception as e:
    logging.error(f"Cannot connect to MongoDB!{e}")


## function for finding nearest YouBike station
def find_youbike(lat,lng):
    near_youbike = list(collection_youbike.find({
        "geometry":{
            "$near":{
                "$geometry":{ 
                    "type": "Point", 
                    "coordinates": [lng, lat]
                }, 
                "$maxDistance": 300
            }
        }
    }).limit(3))

    nearest = near_youbike[0]
    return nearest

## function for planning YouBike routes
def route_youbike(start_lat,start_lng,end_lat,end_lng):
    try:
        googlemap_api_key = os.getenv("googlemaps_API_Key")
    except Exception as e:
        logging.error(f"Cannot get API KEY from env!{e}")

    start_bike_station = find_youbike(float(start_lat),float(start_lng))
    end_bike_station = find_youbike(float(end_lat),float(end_lng))

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
        "intermediates": [
            {
                "location":{
                    "latLng":{
                        "latitude": start_bike_station['geometry']['coordinates'][1],
                        "longitude": start_bike_station['geometry']['coordinates'][0]
                    }
                }
            },
            {
                "location":{
                    "latLng":{
                        "latitude": end_bike_station['geometry']['coordinates'][1],
                        "longitude": end_bike_station['geometry']['coordinates'][0]
                    }
                }
            }
        ],
        "travelMode": "WALK", # option 4
        "computeAlternativeRoutes": "true",
        "polylineEncoding": "GEO_JSON_LINESTRING", # specifying GeoJSON line string
    }
    response = requests.post(url, headers=headers, json=payload)
    return response

def check_and_log_missing_data(ramen, field):
    if field not in ramen or not ramen[field]:
        logging.exception(f"Missing {field} for {ramen.get('_id', '待補')}\t{ramen.get('name', '待補')}")
        return True
    return False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route("/details")
def show_detail_page():
    return render_template(".html")

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
                        2 / 6378.1 # equatorial radius of Earth is approximately 6,378.1 kilometers
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
            "name": ramen.get("name","待補"),
            "address": ramen.get("address","暫無"),
            "weekday": weekDaysMapping[weekday()],
            "open": ramen["open_time"][weekDaysMapping[weekday()]] if ramen["open_time"] else "不定",
            "overall": ramen["overall_rating"]["mean"],
            "id": ramen.get("place_id",ramen.get("name","待補"))
        }
    } for ramen in ramen_data if not any(check_and_log_missing_data(ramen, key) for key in ["address", "open_time", "overall_rating", "place_id"])]

    print(len(ramen_data))

    return jsonify(ramen_geojson)


@app.route("/ramen/api/v1.0/details", methods=["GET"])
def ramen_details():
    place_id = request.args.get('id')
    ramen_details = collection_ramen.find_one({"place_id": place_id})
    
    if ramen_details:
        details_dict = {
            "name": ramen_details['name'],
            "open_time": ramen_details['open_time'],
            "maps_url": ramen_details['maps_url'],
            "img_base64": ramen_details['img_base64'],
            "website": ramen_details['website'],
            "overall_rating": ramen_details['overall_rating'],
            "address": ramen_details['address'],
            "place_id": ramen_details['place_id']
        }
    
        return jsonify(details_dict), 200
    else:
        return jsonify(f"place id {place_id} not found"), 403


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


@app.route("/traffic/api/v1.0/routes/combined", methods=['GET'])
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
        # check the response status code
        if response.status_code == 200:
            result = response.json()
        else:
            raise Exception(f"{response.text}")

        # decide making another YouBike request or not
        time = []
        for i in result['routes']:
            time.append(i['duration'])
        concat_index = time.index(min(time))
        print(f"concat_index: {concat_index}")

        way = []
        fastest_route = result['routes'][concat_index]['legs']
        for i in fastest_route[0]['steps']:
            if 'transitDetails' in i.keys():
                way.append(i['transitDetails']['transitLine']['vehicle']['type'])
            else:
                way.append(i['travelMode'])
        
        print(way)
        # planning YouBike route start from the end of the first bus route
        bike_route = []
        if way.count('BUS') > 1:
            change_index = way.index('BUS') # the index of route to break and concat YouBike route
            change_location = fastest_route[0]['steps'][change_index]['transitDetails']['stopDetails']['arrivalStop']['location']['latLng']
            print(f"change_index: {change_index}")

            try:
                Bike_response = route_youbike(change_location['latitude'],change_location['longitude'],end_lat,end_lng)
                if Bike_response.status_code == 200:
                    Bike = Bike_response.json()
                    youbike_route = Bike['routes'][0]['legs']
            except Exception as e:
                raise Exception(f"Error fetching route_youbike: {e}")
            
            print(f"length of youbike_route: {len(youbike_route)}")
            if len(youbike_route) == 3:
                # WALK from bus stop to YouBike
                for step in youbike_route[0]['steps']:
                    bike_route.append(step)
                ## YouBike route
                for step in youbike_route[1]['steps']:
                    step['travelMode']= 'YouBike2'
                    bike_route.append(step)
                # WALK from YouBike to ramen
                for step in youbike_route[2]['steps']:
                    bike_route.append(step)
            else:
                raise Exception(f"Total {len(youbike_route)} steps for 4 waypoints!")
        # print(bike_route)
        
        if bike_route:
            try:
                combined_route = fastest_route[0]['steps'][:change_index+1]
            except Exception as e:
                raise Exception(f"Wrong in combined_route: {e}")
            try:
                ## append improved route into legs
                result['routes'][concat_index]['legs'].append([
                    {'stepsOverview' : 'combined'},
                    {'steps' : combined_route+bike_route}
                ])
            except Exception as e:
                raise Exception(f"Wrong in result: {e}")

    except Exception as e:
        logging.error(f"Wrong in google route API: {e}")
        print(e)
        return jsonify(result)
    
    # add prompt for front-end to quick indexing
    result['prompt'] = [{
        'fastest_index' : concat_index,
        'youbike_improve' : 1 if bike_route else 0
    }]

    return jsonify(result)
    
# Handle the connection
@socketio.on('connect')
def handle_connect():
    print('Client connected')

# Handle custom connect event from client
@socketio.on('connect_event')
def handle_custom_connect_event(data):
    print('Received connect_event: ' + str(data))
    emit('server_response', {'data': 'Server connected!'})

# Handle client event
@socketio.on('client_event')
def handle_client_event(data):
    room_id = data['id']
    print('Received data: ' + str(data))
    emit('server_response', {'message': str(data['data'])},room=room_id)

@socketio.on('join_room')
def on_join(data):
    room_id = data['id']
    join_room(room_id)
    emit('server_response', {'message': f'Joined room {room_id}'}, room=room_id)

@socketio.on('leave_room')
def on_leave(data):
    room_id = data['id']
    leave_room(room_id)
    emit('server_response', {'message': f'Left room {room_id}'}, room=room_id)



if __name__ == "__main__":
    # app.run(debug=True,port=5000)
    socketio.run(app,debug=True,port=5000)
