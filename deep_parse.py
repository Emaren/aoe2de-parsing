import logging
import sys
from mgz import header, summary

# Increase the verbosity of logs
logging.basicConfig(level=logging.DEBUG)

def deep_parse(replay_path):
    """
    Attempt a step-by-step parse of the replay with debug logging.
    """
    try:
        logging.debug(f"--- Opening file: {replay_path} ---")

        with open(replay_path, "rb") as f:
            logging.debug("Parsing replay header...")
            h = header.parse_stream(f)  # mgz tries to read the replay header

            # Show basic header info
            logging.debug(f"Header parse complete. Version: {h.version}")

            # Now, reset file pointer and parse the summary
            f.seek(0)
            logging.debug("Parsing replay summary...")
            s = summary.Summary(f)

            # If we get here without an exception, mgz recognized the structure
            logging.debug("Summary parse complete.")

            # Print out a couple of fields
            print(f"Replay version: {h.version}")
            print(f"Match duration: {s.get_duration()}")
            print("Players:")
            for p in s.get_players():
                print(f"  - {p['name']} (civ: {p['civilization']}), winner: {p['winner']}")

    except Exception as e:
        logging.error(f"Parsing failed with error: {e}", exc_info=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deep_parse.py /path/to/replay.aoe2record")
        sys.exit(1)

    replay_file = sys.argv[1]
    deep_parse(replay_file)
