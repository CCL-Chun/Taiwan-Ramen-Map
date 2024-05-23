# server/__init__.py
from flask import Flask
from flask_socketio import SocketIO
from server.models.Database import MongoDBConnection
from server.models.Redis import RedisConnection
from config import Config, TestConfig
from utils import setup_redis_index
import logging
import os
import mongomock

logging.basicConfig(level=logging.INFO,filename='../log/ramen_map_log',filemode='a',
   format='%(asctime)s %(filename)s %(levelname)s:%(message)s')

# Determine the configuration class
config_class = TestConfig if os.getenv('FLASK_ENV') == 'testing' else Config

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(config_class)

if config_class == TestConfig:
    # Use mongomock for MongoDB in testing
    mock_mongo_client = mongomock.MongoClient()
    app.mongo_connection = mock_mongo_client[app.config['DB_NAME']]

    # Mock Redis client
    class MockRedis:
        def __init__(self):
            self.store = {}

        def get_client(self):
            return self

        def execute_command(self, *args):
            pass

        def hset(self, key, mapping):
            self.store[key] = mapping

        def get(self, key):
            return self.store.get(key, None)

        def delete(self, key):
            if key in self.store:
                del self.store[key]

        def drop_database(self, db_name):
            self.store = {}

    app.redis_connection = MockRedis()

    # Mock SocketIO
    class MockSocketIO:
        def __init__(self, *args, **kwargs):
            pass

        def on(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator

        def emit(self, *args, **kwargs):
            pass

        def run(self, *args, **kwargs):
            pass

    socketio = MockSocketIO()
else:
    # Initialize extensions
    socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

    # Initialize databases
    app.mongo_connection = MongoDBConnection(app.config['MONGO_URI'], app.config['DB_NAME'])
    app.redis_connection = RedisConnection(host='localhost', port=6379, db=0)

    # Setup Redis index
    try:
        setup_redis_index(app.mongo_connection.get_collection('ramen_info'), app.redis_connection.get_client())
    except Exception as e:
        logging.error(f"Error setting up Redis index: {e}")

# Import routes after app initialization to avoid circular imports
with app.app_context():
    from server.controllers import traffic_controller, ramen_controller, search_controller, socketio_controller
    import server.views
