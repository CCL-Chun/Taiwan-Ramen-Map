from flask import Flask, render_template, jsonify, request, make_response
from flask_socketio import SocketIO, emit, join_room, leave_room
from dotenv import load_dotenv
from Database import MongoDBConnection
from datetime import datetime
import requests
import logging
import redis
import pytz
import json
import os

## write to log
# logging.basicConfig(level=logging.INFO,filename='log_map.txt',filemode='a',
#    format='%(asctime)s %(filename)s %(levelname)s:%(message)s')
logging.basicConfig(level=logging.WARN,filename='log/ramen_map_log',filemode='a',
    format='%(asctime)s %(levelname)s:%(message)s')
## load env variables
load_dotenv()

## connect to cloud MongoDB
try:
    connection = MongoDBConnection()
    collection_ramen = connection.get_collection('ramen_info')
    collection_parking = connection.get_collection('parking_info')
    collection_youbike = connection.get_collection('youbike_info')
except Exception as e:
    logging.error(f"Cannot connect to MongoDB!{e}")

## connect to redis
redis_client = redis.Redis(host='localhost', port=6379, db=0)
# fetch ramen names and place_id
ramen_names = list(collection_ramen.find({
        "name": {"$exists": "true"}, "place_id": {"$exists": "true"}, "address": {"$exists": "true"}
    }, {
        "_id": 0, "name": 1, "place_id": 1, "address": 1
    })
)
# Ensure the old index deleted if it exists
try:
    redis_client.execute_command('FT.DROPINDEX', 'ramen_names_idx', 'IF EXISTS')
except Exception as e:
    print("Failed to drop index:", e)
# Create a RediSearch index on the 'name' field
redis_client.execute_command('FT.CREATE', 'ramen_names_idx', 'ON', 'HASH', 'PREFIX', 1, 'ramen:', 
                            'SCHEMA', 'name', 'TEXT', 'place_id', 'TEXT', 'address', 'TEXT')
for item in ramen_names:
    key = f"ramen:{item['name']}"
    redis_client.hset(key, mapping={
        'name': item['name'], 
        'place_id': item['place_id'],
        'address': item['address']
    })

## weekday determination
timezone = pytz.timezone('Asia/Taipei')
weekDaysMapping = ("星期一", "星期二",
                   "星期三", "星期四",
                   "星期五", "星期六",
                   "星期日")
def weekday():
    # will return 0 when Monday
    return datetime.weekday(datetime.now(pytz.utc).astimezone(timezone))

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

    if near_youbike:
        nearest = near_youbike[0]
        return nearest
    else:
        raise Exception(f"Find no YouBike stations around {lat},{lng}")

## function for planning YouBike routes
def route_youbike(start_lat,start_lng,end_lat,end_lng):
    try:
        googlemap_api_key = os.getenv("googlemaps_API_Key")
    except Exception as e:
        logging.error(f"Cannot get API KEY from env!{e}")

    try:
        start_bike_station = find_youbike(float(start_lat),float(start_lng))
        end_bike_station = find_youbike(float(end_lat),float(end_lng))

        start_info = {
            "latlng":[
                start_bike_station['geometry']['coordinates'][1],
                start_bike_station['geometry']['coordinates'][0]
            ],
            "sna":start_bike_station['properties']['sna'],
            "total":start_bike_station['properties']['total'],
            "available_rent_bikes":start_bike_station['properties']['available_rent_bikes'],
            "available_return_bikes":start_bike_station['properties']['available_return_bikes'],
            "updateTime":start_bike_station['properties']['updateTime']
        }

        end_info = {
            "latlng":[
                end_bike_station['geometry']['coordinates'][1],
                end_bike_station['geometry']['coordinates'][0]
            ],
            "sna":end_bike_station['properties']['sna'],
            "total":end_bike_station['properties']['total'],
            "available_rent_bikes":end_bike_station['properties']['available_rent_bikes'],
            "available_return_bikes":end_bike_station['properties']['available_return_bikes'],
            "updateTime":end_bike_station['properties']['updateTime']
        }

    except Exception as e:
        logging.info(f"{e} Use origin plan.")
        return make_response(jsonify({"error": f"{e} Use origin plan."}), 403)
        
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

    try:
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            route_data = response.json()
            
            route_json = {
                "route_data":route_data,
                "start_info":start_info,
                "end_info":end_info
            }

            return jsonify(route_json), 200
        else:
            logging.exception(f"{e} Use origin plan.")
            return make_response(jsonify({"error": f"{e} Use origin plan."}), response.status_code)
    
    except Exception as e:
        logging.info(f"{e} Use origin plan.")
        return make_response(jsonify({"error": f"{e} Use origin plan."}), 403)
        

def check_and_log_missing_data(ramen, field):
    if field not in ramen or not ramen[field]:
        logging.debug(f"Missing {field} for {ramen.get('_id', '待補')}\t{ramen.get('name', '待補')}")
        return True
    return False

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

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
                        4 / 6378.1 # equatorial radius of Earth is approximately 6,378.1 kilometers
                ]
            }
        }
    }).limit(100))
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
    } for ramen in ramen_data if not any(check_and_log_missing_data(ramen, key) for key in ["address", "open_time", "overall_rating"])]

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
            "place_id": ramen_details['place_id'],
            "features": ramen_details.get("features","由你來介紹"),
            "similar": ramen_details.get("top_similar","由你來推薦")
        }
    
        return jsonify(details_dict), 200
    else:
        return jsonify(f"place id {place_id} not found"), 404


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
            raise Exception(f"Google API error: {response.text}")

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
        start_info = []
        end_info = []
        if way.count('BUS') > 1:
            change_index = way.index('BUS') # the index of route to break and concat YouBike route
            change_location = fastest_route[0]['steps'][change_index]['transitDetails']['stopDetails']['arrivalStop']['location']['latLng']
            print(f"change_index: {change_index}")

            try:
                Bike_response = route_youbike(change_location['latitude'],change_location['longitude'],end_lat,end_lng)
                if Bike_response[1] == 200: # for flask internal function check
                    Bike = Bike_response[0].get_json()
                    
                    start_info = Bike['start_info']
                    end_info = Bike['end_info']
                    youbike_route = Bike['route_data']['routes'][0]['legs']
            
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
                        # logging.debug(bike_route)
                        raise Exception(f"Total {len(youbike_route)} steps for 4 waypoints!")
            except Exception as e:
                raise Exception(f"Cannot fetching route_youbike: {e}")

        if bike_route:
            try:
                combined_route = fastest_route[0]['steps'][:change_index+1]
            except Exception as e:
                logging.WARN(f"Wrong in combined_route: {start_lat},{start_lng},{end_lat},{end_lng}: {e}")
                raise Exception(f"Wrong in combined_route: {e}")
            try:
                ## append improved route into legs
                result['routes'][concat_index]['legs'].append([
                    {'stepsOverview' : 'combined'},
                    {'steps' : combined_route+bike_route}
                ])
            except Exception as e:
                logging.WARN(f"append improved route: {start_lat},{start_lng},{end_lat},{end_lng}: {e}")
                raise Exception(f"append improved route: {e}")

    except Exception as e:
        logging.info(f"Wrong in google route API: {e}")
    
    # add prompt for front-end to quick indexing
    result['prompt'] = [{
        'fastest_index' : concat_index,
        'youbike_improve' : 1 if bike_route else 0,
        'start_info' : start_info,
        'end_info' : end_info
    }]

    return jsonify(result), 200
    
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
    message = str(data['data'])
    timestamp = datetime.now(pytz.utc).strftime("%Y/%m/%d %H:%M:%S")

    message_data = {
        'message': message,
        'timestamp': timestamp
    }
    message_json = json.dumps(message_data)

    # Store message in Redis with expiration time (24 hours = 86400 seconds)
    redis_key = f"messages_{room_id}_{timestamp}"
    redis_client.setex(redis_key, 86400, message_json)

    emit('server_response', {
        'message': message,
        'time': timestamp
    }, room=room_id)

@socketio.on('join_room')
def on_join(data):
    room_id = data['id']
    join_room(room_id)

    # Fetch all messages for this room from Redis
    keys = redis_client.keys(f"messages_{room_id}_*")
    messages = [json.loads(redis_client.get(k).decode('utf-8')) for k in keys]
    
    # Emit all previous messages to the client
    for msg_data in messages:
        emit('server_response', {
            'message': msg_data['message'],
            'time': msg_data['timestamp']
        }, room=room_id)

@socketio.on('leave_room')
def on_leave(data):
    room_id = data['id']
    leave_room(room_id)

@app.route("/search/api/v1.0/name/autocomplete", methods=['GET'])
def autocomplete():
    query = request.args.get('query', '')
    if not query:
        return jsonify([])

    # Use RediSearch to perform a text search
    results = redis_client.execute_command('FT.SEARCH', 'ramen_names_idx', f'@name:*{query}*', 'LIMIT', 0, 10)
    if results[0] > 0:  # results[0] contains the number of search results
        # Parse results into dictionaries
        parsed_results = []
        for index in range(1, len(results), 2):  # Skip the count and iterate over results
            fields = results[index + 1]
            it = iter(fields)
            dict_result = dict(zip(it, it))  # Create a dictionary from the list of fields
            dict_result = {k.decode('utf-8'): v.decode('utf-8') for k, v in dict_result.items()}  # Decode bytes to string
            parsed_results.append(dict_result)
        return jsonify(parsed_results)
    else:
        return jsonify([])  # Return an empty list if no results found

@app.route("/ramen/api/v1.0/restaurants/searchone", methods=["GET"])
def search_ramen():
    place_id = request.args.get('place_id')
    # find ramen records
    ramen_search = collection_ramen.find_one({"place_id": place_id})

    # put data into features list
    ramen_geojson = {}
    ramen_geojson["features"] = [{
        "type": "Feature",
        "geometry": ramen_search["location"],
        "properties":
        {
            "name": ramen_search.get("name","待補"),
            "address": ramen_search.get("address","暫無"),
            "weekday": weekDaysMapping[weekday()],
            "open": ramen_search["open_time"][weekDaysMapping[weekday()]] if ramen_search["open_time"] else "不定",
            "overall": ramen_search["overall_rating"]["mean"],
            "id": ramen_search.get("place_id",ramen_search.get("name","待補"))
        }
    }]

    return jsonify(ramen_geojson), 200


if __name__ == "__main__":
    # app.run(debug=True,port=5000)
    socketio.run(app,debug=True,port=5000)
