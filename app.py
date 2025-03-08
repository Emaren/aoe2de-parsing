from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import io
import logging
import json
import pathlib
from mgz import header, summary

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'game_stats.db')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# -------------------------------------------------------------------------
# Make replay_file unique to avoid duplicates. If you still see duplicates,
# see the notes below on how to fix existing data or path mismatches.
# -------------------------------------------------------------------------
class GameStats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    replay_file = db.Column(db.String(500), unique=True, nullable=False)  # UNIQUE
    game_version = db.Column(db.String(50))
    map = db.Column(db.String(100))  
    game_type = db.Column(db.String(50))
    duration = db.Column(db.Integer)
    winner = db.Column(db.String(100))
    players = db.Column(db.Text)     # JSON
    event_types = db.Column(db.Text) # JSON
    key_events = db.Column(db.Text)  # JSON
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

with app.app_context():
    db.create_all()

def parse_replay(replay_path):
    """Parse an AoE2 replay file, adjusting durations above 20 hours as milliseconds."""
    stats = {}
    if not os.path.exists(replay_path):
        logging.error(f"❌ Replay not found: {replay_path}")
        return None

    try:
        with open(replay_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        logging.error(f"❌ Error reading: {e}")
        return None

    try:
        h = header.parse(file_bytes)
        stats["game_version"] = str(h.version)
    except Exception as e:
        logging.error(f"❌ Error parsing header: {e}")
        return None

    try:
        match_summary = summary.Summary(io.BytesIO(file_bytes))
        raw_map_data = match_summary.get_map()
        stats["map"] = {
            "name": raw_map_data.get("name", "Unknown"),
            "size": raw_map_data.get("size", "Unknown"),
        }
        stats["game_type"] = str(match_summary.get_version())

        raw_duration = match_summary.get_duration()
        # If game is over 20 hours => treat as ms
        TWENTY_HOURS = 20 * 3600  # 72,000 seconds
        if raw_duration > TWENTY_HOURS:
            raw_duration //= 1000
        
        stats["duration"] = int(raw_duration)

        players = []
        winner = None
        for p in match_summary.get_players():
            player_data = {
                "name": p.get("name", "Unknown"),
                "civilization": p.get("civilization", "Unknown"),
                "winner": p.get("winner", False),
                "score": p.get("score", 0),
                "military_score": p.get("military", {}).get("score", 0),
                "economy_score": p.get("economy", {}).get("score", 0),
                "technology_score": p.get("technology", {}).get("score", 0),
                "society_score": p.get("society", {}).get("score", 0),
                "units_killed": p.get("military", {}).get("units_killed", 0),
                "fastest_castle_age": p.get("technology", {}).get("fastest_castle_age", 0),
            }
            players.append(player_data)
            if player_data["winner"]:
                winner = player_data["name"]
        stats["players"] = players
        stats["winner"] = winner if winner else "Unknown"

    except Exception as e:
        logging.error(f"❌ Error extracting summary: {e}")
        return None

    stats["replay_file"] = replay_path
    logging.info(f"✅ Parsed replay data: {stats}")
    return stats

@app.route('/api/parse_replay', methods=['POST'])
def parse_new_replay():
    data = request.json
    replay_path = data.get("replay_file")
    if not replay_path:
        return jsonify({"error": "Replay path missing"}), 400

    replay_path = str(pathlib.Path(replay_path).expanduser().resolve())
    
    # Check if already in DB
    existing = GameStats.query.filter_by(replay_file=replay_path).first()
    if existing:
        logging.info(f"⚠️ Replay already exists in DB, skipping: {replay_path}")
        return jsonify({"message": "Replay already in database."}), 200
    
    if not os.path.exists(replay_path):
        return jsonify({"error": f"Replay not found: {replay_path}"}), 400

    parsed_data = parse_replay(replay_path)
    if not parsed_data:
        return jsonify({"error": "Failed to parse replay"}), 500

    map_json = json.dumps(parsed_data["map"])
    new_game = GameStats(
        replay_file=parsed_data["replay_file"],
        game_version=parsed_data["game_version"],
        map=map_json,
        game_type=parsed_data["game_type"],
        duration=parsed_data["duration"],
        winner=parsed_data["winner"],
        players=json.dumps(parsed_data["players"]),
        event_types="[]",
        key_events="[]"
    )

    db.session.add(new_game)
    try:
        db.session.commit()
    except Exception as e:
        logging.error(f"❌ DB Insert Error: {e}")
        return jsonify({"error": "Failed to insert replay into DB"}), 500

    return jsonify({"message": "Replay parsed and stored successfully!"})

@app.route('/api/game_stats', methods=['GET'])
def game_stats():
    """Returns all games, newest first."""
    all_games = GameStats.query.order_by(GameStats.timestamp.desc()).all()
    results = []
    for game in all_games:
        map_data = json.loads(game.map) if game.map else {}
        players_data = json.loads(game.players) if game.players else []
        event_types = json.loads(game.event_types) if game.event_types else []
        key_events = json.loads(game.key_events) if game.key_events else []
        results.append({
            "id": game.id,
            "game_version": game.game_version,
            "map": map_data,
            "game_type": game.game_type,
            "duration": game.duration,
            "winner": game.winner,
            "players": players_data,
            "event_types": event_types,
            "key_events": key_events,
            "timestamp": str(game.timestamp)
        })
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=8002)
