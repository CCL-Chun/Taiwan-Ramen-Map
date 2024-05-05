from pymongo import UpdateOne
from dotenv import load_dotenv
from Database import MongoDBConnection
import logging
import json
import os
import re

## write to log
logging.basicConfig(level=logging.INFO,filename='log_update_ramen.txt',filemode='a',
    format='%(asctime)s %(filename)s %(levelname)s:%(message)s')

## connect to cloud MongoDB
try:
    connection = MongoDBConnection()
    collection = connection.get_collection('ramen_info')
except Exception as e:
    print(e)

with open("redo_list.json","r") as f:
    data = json.loads(f.read())

# operations = []
# for ramen in data:
#     new_url = re.sub(r'place/.*/data','place/data',ramen["maps_url"])
#     location = {
#         "type":"Point",
#         "coordinates":[
#             float(ramen["longitude"]),float(ramen["latitude"])
#         ]
#     }
#     query = {"name": ramen["name"]}
#     update = {
#         "$set": {
#             "name": ramen["name"],
#             "maps_url": new_url,
#             "location": location
#         }
#     }
#     operation = UpdateOne(query, update, upsert=True)
#     operations.append(operation)

# try:
#     if operations:
#         result = collection.bulk_write(operations, ordered=False)
#         logging.info(f"Ramen data updated successfully: {result.bulk_api_result}")

#     else:
#         logging.info("No Ramen data to update.")

# except Exception as e:
#     logging.error(f"Error during Ramen data bulk update: {e}")
#     print(e)
