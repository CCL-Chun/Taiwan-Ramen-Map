from dotenv import load_dotenv
from Database import MongoDBConnection
import requests
import json
import os

## connect to cloud MongoDB
try:
    connection = MongoDBConnection()
    ramen_collection = connection.get_collection('ramen_info')
    parking_collection = connection.get_collection('parking_info')
except Exception as e:
    print(e)

import requests
import json

class YoubikeTaipei:
    def __init__(self):
        """
        Initializes the parser with the URL from Taipei City.
        """
        self.url = "https://tcgbusfs.blob.core.windows.net/dotapp/youbike/v2/youbike_immediate.json"

    def fetch_data(self):
        """
        Fetch the data from Taipei City Youbike2.0.
        :return: JSON format
        """
        try:
            response = requests.get(self.url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to fetch data: {e}")
            return []

    def parse_for_mongodb(self):
        """
        Parses the Youbike data to format suitable for MongoDB geoindexing.
        :return: List of dictionaries with modified 'coordinates' field for geoindexing
        """
        data = self.fetch_data()
        if not data:
            return [] # when fetch_data failed

        parsed_data = []
        for item in data:
            coordinates = [item.get('longitude'), item.get('latitude')]
            modified_item = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": coordinates
                },
                "properties": {key: value for key, value in item.items() if key not in ['latitude', 'longitude']}
            }
            parsed_data.append(modified_item)

        return parsed_data
