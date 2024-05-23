import redis
import logging

class RedisConnection:
    def __init__(self, host='localhost', port=6379, db=0):
        try:
            self.redis_client = redis.Redis(host=host, port=port, db=db)
        except Exception as e:
            logging.error(f"Cannot connect to Redis! {e}")

    def get_client(self):
        return self.redis_client

    def drop_index(self, index_name):
        try:
            self.redis_client.execute_command('FT.DROPINDEX', index_name, 'IF EXISTS')
        except Exception as e:
            logging.error(f"Failed to drop index: {e}")

    def create_index(self, index_name, schema):
        try:
            self.redis_client.execute_command('FT.CREATE', index_name, 'ON', 'HASH', 'PREFIX', 1, 'ramen:', 'SCHEMA', *schema)
        except Exception as e:
            logging.error(f"Failed to create index: {e}")
