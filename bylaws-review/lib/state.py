import hashlib
import json
import os

STATE_PATH = os.path.join(os.path.dirname(__file__), "..", "state.json")


def row_hash(row):
    key = f"{row['timestamp']}|{row['email']}|{row['comment']}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def load_state(path=STATE_PATH):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state, path=STATE_PATH):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")
