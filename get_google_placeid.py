from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import logging
import requests
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_place_id.txt',filemode='a',
    format='%(asctime)s %(levelname)s:%(message)s')

# connect to cloud MongoDB
try:
    load_dotenv()
    username = os.getenv("MongoDB_user")
    password = os.getenv("MongoDB_password")
    cluster_url = os.getenv("MongoDB_cluster_url")
    uri = f"mongodb+srv://{username}:{password}@{
        cluster_url}?retryWrites=true&w=majority&appName=ramen-taiwan"
    # create a new client and connect to the server
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client['ramen-taiwan']
    collection_ramen = db['ramen_info']

except Exception as e:
    logging.error(f"Cannot connect to MongoDB!{e}")

# get place id from place search text API (free if only request place id)
def get_place_id(query, api_key):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        'Content-Type': 'application/json',
        'X-Goog-Api-Key': api_key,
        'X-Goog-FieldMask': 'places.id'
    }
    payload = {
        'textQuery': query
    }
    response = requests.post(url, headers=headers, json=payload)
    result = response.json()
    if 'places' in result:
        # logging.info(f"{query} has {len(result['places'])} place id")
        if len(result['places']) == 1:
            return result['places'][0]['id'] # only one place id
        else:
            f = open("log_many_aliases.txt","a")
            for place in result['places']:
                f.write(f"{query}\t{place['id']}\n")
            f.close()
            return None # should be checked

    else:
        print(f"No places found or error {query}")
        logging.error(f"No places found or error {query}")

# get API from .env
try:
    API_KEY = os.getenv("googlemaps_API_Key")
    print(API_KEY)
except Exception as e:
    logging.error(f"Cannot get API KEY from env!{e}")

# retrieve place id
try:
    resturant = collection_ramen.find({}, {"name": 1, "_id": 1})

    wait_for_update = [] # list for update to MongoDB 
    for ramen in resturant:
        place_id = get_place_id(ramen["name"],API_KEY)
        if place_id:
            wait_for_update.append({
                "_id" : ramen["_id"],
                "name" : ramen["name"],
                "place_id" : place_id
            })

    print(f"Total to update: {len(wait_for_update)})")

except Exception as e:
    print(e)

# update to MongoDB
try:
    for updating in wait_for_update:
        update = collection_ramen.update_one(
            {"_id": updating["_id"]},
            {
                "$set": {
                    "place_id": updating["place_id"]
                }
            }
        )
        logging.info(f"{updating["name"]} update to MongoDB: {update}")

except Exception as e:
    print(e)