from flask import jsonify, request, make_response
from server import app
from utils import create_geojson_feature, check_and_log_missing_data
import logging


@app.route("/api/v1.0/ramens", methods=["GET"])
def get_ramens():
    mongo_connection = app.mongo_connection
    collection_ramen = mongo_connection.get_collection('ramen_info')
    
    try:
        center_received = request.args.get('center')
        if not center_received:
            return make_response(jsonify({'error': "Missing 'center' parameter"}), 400)
        lng, lat = map(float, center_received.split(','))
    except (ValueError, TypeError) as e:
        logging.error(f"Invalid 'center' parameter: {e}")
        return make_response(jsonify({'error': "Invalid 'center' parameter"}), 400)

    try:
        ramen_data = list(collection_ramen.find({
            "location": {
                "$geoWithin": {
                    "$centerSphere": [
                        [lng, lat],
                        3 / 6378.1  # equatorial radius of Earth in kilometers
                    ]
                }
            }
        }).limit(100))

        features = [create_geojson_feature(ramen) for ramen in ramen_data
                    if not any(check_and_log_missing_data(ramen, key) for key in ["address", "open_time", "overall_rating"])]

        return jsonify({"type": "FeatureCollection", "features": features})

    except Exception as e:
        logging.error(f"Database query failed: {e}")
        return make_response(jsonify({'error': "Database query failed"}), 500)


@app.route("/api/v1.0/ramens/details", methods=["GET"])
def ramen_details():
    place_id = request.args.get('id')
    if not place_id:
        return make_response(jsonify({'error': "Missing 'id' parameter"}), 400)

    mongo_connection = app.mongo_connection
    collection_ramen = mongo_connection.get_collection('ramen_info')

    try:
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
                "features": ramen_details.get("features", "由你來介紹"),
                "similar": ramen_details.get("top_similar", "由你來推薦")
            }
        
            return jsonify(details_dict), 200
        else:
            return make_response(jsonify({'error': f"place id {place_id} not found"}), 404)

    except Exception as e:
        logging.error(f"Database query failed: {e}")
        return make_response(jsonify({'error': "Database query failed"}), 500)