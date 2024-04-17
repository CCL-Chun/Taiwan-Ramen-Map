from dotenv import load_dotenv
from Database import MongoDBConnection
from Youbike_realtime_info import YoubikeTaipei
import logging
import json
import os

## write to log
logging.basicConfig(level=logging.INFO,filename='log_youbike.txt',filemode='a',
    format='%(asctime)s %(filename)s %(levelname)s:%(message)s')

## connect to cloud MongoDB
try:
    connection = MongoDBConnection()
except Exception as e:
    print(e)

## retrieve data from API
data_to_save = YoubikeTaipei().parse_for_mongodb()

## insert to DB
collection = connection.get_collection('youbike_info')
collection.create_index([("geometry", "2dsphere")])

try:
    if data_to_save:
        collection.insert_many(data_to_save)
        print("Data inserted successfully!")
    else:
        print("No data to insert.")
except Exception as e:
    print(e)