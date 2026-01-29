"""
Flask Web Application for BLE Tag Tracking System
Displays tag positions on a map and allows sending alarms
"""
import asyncio
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from functools import wraps
import threading
import os
import tag_mapping

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Global references - will be set from run.py
db_handler = None
alarm_service = None
event_loop = None

# List of available rooms for alarms
ROOMS = [
    "423A", "KORYTARZ", "SCHODY", "WC", "WINDA",
]


def init_app(db, alarm_svc, loop):
    """Initialize Flask app with database and alarm service references"""
    global db_handler, alarm_service, event_loop
    db_handler = db
    alarm_service = alarm_svc
    event_loop = loop


@app.route('/')
def index():
    """Main page with map display"""
    return render_template('index.html', rooms=ROOMS)


@app.route('/static/plan_img.png')
def serve_map():
    """Serve the floor plan image"""
    return send_from_directory(os.path.dirname(__file__), 'plan_img.png')


@app.route('/api/positions')
def get_positions():
    """Get current positions of all tags"""
    if not db_handler:
        return jsonify({"error": "Database not initialized"}), 500
    
    try:
        positions = db_handler.get_all_current_positions()
        return jsonify(positions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/history/<tag_identifier>')
def get_history(tag_identifier):
    """Get location history for a specific tag (by name or MAC)"""
    if not db_handler:
        return jsonify({"error": "Database not initialized"}), 500
    
    # Sprawdź czy to nazwa czy MAC
    mac_address = tag_mapping.get_mac_by_name(tag_identifier)
    if not mac_address:
        # Jeśli nie znaleziono w mapowaniu, zakładamy że to MAC
        mac_address = tag_identifier
    
    time_range = request.args.get('range', '-1h')
    
    try:
        history = db_handler.get_history(mac_address, time_range)
        # Convert datetime objects to ISO strings
        for entry in history:
            if entry.get('time'):
                entry['time'] = entry['time'].isoformat()
        return jsonify(history)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tags')
def get_tags():
    """Get list of all known tags"""
    if not db_handler:
        return jsonify({"error": "Database not initialized"}), 500
    
    try:
        # Zwracamy mapowanie nazw do MAC
        tags = tag_mapping.get_all_tags()
        return jsonify(tags)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/alarm', methods=['POST'])
def send_alarm():
    """Send alarm to a specific tag"""
    if not alarm_service or not event_loop:
        return jsonify({"error": "Alarm service not initialized"}), 500
    
    data = request.get_json()
    mac_address = data.get('mac')
    tag_name = data.get('name')
    room = data.get('room')
    
    # Jeśli podano nazwę zamiast MAC, zamień na MAC
    if tag_name and not mac_address:
        mac_address = tag_mapping.get_mac_by_name(tag_name)
        if not mac_address:
            return jsonify({"error": f"Unknown tag name: {tag_name}"}), 400
    
    if not mac_address or not room:
        return jsonify({"error": "Missing mac/name or room parameter"}), 400
    
    try:
        # Schedule coroutine in the main event loop
        future = asyncio.run_coroutine_threadsafe(
            alarm_service.trigger_alarm(room, mac_address+''.join(format(ord(c), '02x') for c in room)),
            event_loop
        )
        future.result(timeout=5)  # Wait up to 5 seconds
        tag_display = tag_mapping.get_name_by_mac(mac_address)
        return jsonify({"success": True, "message": f"Alarm sent to {tag_display} for room {room}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/rooms')
def get_rooms():
    """Get list of available rooms"""
    return jsonify(ROOMS)


@app.route('/api/tag-mapping')
def get_tag_mapping():
    """Get tag name to MAC address mapping"""
    return jsonify({
        "name_to_mac": tag_mapping.TAG_NAME_TO_MAC,
        "mac_to_name": tag_mapping.TAG_MAC_TO_NAME
    })


def run_flask(host='0.0.0.0', port=5001):
    """Run Flask app in a separate thread"""
    app.run(host=host, port=port, debug=False, threaded=True, use_reloader=False)


def start_flask_thread(host='0.0.0.0', port=5001):
    """Start Flask in a background thread"""
    flask_thread = threading.Thread(
        target=run_flask, 
        args=(host, port),
        daemon=True
    )
    flask_thread.start()
    print(f"[Flask] Web server started at http://{host}:{port}")
    return flask_thread
