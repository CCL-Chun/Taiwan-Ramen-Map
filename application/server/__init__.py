# server/__init__.py
from flask import Flask
from flask_socketio import SocketIO
from server.models.Database import MongoDBConnection
from server.models.Redis import RedisConnection
from config import Config, TestConfig
from utils import setup_redis_index, handle_change_stream, start_change_stream_listener
import logging
import os
import mongomock

# Determine the configuration class
config_class = TestConfig if os.getenv('FLASK_ENV') == 'testing' else Config

# Initialize Flask application
app = Flask(__name__)
app.config.from_object(config_class)

if config_class == TestConfig:
    # Use mongomock for MongoDB in testing
    mock_mongo_client = mongomock.MongoClient()
    app.mongo_connection = mock_mongo_client[app.config['DB_NAME']]

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
    logging.basicConfig(level=logging.WARN,filename='../log/ramen_map_log',filemode='a',
        format='%(asctime)s %(filename)s %(levelname)s:%(message)s')
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

    # Setup event-based invalidation to update cache in Redis
    try:
        start_change_stream_listener(app.mongo_connection.get_collection('ramen_info'), app.redis_connection.get_client())
    except Exception as e:
        logging.error(f"Error setting up event-based invalidation: {e}")


# Import routes after app initialization to avoid circular imports
with app.app_context():
    from server.controllers import traffic_controller, ramen_controller, search_controller, socketio_controller
    import server.views
