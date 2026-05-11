"""
checkpoint.py — Save and load progress so the scraper can resume after interruption.
"""

import os
import json

CHECKPOINT_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "checkpoint.json"
)


def load_checkpoint() -> set:
    """Return a set of completed job keys (tehsil::entity)."""
    if not os.path.exists(CHECKPOINT_FILE):
        return set()
    try:
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
        return set(data.get("completed", []))
    except Exception:
        return set()


def save_checkpoint(job_key: str):
    """Mark a job key as completed."""
    completed = load_checkpoint()
    completed.add(job_key)
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump({"completed": list(completed)}, f, indent=2)


def reset_checkpoint():
    """Clear all checkpoints to start fresh."""
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)
    print("Checkpoint reset.")
