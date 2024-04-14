from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# serve the web page
@app.route('/')
def index():
    return render_template('socket_io_test.html') 

# Handle the connection
@socketio.on('connect')
def handle_connect():
    print('Client connected')

# Handle custom connect event from client
@socketio.on('connect_event')
def handle_custom_connect_event(json):
    print('Received connect_event: ' + str(json))
    emit('server_response', {'data': 'Server connected!'},broadcast=True)

# Handle client event
@socketio.on('client_event')
def handle_client_event(json):
    print('Received data: ' + str(json))
    emit('server_response', {'data': 'Server received: ' + str(json['data'])},broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)
