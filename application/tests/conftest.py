import pytest
import os
os.environ['FLASK_ENV'] = 'testing'

from server import app
from utils import setup_redis_index
from unittest.mock import MagicMock

@pytest.fixture(scope='session', autouse=True)
def set_test_env():
    """Set the FLASK_ENV to 'testing' for the duration of the tests."""
    os.environ['FLASK_ENV'] = 'testing'

@pytest.fixture
def test_app():
    # Ensure the app is configured for testing
    app.config.from_object('config.TestConfig')

    # Establish an application context before running the tests
    with app.app_context():
        yield app  # This will be available to any test that uses the 'test_app' fixture


@pytest.fixture()
def test_client():
    testing_client = app.test_client()

    # Establish an application context before running the tests.
    ctx = app.app_context()
    ctx.push()

    yield testing_client

    ctx.pop()


@pytest.fixture
def mock_redis_data():
    return [
        {"name": "麵屋武藏", "place_id": "1", "address": "Address 1"},
        {"name": "麵屋昕家", "place_id": "2", "address": "Address 2"},
        {"name": "羽都麵屋", "place_id": "3", "address": "Address 3"},
        {"name": "黑曜麵屋", "place_id": "4", "address": "Address 4"},
        {"name": "實正拉麵", "place_id": "5", "address": "Address 5"}
    ]

@pytest.fixture
def mock_redis(test_app, mock_redis_data):
    """Fixture to mock Redis client."""
    class MockRedis:
        def __init__(self):
            self.store = {}

        def get_client(self):
            return self

        def execute_command(self, *args):
            command, index, query, limit, start, num = args
            if command == 'FT.SEARCH' and index == 'ramen_names_idx':
                results = {
                    '麵屋': ['麵屋武藏', '麵屋昕家', '羽都麵屋', '黑曜麵屋'],
                    '拉麵': ['實正拉麵'],
                }
                search_term = query.split('*')[1]
                return [item for sublist in [results.get(k, []) for k in results if search_term in k] for item in sublist]
            return []

        def hset(self, key, mapping):
            self.store[key] = mapping

        def get(self, key):
            return self.store.get(key, None)

        def delete(self, key):
            if key in self.store:
                del self.store[key]

        def drop_database(self, db_name):
            self.store = {}

    test_app.redis_connection = MockRedis()

    # Setup the mock Redis index with sample data
    mock_collection = MagicMock()
    mock_collection.find.return_value = mock_redis_data
    setup_redis_index(mock_collection, test_app.redis_connection)

    yield test_app.redis_connection