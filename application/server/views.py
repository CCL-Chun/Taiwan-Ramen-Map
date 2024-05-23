from flask import render_template
from server import app

@app.route("/")
def first_view():
    return render_template('leaflet_map.html')
