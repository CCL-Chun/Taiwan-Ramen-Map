from flask import render_template, jsonify
from server import app

@app.route("/")
def first_view():
    return render_template('leaflet_map.html')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200
