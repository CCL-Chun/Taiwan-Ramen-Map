from datetime import datetime, timedelta
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
            "open": ramen["open_time"].get(current_weekday(), "不定") if "open_time" in ramen else "不定",
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
        ramen_names = list(collection_ramen.find({
            "name": {"$exists": True}, "place_id": {"$exists": True}, "address": {"$exists": True}
        }, {
            "_id": 0, "name": 1, "place_id": 1, "address": 1
        }))

        redis_client.execute_command('FT.DROPINDEX', 'ramen_names_idx', 'IF EXISTS')

        schema = ['name', 'TEXT', 'place_id', 'TEXT', 'address', 'TEXT']
        redis_client.execute_command('FT.CREATE', 'ramen_names_idx', 'ON', 'HASH', 'PREFIX', 1, 'ramen:', 'SCHEMA', *schema)

        for item in ramen_names:
            key = f"ramen:{item['name']}"
            redis_client.hset(key, mapping={
                'name': item['name'], 
                'place_id': item['place_id'],
                'address': item['address']
            })
    except Exception as e:
        logging.error(f"Failed to setup Redis index: {e}")

def store_message(redis_client, room_id, date_key, message_json, timezone):
    redis_key = f"messages_{room_id}_{date_key}"
    redis_client.zadd(redis_key, {message_json: datetime.now(timezone).timestamp()})

    if redis_client.ttl(redis_key) == -1:  # TTL of -1 indicates the key has no expiration
        ttl = calculate_ttl()
        redis_client.expire(redis_key, ttl)

def get_messages(redis_client, room_id, date_key):
    redis_key = f"messages_{room_id}_{date_key}"
    return redis_client.zrange(redis_key, 0, -1, withscores=True)