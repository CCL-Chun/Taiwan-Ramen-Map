from pymongo import MongoClient
from pymongo.server_api import ServerApi
from flask import current_app
import logging

class MongoDBConnection:
    def __init__(self, uri, db_name):
        """Initialize the MongoDB connection."""
        try:
            self.client = MongoClient(uri, server_api=ServerApi('1'),readPreference='secondaryPreferred')
            self.db = self.client[db_name]
        except Exception as e:
            logging.error(f"Cannot connect to MongoDB! {e}")
            raise e

    def get_collection(self, collection_name):
        """Retrieve a collection by name from the database."""
        return self.db[collection_name]



# Usage example:
# in __init__.py
#=================
# global mongo_connection
# mongo_connection = MongoDBConnection(app.config['MONGO_URI'], app.config['DB_NAME'])
#=================
# in controller.py
#=================
# from ..models.Database import mongo_connection
# collection_ramen = mongo_connection.get_collection('ramen_info')
#=================
