import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise RuntimeError(f"Configuration file not found at {CONFIG_FILE}. Please ensure config.json is present.")
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        return config
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {e}")

if __name__ == "__main__":
    config = load_config()
    print(json.dumps(config, indent=2))
