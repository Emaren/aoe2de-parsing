import os
import platform
import time
import logging
import json
import threading
import io
from watchdog.observers.polling import PollingObserver
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from mgz import header, summary
from config import load_config

# ✅ Load configuration from config.json
config = load_config()
config_dirs = config.get("replay_directories", None)
use_polling = config.get("use_polling", True)
polling_interval = config.get("polling_interval", 1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ✅ File to store processed replays
PROCESSED_REPLAYS_FILE = "processed_replays.json"
processed_replays = {}

def load_processed_replays():
    """Loads previously processed replays from JSON storage."""
    global processed_replays
    try:
        with open(PROCESSED_REPLAYS_FILE, "r") as f:
            processed_replays = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        processed_replays = {}

def save_processed_replays():
    """Saves processed replays to a JSON file."""
    with open(PROCESSED_REPLAYS_FILE, "w") as f:
        json.dump(processed_replays, f, indent=4)

def format_duration(seconds):
    """Convert game duration from raw value to 'Xh Ym Zs' format."""
    try:
        seconds = int(float(seconds))  # Convert from float
        if seconds > 86400:  # If more than 24 hours, it's likely in milliseconds
            seconds = seconds // 1000  # Convert ms to seconds

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours}h {minutes}m {seconds}s"
    except Exception as e:
        logging.error(f"❌ Error formatting duration: {e}")
        return "Unknown"



def parse_replay(file_path):
    """
    Parses an AoE2 DE replay file and extracts game stats.
    """
    try:
        with open(file_path, "rb") as f:
            replay_data = f.read()  # Read binary data

        # ✅ Parse header and summary
        h = header.parse(replay_data)
        match_summary = summary.Summary(io.BytesIO(replay_data))

        raw_duration = match_summary.get_duration()
        logging.debug(f"🕒 Raw duration from replay: {raw_duration} seconds")  # <== Debug log

        stats = {
            "game_version": str(h.version),
            "map": match_summary.get_map(),
            "game_type": str(match_summary.get_version()),
            "duration": format_duration(raw_duration),  # ✅ Fix duration
            "players": [
                {
                    "name": p.get("name", "Unknown"),
                    "civilization": p.get("civilization", "Unknown"),
                    "winner": p.get("winner", False),
                    "score": p.get("score", 0),
                }
                for p in match_summary.get_players()
            ]
        }

        processed_replays[file_path] = stats
        save_processed_replays()

        logging.info(f"✅ Parsed Replay: {file_path}")
        logging.info(f"📌 Game Version: {stats['game_version']}")
        logging.info(f"📌 Map: {stats['map']}")
        logging.info(f"📌 Duration: {stats['duration']}")
        logging.info(f"📌 Players: {stats['players']}")

    except Exception as e:
        logging.error(f"❌ Error parsing {file_path}: {e}")


def stream_replay_updates(replay_file):
    """Monitors and parses replay files on modification (for live updates)."""
    last_size = 0
    while True:
        try:
            current_size = os.path.getsize(replay_file)
            if current_size > last_size:
                logging.info(f"🔄 Processing replay update: {replay_file}")
                parse_replay(replay_file)
            last_size = current_size
        except Exception as e:
            logging.error(f"❌ Error streaming {replay_file}: {e}")
        time.sleep(5)  # Adjust polling interval as needed

class ReplayEventHandler(FileSystemEventHandler):
    """Handles new and modified replay files."""
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".aoe2record"):
            logging.info(f"🆕 New replay detected: {event.src_path}")
            processed_replays[event.src_path] = {}  # Mark as processing
            threading.Thread(target=stream_replay_updates, args=(event.src_path,), daemon=True).start()

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".aoe2record"):
            logging.info(f"✍️ Replay modified: {event.src_path}")
            threading.Thread(target=stream_replay_updates, args=(event.src_path,), daemon=True).start()

def get_possible_directories():
    """Auto-detect likely AoE2 replay directories based on OS."""
    dirs = []
    system = platform.system()
    home = os.path.expanduser("~")

    if system == "Windows":
        userprofile = os.environ.get("USERPROFILE", "")
        dirs += [
            os.path.join(userprofile, "Documents", "My Games", "Age of Empires 2 DE", "SaveGame"),
            os.path.join(userprofile, "AppData", "Local", "Packages",
                         "Microsoft.AgeofEmpiresII_8wekyb3d8bbwe", "LocalCache", "SaveGame"),
            r"C:\GOG Games\Age of Empires II DE\SaveGame",
            r"C:\Age of Empires 2 DE\SaveGame",
            r"D:\Games\Age of Empires II DE\SaveGame"
        ]
    elif system == "Darwin":  # macOS
        dirs += [
            os.path.join(home, "Documents", "My Games", "Age of Empires 2 DE", "SaveGame"),
            os.path.join(home, "Library", "Application Support", "CrossOver", "Bottles", "AoE2DE", "SaveGame"),
            os.path.join(home, "Parallels", "AoE2DE", "SaveGame"),
            os.path.join(home, "Games", "AoE2DE", "SaveGame")
        ]
        steam_base = os.path.join(home, "Library", "Application Support", "CrossOver", "Bottles", "Steam", "drive_c",
                                  "users", "crossover", "Games", "Age of Empires 2 DE")
        if os.path.isdir(steam_base):
            for subdir in os.listdir(steam_base):
                candidate = os.path.join(steam_base, subdir, "SaveGame")
                if os.path.isdir(candidate):
                    dirs.append(candidate)
    elif system == "Linux":
        dirs += [
            os.path.join(home, ".wine", "drive_c", "Program Files (x86)", "Microsoft Games",
                         "Age of Empires II DE", "SaveGame"),
            os.path.join(home, ".wine", "drive_c", "Program Files", "Age of Empires II DE", "SaveGame"),
            os.path.join(home, "Documents", "My Games", "Age of Empires 2 DE", "SaveGame")
        ]
    return [d for d in dirs if os.path.isdir(d)]

# ✅ Determine directories to watch
if config_dirs:
    possible_dirs = config_dirs
else:
    possible_dirs = get_possible_directories()

def watch_replay_directories(directories, use_polling=True, interval=1):
    """Watches AoE2 DE replay directories for new game files."""
    load_processed_replays()
    observer = PollingObserver() if use_polling else Observer()

    for directory in directories:
        if os.path.exists(directory):
            logging.info(f"👀 Watching directory: {directory}")
            observer.schedule(ReplayEventHandler(), directory, recursive=False)
        else:
            logging.warning(f"⚠️ Directory not found: {directory}")

    observer.start()
    try:
        while True:
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("🛑 Stopping watcher.")
        observer.stop()
    observer.join()

if __name__ == '__main__':
    logging.info("📌 Possible directories to watch:")
    for d in possible_dirs:
        logging.info(f"  📂 {d}")
    watch_replay_directories(possible_dirs, use_polling=use_polling, interval=polling_interval)
