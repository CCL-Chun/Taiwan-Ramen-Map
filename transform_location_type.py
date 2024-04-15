from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import os

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
    collection = db['ramen_info']
    # collection.create_index([("location", "2dsphere")]) # please create Geoindex after update
except Exception as e:
    logging.error(f"Cannot connect to MongoDB!{e}")

try:
  update_result = collection.update_many(
      {},  # all documents in the collection
      [
          {
              "$set": {
                  "location": {
                      "type": "Point",
                      "coordinates": [
                          {"$toDouble": "$longitude"},
                          {"$toDouble": "$latitude"}
                      ]
                  }
              }
          },
          {
              "$unset": ["latitude", "longitude"]  # remove the origin fields
          }
      ]
  )

  print(update_result)

except Exception as e:
  print(e)
