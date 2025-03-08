import os
import io
import json
import logging
import requests
from mgz import header, summary
from mgz.fast.actions import parse_action_71094  # Correct action parser

# Configure Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FLASK_API_URL = "http://localhost:8002/api/parse_replay"

def format_duration(seconds):
    """
    Converts duration from seconds to 'X hours Y minutes' or
    'X hours Y minutes Z seconds', etc. for user-friendly display.
    """
    minutes = seconds // 60
    hours = minutes // 60
    minutes %= 60
    secs = seconds % 60

    if hours > 0 and minutes > 0 and secs > 0:
        return f"{hours} hours {minutes} minutes {secs} seconds"
    elif hours > 0 and minutes > 0:
        return f"{hours} hours {minutes} minutes"
    elif hours > 0:
        return f"{hours} hours"
    elif minutes > 0 and secs > 0:
        return f"{minutes} minutes {secs} seconds"
    elif minutes > 0:
        return f"{minutes} minutes"
    else:
        return f"{secs} seconds"

def parse_replay(replay_path):
    """
    Parses an AoE2 replay file and extracts game stats plus key actions,
    returning a dictionary containing all relevant fields.
    """
    stats = {"replay_file": os.path.basename(replay_path)}

    if not os.path.exists(replay_path):
        logging.error(f"❌ Replay file not found: {replay_path}")
        return None

    try:
        with open(replay_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        logging.error(f"❌ Error reading replay file: {e}")
        return None

    # Step 1: Parse Header (Game Version)
    try:
        with io.BytesIO(file_bytes) as f:
            h = header.parse_stream(f)
            stats["game_version"] = str(h.version)
            logging.info(f"✅ Parsed Game Version: {stats['game_version']}")
    except Exception as e:
        logging.error(f"❌ Error parsing header: {e}")
        return None

    # Step 2: Extract Match Summary (map info, players, duration, etc.)
    try:
        with io.BytesIO(file_bytes) as f:
            match_summary = summary.Summary(f)
            raw_duration = match_summary.get_duration()

            # If the duration is huge (e.g. > 48 hours), assume it's milliseconds
            if raw_duration > 48 * 3600:
                raw_duration = raw_duration // 1000

            # Store both numeric duration (for DB) and formatted string
            stats["duration"] = int(raw_duration)
            stats["game_duration"] = format_duration(raw_duration)

            # Map info
            raw_map_data = match_summary.get_map()
            stats["map_name"] = raw_map_data.get("name", "Unknown")
            stats["map_size"] = raw_map_data.get("size", "Unknown")

            # Game type info
            stats["game_type"] = str(match_summary.get_version())

            players = []
            winner = None

            for p in match_summary.get_players():
                player_name = p.get("name", "").strip() or "Unknown"
                civilization = p.get("civilization", "Unknown")

                player_data = {
                    "name": player_name,
                    "civilization": civilization,
                    "winner": p.get("winner", False),
                    "team": p.get("team", "Unknown"),
                    "score": p.get("score", 0),
                    "apm": p.get("apm", 0),
                    "military_score": p.get("military", {}).get("score", 0),
                    "economy_score": p.get("economy", {}).get("score", 0),
                    "technology_score": p.get("technology", {}).get("score", 0),
                    "society_score": p.get("society", {}).get("score", 0),
                    "units_killed": p.get("military", {}).get("units_killed", 0),
                    "buildings_destroyed": p.get("military", {}).get("buildings_destroyed", 0),
                    "resources_gathered": p.get("economy", {}).get("resources_gathered", 0),
                    "fastest_castle_age": p.get("technology", {}).get("fastest_castle_age", 0),
                    "fastest_imperial_age": p.get("technology", {}).get("fastest_imperial_age", 0),
                    "relics_collected": p.get("economy", {}).get("relics_collected", 0),
                }

                # Avoid adding placeholder
                if player_name != "Unknown" and civilization != "Unknown":
                    players.append(player_data)

                if player_data["winner"]:
                    winner = player_name

            stats["players"] = players
            stats["winner"] = winner if winner else "Unknown"

            logging.info(f"✅ Parsed {len(players)} players.")
    except Exception as e:
        logging.error(f"❌ Error extracting match summary: {e}")
        return None

    # Step 3: Extract Actions (Key Events)
    event_types = set()
    key_events = []

    try:
        with io.BytesIO(file_bytes) as f:
            while True:
                try:
                    action = parse_action_71094(f)
                    if not action:
                        break
                    op = getattr(action, "operation", "Unknown")
                    event_types.add(op)

                    # Track significant events
                    if any(k in op.lower() for k in ["kill", "destroy", "capture", "wonder"]):
                        key_events.append({
                            "type": op,
                            "timestamp": getattr(action, "timestamp", 0),
                        })
                except Exception:
                    break

        stats["unique_event_types"] = list(event_types)
        stats["key_events"] = key_events
        logging.info(f"✅ Extracted {len(key_events)} key events.")
    except Exception as e:
        logging.error(f"❌ Error extracting actions: {e}")
        stats["unique_event_types"] = []
        stats["key_events"] = []

    # Dump extracted data for debugging
    debug_output_path = f"{replay_path}.json"
    try:
        with open(debug_output_path, "w") as debug_file:
            json.dump(stats, debug_file, indent=4)
        logging.info(f"🔍 Dumped parsed data to {debug_output_path}")
    except Exception as e:
        logging.error(f"❌ Error writing debug JSON file: {e}")

    return stats

def send_to_api(parsed_data):
    """
    Sends parsed replay data to the Flask API so it can be stored in the DB.
    The Flask endpoint expects a JSON key 'replay_file' with the *absolute path*.
    """
    if "replay_file" not in parsed_data or not parsed_data["replay_file"]:
        logging.error("❌ API Error: Replay file name missing from request payload.")
        return

    try:
        logging.info(f"📤 Sending data to API: {json.dumps(parsed_data, indent=2)}")
        response = requests.post(FLASK_API_URL, json=parsed_data)
        logging.info(f"API Response: {response.status_code} - {response.text}")

        if response.status_code == 200:
            logging.info(f"✅ Successfully sent replay to API: {parsed_data['replay_file']}")
        else:
            logging.error(f"❌ API Error: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"❌ Failed to send replay to API: {e}")

if __name__ == "__main__":
    SAVEGAME_DIR = (
        "/Users/tonyblum/Library/Application Support/CrossOver/Bottles/Steam/"
        "drive_c/users/crossover/Games/Age of Empires 2 DE/76561198065420384/savegame"
    )

    for replay_file in os.listdir(SAVEGAME_DIR):
        if replay_file.endswith(".aoe2record"):
            replay_path = os.path.join(SAVEGAME_DIR, replay_file)
            parsed_data = parse_replay(replay_path)
            if parsed_data:
                # Overwrite the short name with the absolute path
                parsed_data["replay_file"] = replay_path
                # Send the data to your Flask API
                send_to_api(parsed_data)
