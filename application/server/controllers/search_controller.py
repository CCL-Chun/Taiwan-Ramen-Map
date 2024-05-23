from flask import request, jsonify, make_response
from server import app
from utils import create_geojson_feature, parse_redis_search_results
import logging


# autocomplete in search box
@app.route("/api/v1.0/ramens/autocomplete", methods=['GET'])
def autocomplete():
    query = request.args.get('query', '')
    if not query:
        return jsonify([]) # Return an empty list if search fails

    # Use RediSearch to perform a text search
    try:
        redis_client = app.redis_connection.get_client()
        results = redis_client.execute_command('FT.SEARCH', 'ramen_names_idx', f'@name:*{query}*', 'LIMIT', 0, 10)
        parsed_results = parse_redis_search_results(results)
        return jsonify(parsed_results)
    except Exception as e:
        logging.error(f"Search failed on {query}: {e}")
        return jsonify({'error': 'Search failed'}), 500

# search ramen by place_id
@app.route("/api/v1.0/ramens/<string:place_id>", methods=["GET"])
def search_ramen(place_id):
    mongo_connection = app.mongo_connection
    collection_ramen = mongo_connection.get_collection('ramen_info')
    
    try:
        ramen_search = collection_ramen.find_one({"place_id": place_id})
        if not ramen_search:
            return make_response(jsonify({'error': "Ramen restaurant not found"}), 404)

        feature = create_geojson_feature(ramen_search)
        return jsonify({"features": [feature]}), 200

    except Exception as e:
        logging.error(f"Database query failed: {e}")
        return make_response(jsonify({'error': "Database query failed"}), 500)
