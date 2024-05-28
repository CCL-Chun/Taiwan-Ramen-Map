from flask import render_template, jsonify, request
from server import app
from werkzeug.exceptions import HTTPException
import logging

@app.route("/")
def first_view():
    return render_template('leaflet_map.html')

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"}), 200

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return e
    # Log the error
    logging.error(f"Unhandled Exception: {e}, Path: {request.path}")
    return render_template('500.html'), 500
