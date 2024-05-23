import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DEBUG = False
    TESTING = False

    SECRET_KEY = os.getenv('SECRET_KEY') or 'a_secret_key'
    MONGO_URI = f"mongodb+srv://{os.getenv('MongoDB_user')}:{os.getenv('MongoDB_password')}@{os.getenv('MongoDB_cluster_url')}?retryWrites=true&w=majority&appName=ramen-taiwan"
    DB_NAME = 'ramen-taiwan'
    GOOGLE_MAPS_API_KEY = os.getenv('googlemaps_API_Key')

class TestConfig(Config):
    TESTING = True
    USE_MOCK_DATABASE = True
    USE_MOCK_API_KEYS = True
