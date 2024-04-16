from dotenv import load_dotenv
from Database import MongoDBConnection
from Youbike_realtime_info import YoubikeTaipei
import logging
import json
import os

## write to log
# logging.basicConfig(level=logging.INFO,filename='log_update_youbike.txt',filemode='a',
#     format='%(asctime)s %(filename)s %(levelname)s:%(message)s')

## connect to cloud MongoDB
try:
    connection = MongoDBConnection()
    collection = connection.get_collection('youbike_info')
except Exception as e:
    print(e)

## retrieve data from API
data_to_update = YoubikeTaipei().parse_for_mongodb()

## update
if data_to_update:
    for item in data_to_update:
        sno = item["properties"]["sno"] # station id
        new_statement = {
            "properties.sbi": item["properties"]["sbi"],
            "properties.mday": item["properties"]["mday"],
            "properties.bemp": item["properties"]["bemp"],
            "properties.srcUpdateTime": item["properties"]["srcUpdateTime"],
            "properties.updateTime": item["properties"]["updateTime"],
            "properties.infoTime": item["properties"]["infoTime"],
            "properties.infoDate": item["properties"]["infoDate"],
            "properties.act": item["properties"]["act"]
        }

        collection.update_one(
            {"properties.sno": sno},  # Query to find the document (using station ID inside properties)
            {"$set": new_statement}
        )
else:
    print("No data")
