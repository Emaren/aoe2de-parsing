from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

# Allow frontend to access the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For stricter security, use ["http://192.168.151.28:3001"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROCESSED_REPLAYS_FILE = "processed_replays.json"

def safe_load_json(file_path):
    """Safely loads JSON while handling potential corruption."""
    if not os.path.exists(file_path):
        return {"games": []}  # Ensure empty list instead of error

    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            if not data:
                return {"games": []}
            return parse_replay_data(data)
    except json.JSONDecodeError:
        return {"games": []}

def parse_replay_data(replays):
    """Extracts relevant game stats from parsed replays."""
    game_stats = []

    for replay_file, game_data in replays.items():
        game_entry = {
            "game_version": game_data.get("game_version", "Unknown"),
            "map_name": game_data.get("map", {}).get("name", "Unknown"),
            "map_size": game_data.get("map", {}).get("size", "Unknown"),
            "game_duration": game_data.get("duration", 0),
            "players": []
        }

        for player in game_data.get("players", []):
            player_stats = {
                "name": player.get("name", "Unknown"),
                "civilization": player.get("civilization", "Unknown"),
                "winner": player.get("winner", False),
                "military_score": player.get("military_score", 0),
                "economy_score": player.get("economy_score", 0),
                "technology_score": player.get("technology_score", 0),
                "society_score": player.get("society_score", 0),
                "units_killed": player.get("units_killed", 0),
                "buildings_destroyed": player.get("buildings_destroyed", 0),
                "resources_gathered": player.get("resources_gathered", 0),
                "fastest_castle_age": player.get("fastest_castle_age", 0),
                "fastest_imperial_age": player.get("fastest_imperial_age", 0),
                "relics_collected": player.get("relics_collected", 0),
            }
            game_entry["players"].append(player_stats)

        game_stats.append(game_entry)

    return {"games": game_stats}

@app.get("/api/game_stats")
def get_game_stats():
    """Retrieve and format game stats for the betting app."""
    return safe_load_json(PROCESSED_REPLAYS_FILE)

@app.get("/")
def root():
    return {"message": "AoE2 Betting Backend is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
