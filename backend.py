import json
from fastapi import FastAPI, HTTPException, Request
from flask import Flask, request as flask_request, jsonify
from pydantic import BaseModel
import uvicorn
import threading
import sqlite3

# FastAPI App
fastapi_app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

# Add CORS Middleware to FastAPI
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change to specific domain in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Flask App (For compatibility)
flask_app = Flask(__name__)

# In-memory storage for bets
bets = {}

# Bet Model using Pydantic
class Bet(BaseModel):
    match_id: str
    player_1: str
    player_2: str
    amount: float
    accepted: bool = False
    winner: str = None  # Will be filled when replay is uploaded

@fastapi_app.post("/bets/create")
def create_bet(bet: Bet):
    if bet.match_id in bets:
        raise HTTPException(status_code=400, detail="Match ID already exists.")
    
    bets[bet.match_id] = bet.dict()
    return {"message": "Bet created!", "bet_id": bet.match_id}

@fastapi_app.post("/bets/accept/{match_id}")
def accept_bet(match_id: str):
    if match_id not in bets:
        raise HTTPException(status_code=404, detail="Bet not found.")
    
    bets[match_id]["accepted"] = True
    return {"message": "Bet accepted!", "bet": bets[match_id]}

@fastapi_app.get("/bets/pending")
def get_pending_bets():
    return [bet for bet in bets.values() if not bet["accepted"]]

@fastapi_app.post("/replay/upload/{match_id}")
async def upload_replay(match_id: str, request: Request):
    data = await request.json()
    winner = data.get("winner")

    if match_id not in bets:
        raise HTTPException(status_code=404, detail="Bet not found.")

    if bets[match_id]["winner"]:
        raise HTTPException(status_code=400, detail="Bet already settled.")

    bets[match_id]["winner"] = winner
    return {"message": f"Bet settled! {winner} won the bet."}

@fastapi_app.get("/")
def root():
    return {"message": "AoE2 Betting Backend is running!"}

fastapi_app = FastAPI()

@fastapi_app.get("/api/game_stats")
def get_game_stats():
    try:
        conn = sqlite3.connect("game_stats.db")
        cursor = conn.cursor()

        # Fetch the latest game first
        cursor.execute("SELECT id, replay_file, game_version, map, game_type, duration, winner, players, timestamp FROM game_stats ORDER BY timestamp DESC LIMIT 10")
        rows = cursor.fetchall()
        conn.close()

        # Format the response properly
        games = [
            {
                "id": row[0],
                "replay_file": row[1],
                "game_version": row[2],
                "map_name": row[3],
                "game_type": row[4],
                "game_duration": f"{row[5] // 60} minutes {row[5] % 60} seconds",
                "winner": row[6],
                "players": json.loads(row[7]) if row[7] and row[7] != "[]" else [{"name": "Unknown", "civilization": "Unknown"}],
                "timestamp": row[8]  # ✅ Include timestamp to verify sorting
            }
            for row in rows
        ]

        return {"games": games}

    except Exception as e:
        return {"error": str(e)}

# Flask Endpoint for Receiving Replays
@flask_app.route('/api/replays', methods=['POST'])
def receive_replay():
    data = flask_request.get_json()
    print("Received replay stats:")
    print(data)
    return jsonify({"status": "success", "message": "Data received"}), 200

# Flask Home Endpoint
@flask_app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Flask API for AoE2 Betting is running!"})

# Function to run Flask in a separate thread
def run_flask():
    flask_app.run(host="0.0.0.0", port=5001, debug=True, use_reloader=False)

# Run Flask in a thread when FastAPI starts
if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, reload=True)
