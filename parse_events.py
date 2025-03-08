import os
from mgz.summary import Summary
from mgz import fast

REPLAY_FILE = "/Users/tonyblum/Library/Application Support/CrossOver/Bottles/Steam/drive_c/users/crossover/Games/Age of Empires 2 DE/76561198065420384/SaveGame/MP Replay v101.103.2359.0 @2025.02.25 125841 (2).aoe2record"

if not os.path.exists(REPLAY_FILE):
    print(f"❌ Error: Replay file not found at {REPLAY_FILE}")
    exit()

# ✅ Step 1: Parse Replay Metadata
try:
    with open(REPLAY_FILE, "rb") as f:
        summary = Summary(f)
        print("✅ Replay metadata parsed successfully!")
except Exception as e:
    print(f"❌ Error parsing replay metadata: {e}")
    exit()

# ✅ Step 2: Extract Actions
event_types = set()
key_events = []

try:
    with open(REPLAY_FILE, "rb") as f:
        for action in fast.parse_stream(f):
            print(f"🔍 Raw Action Data: {action}")  # Debugging all actions
            
            if isinstance(action, dict):
                op = action.get("op", "Unknown")
                event_types.add(op)

                if op in ["kill", "relic_captured", "wonder_started", "wonder_completed"]:
                    key_events.append(action)

except Exception as e:
    print(f"❌ Error extracting actions: {e}")
    exit()

# ✅ Step 3: Print Extracted Events
print(f"\n🔹 Unique Event Types Found: {event_types}")

if key_events:
    print("\n🔹 Extracted Key Events:")
    for event in key_events:
        print(event)
else:
    print("⚠️ No key events found.")
