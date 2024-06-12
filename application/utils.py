from datetime import datetime, timedelta
from threading import Thread
import logging
import pytz
import json

## for creating rame_geojson
def create_geojson_feature(ramen):
    return {
        "type": "Feature",
        "geometry": ramen["location"],
        "properties": {
            "name": ramen.get("name", "待補"),
            "address": ramen.get("address", "暫無"),
            "weekday": current_weekday(),
            "open": ramen["open_time"].get(current_weekday(), "不定") if "open_time" and "open_time" in ramen else "不定",
            "overall": ramen.get("overall_rating", {}).get("mean", "N/A"),
            "id": ramen.get("place_id", ramen.get("name", "待補"))
        }
    }

## weekday determination
def current_weekday():
    timezone = pytz.timezone('Asia/Taipei')
    weekDaysMapping = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")
    # will return 0 when Monday
    current_weekday = datetime.now(pytz.utc).astimezone(timezone).weekday()
    return weekDaysMapping[current_weekday]

## calculate remain time to expiration for redis
def calculate_ttl():
    timezone = pytz.timezone('Asia/Taipei')
    now = datetime.now(timezone)
    midnight_next_day = (now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    ttl = (midnight_next_day - now).total_seconds()
    return int(ttl)

## function for finding nearest YouBike station
def find_youbike(collection_youbike,lat,lng):
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

## for checking missing keys in MongoDB documents
def check_and_log_missing_data(ramen, field):
    if field not in ramen or not ramen[field]:
        logging.debug(f"Missing {field} for {ramen.get('_id', '待補')}\t{ramen.get('name', '待補')}")
        return True
    return False

## parse the result seached from redis for response
def parse_redis_search_results(results):
    parsed_results = []
    if results[0] > 0:  # results[0] contains the number of search results
        # Parse results into dictionaries
        for index in range(1, len(results), 2):  # Skip the count and iterate over results
            fields = results[index + 1]
            it = iter(fields)
            dict_result = dict(zip(it, it))  # Create a dictionary from the list of fields
            dict_result = {k.decode('utf-8'): v.decode('utf-8') for k, v in dict_result.items()}  # Decode bytes to string
            parsed_results.append(dict_result)
    return parsed_results


def setup_redis_index(collection_ramen, redis_client):
    try:
        logging.info("Fetching ramen names from MongoDB.")
        ramen_names = list(collection_ramen.find({
            "name": {"$exists": True}, "place_id": {"$exists": True}, "address": {"$exists": True}
        }, {
            "_id": 1, "name": 1, "place_id": 1, "address": 1
        }))
        logging.info(f"Fetched {len(ramen_names)} ramen names.")

        # Check if the index exists before trying to drop it
        try:
            if redis_client.execute_command('FT._LIST') and 'ramen_names_idx' in redis_client.execute_command('FT._LIST'):
                logging.info("Dropping existing Redis index.")
                redis_client.execute_command('FT.DROPINDEX', 'ramen_names_idx', 'IF EXISTS')
            else:
                logging.info("No existing Redis index to drop.")
        except Exception as e:
            logging.warning(f"Error checking or dropping existing Redis index: {e}")

        # Define schema for the new index
        schema = ['name', 'TEXT', 'place_id', 'TEXT', 'address', 'TEXT']
        logging.info("Creating new Redis index.")
        redis_client.execute_command('FT.CREATE', 'ramen_names_idx', 'ON', 'HASH', 'PREFIX', 1, 'ramen:', 'SCHEMA', *schema)

        # Add ramen names to Redis
        logging.info("Adding ramen names to Redis.")
        for item in ramen_names:
            key = f"ramen:{str(item['_id'])}"
            redis_client.hset(key, mapping={
                'name': item['name'],
                'place_id': item['place_id'],
                'address': item['address']
            })
        logging.info("Redis index setup successfully.")

    except Exception as e:
        logging.warning(f"Failed to setup Redis index: {e}")


def handle_change_stream(change_stream, redis_client,collection_ramen):
    logging.info("Started listening for MongoDB change stream.")
    for change in change_stream:
        logging.info(f"Change detected in MongoDB: {change}")
        if change['operationType'] in ['insert', 'update', 'replace']:
            document = change['fullDocument']
            key = f"ramen:{str(document['_id'])}"
            logging.warning(f"Updating Redis cache for key: {key}")
            redis_client.hset(key, mapping={
                'name': document['name'],
                'place_id': document['place_id'],
                'address': document['address']
            })
        elif change['operationType'] == 'delete':
            key = f"ramen:{str(change['documentKey']['_id'])}"
            logging.warning(f"Deleting Redis cache for key: {key}")
            redis_client.delete(key)


def start_change_stream_listener(collection_ramen, redis_client):
    change_stream = collection_ramen.watch(full_document='updateLookup')
    change_stream_thread = Thread(target=handle_change_stream,
                                    args=(change_stream, redis_client, collection_ramen))
    change_stream_thread.start()


def store_message(redis_client, room_id, date_key, message_json, timezone):
    redis_key = f"messages_{room_id}_{date_key}"
    redis_client.zadd(redis_key, {message_json: datetime.now(timezone).timestamp()})

    if redis_client.ttl(redis_key) == -1:  # TTL of -1 indicates the key has no expiration
        ttl = calculate_ttl()
        redis_client.expire(redis_key, ttl)

def get_messages(redis_client, room_id, date_key):
    redis_key = f"messages_{room_id}_{date_key}"
    return redis_client.zrange(redis_key, 0, -1, withscores=True)