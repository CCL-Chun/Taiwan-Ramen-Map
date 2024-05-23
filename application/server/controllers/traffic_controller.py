from flask import jsonify, request, make_response
from server import app
from utils import find_youbike, calculate_ttl
import logging
import requests


@app.route("/api/v1.0/parking", methods=["GET"])
def get_parking():
    lat = request.args.get('lat',type=float)
    lng = request.args.get('lng',type=float)
    if lat is None or lng is None:
        return jsonify({'error': "Missing 'lat' or 'lng' parameter"}), 400

    mongo_connection = app.mongo_connection
    collection_youbike = mongo_connection.get_collection('youbike_info')
    collection_parking = mongo_connection.get_collection('parking_info')

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

    return jsonify(parking_data), 200


## function for planning YouBike routes
@app.route("/api/v1.0/traffic/routes/youbike", methods=["GET"])
def route_youbike():
    googlemap_api_key = app.config.get('GOOGLE_MAPS_API_KEY')
    if not googlemap_api_key:
        logging.error("Cannot get API KEY from config!")
        return jsonify({'error': "Internal server error"}), 500

    mongo_connection = app.mongo_connection
    collection_youbike = mongo_connection.get_collection('youbike_info')

    try:
        start_lat = request.args.get('start_lat')
        start_lng = request.args.get('start_lng')
        end_lat = request.args.get('end_lat')
        end_lng = request.args.get('end_lng')

        if not all([start_lat, start_lng, end_lat, end_lng]):
            return make_response(jsonify({'error': "Missing one or more required parameters: start_lat, start_lng, end_lat, end_lng"}), 400)

        # Convert parameters to float
        try:
            start_lat = float(start_lat)
            start_lng = float(start_lng)
            end_lat = float(end_lat)
            end_lng = float(end_lng)
        except ValueError:
            raise ValueError("Invalid latitude or longitude format. They must be valid numbers.")
    except Exception as e:
        return make_response(jsonify({'error': f"{e}"}), 400)

    try:
        start_bike_station = find_youbike(collection_youbike, start_lat, start_lng)
        end_bike_station = find_youbike(collection_youbike, end_lat, end_lng)

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
        return jsonify({"error": f"{e} Use origin plan."}), 403
        
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


@app.route("/api/v1.0/routes/combined", methods=['GET'])
def route_plan():
    start_lat = request.args.get('start_lat')
    start_lng = request.args.get('start_lng')
    end_lat = request.args.get('end_lat')
    end_lng = request.args.get('end_lng')
    if not all([start_lat, start_lng, end_lat, end_lng]):
        return make_response(jsonify({'error': "Missing one or more required parameters: start_lat, start_lng, end_lat, end_lng"}), 400)

    googlemap_api_key = app.config.get('GOOGLE_MAPS_API_KEY')
    if not googlemap_api_key:
        logging.error("Cannot get API KEY from config!")
        return jsonify({'error': "Internal server error"}), 500

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
        if response.status_code != 200:
            raise Exception(f"Google API error: {response.text}")

        result = response.json()

        # decide making another YouBike request or not
        time = []
        for i in result['routes']:
            time.append(i['duration'])
        concat_index = time.index(min(time))

        way = []
        fastest_route = result['routes'][concat_index]['legs']
        for i in fastest_route[0]['steps']:
            if 'transitDetails' in i.keys():
                way.append(i['transitDetails']['transitLine']['vehicle']['type'])
            else:
                way.append(i['travelMode'])

    except Exception as e:
        logging.error(f"Wrong in Google route API: {e}")

    try:
        # planning YouBike route start from the end of the first bus route
        bike_route = []
        start_info = []
        end_info = []
        if way.count('BUS') > 1:
            change_index = way.index('BUS') # the index of route to break and concat YouBike route
            change_location = fastest_route[0]['steps'][change_index]['transitDetails']['stopDetails']['arrivalStop']['location']['latLng']

            with app.test_client() as client:
                start_lat = change_location['latitude']
                start_lng = change_location['longitude']

                route_url = f"/api/v1.0/traffic/routes/youbike?start_lat={start_lat}&start_lng={start_lng}&end_lat={end_lat}&end_lng={end_lng}"

                # Make the request to the test client
                Bike_response = client.get(route_url)
                bike_data = Bike_response.get_json()
                bike_status_code = Bike_response.status_code

            if bike_status_code == 200:
                start_info = bike_data['start_info']
                end_info = bike_data['end_info']
                youbike_route = bike_data['route_data']['routes'][0]['legs']
            
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
                raise Exception(f"Wrong append improved route: {e}")

    except Exception as e:
        logging.info(f"Wrong in combine route: {e}")
    
    # add prompt for front-end to quick indexing
    result['prompt'] = [{
        'fastest_index' : concat_index,
        'youbike_improve' : 1 if bike_route else 0,
        'start_info' : start_info,
        'end_info' : end_info
    }]

    return jsonify(result), 200