import os
import io
import json
import pathlib
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# Import mgz header + summary (NOT mgz.replay, to avoid the "Renamed object" error)
from mgz import header, summary

# ------------------------------------------------------------------------------
# Flask app & DB setup
# ------------------------------------------------------------------------------
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'game_stats.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "pool_size": 10,       # default is often 5
    "max_overflow": 20,    # allow extra connections beyond pool_size
    "pool_timeout": 30,    # wait up to 30s for a connection before giving up
    "pool_recycle": 1800   # recycle connections after 30 minutes
}

db = SQLAlchemy(app)

# ------------------------------------------------------------------------------
# Define the GameStats model
# ------------------------------------------------------------------------------
class GameStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    replay_file = db.Column(db.String(500), unique=True, nullable=False)
    game_version = db.Column(db.String(50))
    map = db.Column(db.Text)
    game_type = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    winner = db.Column(db.String(100))
    players = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, nullable=False)  # ✅ Change to required field


# Ensure tables exist on startup
with app.app_context():
    db.create_all()

# ------------------------------------------------------------------------------
# Global error handler to ensure CORS on errors
# ------------------------------------------------------------------------------
@app.errorhandler(Exception)
def handle_exception(e):
    """
    Catch any unhandled exception, return JSON with 500 status,
    ensuring we still set the CORS header for Safari or other browsers.
    """
    logging.error(f"❌ Uncaught Exception: {e}", exc_info=True)
    response = jsonify({"error": str(e)})
    response.status_code = 500
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# ------------------------------------------------------------------------------
# Replay parsing logic (using mgz.header + mgz.summary)
# ------------------------------------------------------------------------------
import re
from datetime import datetime

def extract_timestamp_from_filename(filename):
    """
    Extract timestamp from an AoE2 replay filename.
    Example: "MP Replay v101.103.2359.0 @2025.03.14 202116 (1).aoe2record"
    """
    match = re.search(r"@(\d{4}\.\d{2}\.\d{2}) (\d{6})", filename)
    if match:
        date_part, time_part = match.groups()
        formatted_date = date_part.replace(".", "-")  # Convert to YYYY-MM-DD
        formatted_time = f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}"  # Convert HHMMSS to HH:MM:SS
        try:
            return datetime.strptime(f"{formatted_date} {formatted_time}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return datetime.utcnow()  # Fallback if parsing fails
    return datetime.utcnow()  # Fallback if no timestamp found


def parse_replay(replay_path):
    """Parse a .aoe2record file using mgz.header + mgz.summary."""
    if not os.path.exists(replay_path):
        logging.error(f"❌ Replay not found: {replay_path}")
        return None

    try:
        with open(replay_path, "rb") as f:
            h = header.parse_stream(f)
            f.seek(0)
            match_summary = summary.Summary(f)

            duration_seconds = int(match_summary.get_duration() / 1000)
            game_type_str = str(match_summary.get_settings().get("type", "Unknown"))

            # ✅ Extract timestamp from filename
            match_start_time = extract_timestamp_from_filename(os.path.basename(replay_path))

            stats = {
                "replay_file": replay_path,
                "game_version": str(h.version),
                "map": {
                    "name": match_summary.get_map().get("name", "Unknown"),
                    "size": match_summary.get_map().get("size", "Unknown")
                },
                "game_type": game_type_str,
                "duration": duration_seconds,
                "players": [],
                "winner": "Unknown",
                "timestamp": match_start_time  # ✅ Correct match start time
            }

            for p in match_summary.get_players():
                player_info = {
                    "name": p.get("name", "Unknown"),
                    "civilization": p.get("civilization", "Unknown"),
                    "winner": p.get("winner", False),
                    "military_score": p.get("military", {}).get("score", 0),
                    "economy_score": p.get("economy", {}).get("score", 0),
                    "technology_score": p.get("technology", {}).get("score", 0),
                    "society_score": p.get("society", {}).get("score", 0),
                    "units_killed": p.get("military", {}).get("units_killed", 0),
                    "fastest_castle_age": p.get("technology", {}).get("fastest_castle_age", 0),
                }
                stats["players"].append(player_info)
                if player_info["winner"]:
                    stats["winner"] = player_info["name"]

            logging.info(f"✅ Parsed replay data successfully: {stats}")
            return stats

    except Exception as e:
        logging.error(f"❌ Error parsing replay: {e}", exc_info=True)
        return None



# ------------------------------------------------------------------------------
# POST /api/parse_replay
# ------------------------------------------------------------------------------
@app.route('/api/parse_replay', methods=['POST'])
def parse_new_replay():
    """Receive a JSON with "replay_file" path. Parse & store stats in DB."""
    data = request.json
    replay_path = data.get("replay_file")
    if not replay_path:
        return jsonify({"error": "Replay path missing"}), 400

    replay_path = str(pathlib.Path(replay_path).expanduser().resolve())

    existing = GameStats.query.filter_by(replay_file=replay_path).first()
    if existing:
        logging.info(f"⚠️ Replay already in DB: {replay_path}")
        return jsonify({"message": "Replay already in database."}), 200

    parsed_data = parse_replay(replay_path)
    if not parsed_data:
        return jsonify({"error": "Failed to parse replay"}), 500

    new_game = GameStats(
        replay_file=parsed_data["replay_file"],
        game_version=parsed_data["game_version"],
        map=json.dumps(parsed_data["map"]),
        game_type=parsed_data["game_type"],
        duration=parsed_data["duration"],
        winner=parsed_data["winner"],
        players=json.dumps(parsed_data["players"]),
        timestamp=parsed_data["timestamp"],  # ✅ Use actual match timestamp
    )

    db.session.add(new_game)
    try:
        db.session.commit()
    except Exception as e:
        logging.error(f"❌ DB Insert Error: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to insert replay into DB"}), 500

    return jsonify({"message": "Replay parsed and stored successfully!"}), 200


# ------------------------------------------------------------------------------
# GET /api/game_stats
# ------------------------------------------------------------------------------
@app.route('/api/game_stats', methods=['GET'])
def game_stats():
    """Return all stored game stats, newest first."""
    all_games = GameStats.query.order_by(GameStats.timestamp.desc()).all()
    results = []
    for game in all_games:
        # Convert map & players from JSON
        try:
            map_data = json.loads(game.map)
        except:
            map_data = game.map

        try:
            player_data = json.loads(game.players)
        except:
            player_data = []

        results.append({
            "id": game.id,
            "game_version": game.game_version,
            "map": map_data,
            "game_type": game.game_type,
            "duration": game.duration,
            "winner": game.winner,
            "players": player_data,
            "timestamp": str(game.timestamp)
        })

    return jsonify(results)

# ------------------------------------------------------------------------------
# Run the Flask app
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True, host="0.0.0.0", port=8002)
