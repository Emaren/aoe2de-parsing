import requests
import os
import platform
import time
import logging
import json
import threading
from queue import Queue
from watchdog.observers.polling import PollingObserver
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import load_config

# ---------------------------------------------------------------------------------------
# LOAD CONFIG & SETUP
# ---------------------------------------------------------------------------------------
config = load_config()
config_dirs = config.get("replay_directories", None)
use_polling = config.get("use_polling", True)
polling_interval = config.get("polling_interval", 1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# We track which replays we've already processed to avoid duplicates
PROCESSED_REPLAYS_FILE = "processed_replays.json"
processed_replays = {}

# AoE2 HD & DE default directories (macOS example shown; adapt if needed)
AOE2HD_REPLAY_DIR = (
    "/Users/tonyblum/Library/Application Support/CrossOver/Bottles/Steam/drive_c/"
    "Program Files (x86)/Steam/steamapps/common/Age2HD/SaveGame/multi"
)
AOE2DE_REPLAY_DIR = os.path.expanduser("~/Documents/My Games/Age of Empires 2 DE/SaveGame")

# ---------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------------------
def load_processed_replays():
    """Load JSON of previously processed replays into a global dict."""
    global processed_replays
    try:
        with open(PROCESSED_REPLAYS_FILE, "r") as f:
            processed_replays = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        processed_replays = {}

def save_processed_replays():
    """Persist the global processed_replays dict to JSON."""
    with open(PROCESSED_REPLAYS_FILE, "w") as f:
        json.dump(processed_replays, f, indent=4)

def parse_replay(file_path):
    """
    Call the parse_replay API endpoint to parse & store the replay in the DB.
    Mark the file as processed on success or error (so we don't retry infinitely).
    """
    if file_path in processed_replays:
        logging.info(f"⚠️ Replay already processed: {file_path}")
        return

    logging.info(f"✅ Attempting to parse new replay: {file_path}")

    api_url = "http://localhost:8002/api/parse_replay"
    try:
        # Extended timeout to handle large/slow parse
        response = requests.post(api_url, json={"replay_file": file_path}, timeout=120)
        if response.status_code == 200:
            logging.info(f"✅ Successfully parsed and stored replay: {file_path}")
        else:
            logging.error(f"❌ API Error ({response.status_code}): {response.json()}")
    except Exception as e:
        logging.error(f"❌ Error calling parse endpoint for {file_path}: {e}")

    # Mark as processed to avoid repeated attempts
    processed_replays[file_path] = {"status": "processed"}
    save_processed_replays()

def wait_for_stable_file(file_path, stable_seconds=30, verification_seconds=20):
    """
    Ensures the file is stable by checking twice before parsing.
    """
    last_size = -1
    stable_time = 0
    check_interval = 1

    # First Stability Check
    while stable_time < stable_seconds:
        if not os.path.exists(file_path):
            logging.warning(f"⚠️ File disappeared before parsing: {file_path}")
            return

        current_size = os.path.getsize(file_path)
        if current_size == last_size:
            stable_time += check_interval
        else:
            stable_time = 0
            last_size = current_size = os.path.getsize(file_path)

        time.sleep(check_interval)

    logging.info(f"🕒 Initial stability detected for file: {file_path}. Verifying again...")

    # Verification Phase
    time.sleep(20)  # Wait extra time for certainty
    new_size = os.path.getsize(file_path)
    if new_size == last_size:
        logging.info(f"✅ File confirmed stable, parsing now: {file_path}")
        parse_replay(file_path)
    else:
        logging.warning(f"⚠️ File size changed after verification. Restarting stability check.")
        wait_for_stable_file(file_path, stable_seconds)

# ---------------------------------------------------------------------------------------
# SINGLE-THREADED QUEUE TO LIMIT CONCURRENCY
# ---------------------------------------------------------------------------------------
# We use a single background worker thread that processes tasks in FIFO order,
# ensuring only one parse is done at a time.
parse_queue = Queue()

def parse_worker():
    """Thread worker that processes stable-file tasks one by one."""
    while True:
        file_path = parse_queue.get()
        if file_path is None:  # Stop signal
            break
        wait_for_stable_file(file_path, stable_seconds=60)
        parse_queue.task_done()

# Start the parse worker in the background
worker_thread = threading.Thread(target=parse_worker, daemon=True)
worker_thread.start()

# ---------------------------------------------------------------------------------------
# WATCHDOG EVENT HANDLER
# ---------------------------------------------------------------------------------------
import re

class ReplayEventHandler(FileSystemEventHandler):
    FINAL_REPLAY_REGEX = re.compile(r"MP Replay v.* @\d{4}\.\d{2}\.\d{2} \d{6}\.aoe2record$")

    def on_created(self, event):
        if event.is_directory:
            return
        filename = os.path.basename(event.src_path)
        if self.FINAL_REPLAY_REGEX.match(filename):
            logging.info(f"🆕 Final Replay Detected: {event.src_path}")
            parse_queue.put(event.src_path)
        else:
            logging.info(f"⏳ Ignoring temporary file: {event.src_path}")

    # If you really want to parse on each modification, uncomment below:
    # def on_modified(self, event):
    #     if event.is_directory:
    #         return
    #     if event.src_path.endswith(".aoe2record") or event.src_path.endswith(".aoe2mpgame"):
    #         logging.info(f"✍️ Replay Modified: {event.src_path}")
    #         parse_queue.put(event.src_path)

# ---------------------------------------------------------------------------------------
# AUTO-DETECT POTENTIAL DIRECTORIES
# ---------------------------------------------------------------------------------------
def get_possible_directories():
    """Auto-detect likely AoE2 replay directories based on OS."""
    dirs = []
    system = platform.system()
    home = os.path.expanduser("~")

    if system == "Windows":
        userprofile = os.environ.get("USERPROFILE", "")
        dirs += [
            os.path.join(userprofile, "Documents", "My Games", "Age of Empires 2 HD", "SaveGame"),
            os.path.join(userprofile, "Documents", "My Games", "Age of Empires 2 DE", "SaveGame"),
            r"C:\GOG Games\Age of Empires II HD\SaveGame",
            r"C:\Age of Empires 2 HD\SaveGame",
            r"D:\Games\Age of Empires II HD\SaveGame",
        ]
    elif system == "Darwin":  # macOS
        dirs.append(AOE2HD_REPLAY_DIR)
        dirs.append(AOE2DE_REPLAY_DIR)
    elif system == "Linux":
        dirs += [
            os.path.join(home, ".wine", "drive_c", "Program Files (x86)", "Microsoft Games",
                         "Age of Empires II HD", "SaveGame"),
            os.path.join(home, ".wine", "drive_c", "Program Files", "Age of Empires II HD", "SaveGame"),
            os.path.join(home, "Documents", "My Games", "Age of Empires 2 HD", "SaveGame"),
            os.path.join(home, "Documents", "My Games", "Age of Empires 2 DE", "SaveGame"),
        ]

    return [d for d in dirs if os.path.isdir(d)]

# ---------------------------------------------------------------------------------------
# MAIN WATCH FUNCTION
# ---------------------------------------------------------------------------------------
def watch_replay_directories(directories, use_polling=True, interval=1):
    """
    Watches AoE2 HD & DE replay directories for new game files.
    On creation of an .aoe2record, we queue a parse task to the parse_worker thread.
    """
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

# ---------------------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------------------
if __name__ == '__main__':
    logging.info("📌 Watching AoE2 HD & DE Replay Directories...")

    if config_dirs:
        possible_dirs = config_dirs
    else:
        possible_dirs = get_possible_directories()

    watch_replay_directories(possible_dirs, use_polling=use_polling, interval=polling_interval)

    # If the script is interrupted, gracefully stop the parse queue:
    parse_queue.put(None)
    worker_thread.join()
