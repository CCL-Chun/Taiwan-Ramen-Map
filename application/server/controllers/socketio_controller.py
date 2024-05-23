from flask_socketio import SocketIO, emit, join_room, leave_room
from server import app, socketio
from utils import store_message, get_messages, calculate_ttl
from datetime import datetime
import pytz
import json
import logging

timezone = pytz.timezone('Asia/Taipei')
# Handle the connection
@socketio.on('connect')
def handle_connect():
    print('Client connected')

# Handle custom connect event from client
@socketio.on('connect_event')
def handle_custom_connect_event(data):
    print('Received connect_event: ' + str(data))
    emit('server_response', {'data': 'Server connected!'})

# Handle client event
@socketio.on('client_event')
def handle_client_event(data):
    room_id = data['id']
    message = str(data['data'])
    timestamp = datetime.now(timezone).strftime("%Y/%m/%d %H:%M:%S")
    date_key = datetime.now(timezone).strftime("%Y/%m/%d")

    message_data = {
        'message': message,
        'timestamp': timestamp
    }
    message_json = json.dumps(message_data)

    # Store message in Redis
    redis_client = app.redis_connection.get_client()
    store_message(redis_client, room_id, date_key, message_json, timezone)

    emit('server_response', {
        'message': message,
        'time': timestamp
    }, room=room_id)

@socketio.on('join_room')
def on_join(data):
    room_id = data['id']
    join_room(room_id)

    date_key = datetime.now(timezone).strftime("%Y/%m/%d")
    redis_client = app.redis_connection.get_client()
    messages_with_scores = get_messages(redis_client, room_id, date_key)

    # Emit all previous messages to the client
    for msg_json, timestamp in messages_with_scores:
        msg = json.loads(msg_json.decode('utf-8'))
        emit('server_response', {
            'message': msg['message'],
            'time': msg['timestamp']
        }, room=room_id)

@socketio.on('leave_room')
def on_leave(data):
    room_id = data['id']
    leave_room(room_id)
