from pymongo import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

class MongoDBConnection:
    def __init__(self):
        """Initialize the MongoDB connection."""
        try:
            load_dotenv()  # Load environment variables
            username = os.getenv("MongoDB_user")
            password = os.getenv("MongoDB_password")
            cluster_url = os.getenv("MongoDB_cluster_url")
            uri = f"mongodb+srv://{username}:{password}@{cluster_url}?retryWrites=true&w=majority&appName=ramen-taiwan"
            self.client = MongoClient(uri, server_api=ServerApi('1'))
            self.db = self.client['ramen-taiwan']
        except Exception as e:
            print(f"Cannot connect to MongoDB! {e}")
            raise e

    def get_collection(self, collection_name):
        """Retrieve a collection by name from the database."""
        return self.db[collection_name]

# Usage example:
# connection = MongoDBConnection()
# ramen_collection = connection.get_collection('ramen_info')
# parking_collection = connection.get_collection('parking_info')
