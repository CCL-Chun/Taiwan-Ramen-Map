from pymongo import UpdateOne
from dotenv import load_dotenv
from Database import MongoDBConnection
from Youbike_realtime_info import YoubikeTaipei
import logging
import json
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_update_youbike.txt',filemode='a',
    format='%(asctime)s %(filename)s %(levelname)s:%(message)s')

## connect to cloud MongoDB
try:
    connection = MongoDBConnection()
    collection = connection.get_collection('youbike_info')
except Exception as e:
    print(e)

## retrieve data from API
data_to_update = YoubikeTaipei().parse_for_mongodb()

## update using bulk write
operations = []
for item in data_to_update:
    query = {"properties.sno": item["properties"]["sno"]}
    update = {"$set": item}
    operation = UpdateOne(query, update, upsert=True)
    operations.append(operation)

try:
    if operations:
        result = collection.bulk_write(operations, ordered=False)
        logging.info(f"Youbike data updated successfully: {result.bulk_api_result}")
        # print(f"Youbike data updated successfully: {result.bulk_api_result}")
    else:
        logging.info("No Youbike data to update.")
        # print("No Youbike data to update.")
except Exception as e:
    logging.error(f"Error during Youbike data bulk update: {e}")
    print(e)
