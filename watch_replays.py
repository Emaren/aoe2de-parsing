import os
import platform
import time
import logging
from watchdog.observers.polling import PollingObserver  # For maximum compatibility
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from parse_replay import parse_replay
from config import load_config

# Load configuration from config.json
config = load_config()
# Use directories from config if provided; otherwise, auto-discover them
config_dirs = config.get("replay_directories", None)
use_polling = config.get("use_polling", True)
polling_interval = config.get("polling_interval", 1)
# Optionally, you can adjust logging level from config if desired:
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class ReplayEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".aoe2record"):
            logging.info(f"Replay created: {event.src_path}")
            parse_replay(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".aoe2record"):
            logging.info(f"Replay modified: {event.src_path}")
            parse_replay(event.src_path)


def get_possible_directories():
    """
    Build a list of likely AoE2 replay directories based on the current OS.
    This avoids hardcoding a specific user's Steam ID by using environment variables
    and scanning parent directories where appropriate.
    """
    dirs = []
    system = platform.system()
    home = os.path.expanduser("~")
    
    if system == "Windows":
        userprofile = os.environ.get("USERPROFILE", "")
        dirs.append(os.path.join(userprofile, "Documents", "My Games", "Age of Empires 2 DE", "SaveGame"))
        dirs.append(os.path.join(userprofile, "AppData", "Local", "Packages",
                                 "Microsoft.AgeofEmpiresII_8wekyb3d8bbwe", "LocalCache", "SaveGame"))
        dirs.append(r"C:\GOG Games\Age of Empires II DE\SaveGame")
        dirs.append(r"C:\Age of Empires 2 DE\SaveGame")
        dirs.append(r"D:\Games\Age of Empires II DE\SaveGame")
    elif system == "Darwin":  # macOS
        docs_path = os.path.join(home, "Documents", "My Games", "Age of Empires 2 DE", "SaveGame")
        if os.path.isdir(docs_path):
            dirs.append(docs_path)
        crossover_path = os.path.join(home, "Library", "Application Support", "CrossOver", "Bottles", "AoE2DE", "SaveGame")
        if os.path.isdir(crossover_path):
            dirs.append(crossover_path)
        # Scan the parent folder for CrossOver Steam installations
        steam_base = os.path.join(home, "Library", "Application Support", "CrossOver", "Bottles", "Steam", "drive_c",
                                  "users", "crossover", "Games", "Age of Empires 2 DE")
        if os.path.isdir(steam_base):
            for subdir in os.listdir(steam_base):
                candidate = os.path.join(steam_base, subdir, "SaveGame")
                if os.path.isdir(candidate):
                    dirs.append(candidate)
        parallels_path = os.path.join(home, "Parallels", "AoE2DE", "SaveGame")
        if os.path.isdir(parallels_path):
            dirs.append(parallels_path)
        custom_path = os.path.join(home, "Games", "AoE2DE", "SaveGame")
        if os.path.isdir(custom_path):
            dirs.append(custom_path)
    elif system == "Linux":
        dirs.append(os.path.join(home, ".wine", "drive_c", "Program Files (x86)", "Microsoft Games",
                                 "Age of Empires II DE", "SaveGame"))
        dirs.append(os.path.join(home, ".wine", "drive_c", "Program Files", "Age of Empires II DE", "SaveGame"))
        docs_linux = os.path.join(home, "Documents", "My Games", "Age of Empires 2 DE", "SaveGame")
        if os.path.isdir(docs_linux):
            dirs.append(docs_linux)
    return dirs

# Use config directories if provided; otherwise, auto-discover
if config_dirs:
    possible_dirs = config_dirs
else:
    possible_dirs = get_possible_directories()


def watch_replay_directories(directories, use_polling=True, interval=1):
    observer = PollingObserver() if use_polling else Observer()
    for directory in directories:
        if os.path.exists(directory):
            logging.info(f"Watching directory: {directory}")
            observer.schedule(ReplayEventHandler(), directory, recursive=False)
        else:
            logging.warning(f"Directory not found: {directory}")
    observer.start()
    try:
        while True:
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("Stopping watcher.")
        observer.stop()
    observer.join()


if __name__ == '__main__':
    logging.info("Possible directories to watch:")
    for d in possible_dirs:
        logging.info(f"  {d}")
    watch_replay_directories(possible_dirs, use_polling=use_polling, interval=polling_interval)
