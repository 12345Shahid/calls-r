#!/usr/bin/env python3
"""
Phone Line Manager (phone_lines.py)
Central configuration and state management for the 3-number rotation system.
Tracks line states (available, in_call, cooling_down) and provides round-robin selection.

Usage:
    from phone_lines import get_next_available_line, mark_line_busy, mark_line_available, is_our_number
"""
import os
import json
import time
import logging
from threading import Lock

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

LINES_PATH = os.path.join(os.path.dirname(__file__), "phone_lines.json")

# File-based line state tracking to share states across dialer and agent worker processes
STATES_PATH = os.path.join(os.path.dirname(__file__), "phone_line_states.json")
_line_states = {}  # Kept for compatibility with test suites and external references
_last_used_index = -1  # For round-robin rotation
_state_lock = Lock()
_config_cache = None
_config_mtime = 0


def _load_states() -> dict:
    """Loads line states from phone_line_states.json, populating _line_states."""
    global _line_states
    if not os.path.exists(STATES_PATH):
        _line_states.clear()
        return _line_states
    try:
        with open(STATES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            _line_states.clear()
            _line_states.update(data)
            return _line_states
    except Exception:
        return _line_states


def _save_states(states: dict):
    """Saves line states to phone_line_states.json."""
    try:
        with open(STATES_PATH, "w", encoding="utf-8") as f:
            json.dump(states, f, indent=2)
    except Exception as e:
        logging.error(f"❌ Failed to save line states: {e}")


def _load_config(force_reload: bool = False) -> dict:
    """Loads phone lines configuration from phone_lines.json."""
    global _config_cache, _config_mtime

    if not os.path.exists(LINES_PATH):
        logging.error(f"❌ Phone lines config not found: {LINES_PATH}")
        return {"lines": []}

    mtime = os.path.getmtime(LINES_PATH)
    if _config_cache and mtime == _config_mtime and not force_reload:
        return _config_cache

    try:
        with open(LINES_PATH, "r", encoding="utf-8") as f:
            _config_cache = json.load(f)
            _config_mtime = mtime
            return _config_cache
    except Exception as e:
        logging.error(f"❌ Failed to load phone lines config: {e}")
        return {"lines": []}


def get_all_lines() -> list[dict]:
    """Returns all configured phone lines."""
    config = _load_config()
    return config.get("lines", [])


def _get_line_state(line_id: str) -> dict:
    """Gets the current state of a line from persistent storage."""
    states = _load_states()
    if line_id not in states:
        states[line_id] = {"status": "available", "busy_since": None, "cool_until": None}
    return states[line_id]


def _is_line_available(line_id: str) -> bool:
    """Checks if a line is currently available (not busy, not cooling)."""
    states = _load_states()
    if line_id not in states:
        states[line_id] = {"status": "available", "busy_since": None, "cool_until": None}
    state = states[line_id]

    if state["status"] == "in_call":
        return False

    if state["status"] == "cooling_down":
        cool_until = state.get("cool_until", 0)
        if time.time() >= cool_until:
            state["status"] = "available"
            state["cool_until"] = None
            _save_states(states)
            return True
        return False

    return True



def get_next_available_line() -> dict | None:
    """Returns the next available phone line using round-robin rotation.
    Skips lines that are in_call or cooling_down.

    Returns:
        A dict with line config (id, phone_number, sip_trunk_id, etc.) or None if all busy.
    """
    global _last_used_index

    with _state_lock:
        lines = get_all_lines()
        if not lines:
            return None

        n = len(lines)
        for i in range(n):
            idx = (_last_used_index + 1 + i) % n
            line = lines[idx]
            line_id = line["id"]

            if _is_line_available(line_id):
                _last_used_index = idx
                logging.info(f"📞 Selected {line['display_name']} ({line['phone_number']}) for next call")
                return line

        logging.warning("⚠️ All phone lines are busy or cooling down!")
        return None


def get_line_for_callback(exclude_line_id: str = None) -> dict | None:
    """Returns any available line EXCEPT the specified one (for cross-number callbacks).

    Args:
        exclude_line_id: The line ID to exclude (e.g., the busy line that missed the inbound call)

    Returns:
        An available line config dict, or None if no other line is free.
    """
    with _state_lock:
        lines = get_all_lines()
        for line in lines:
            if line["id"] == exclude_line_id:
                continue
            if _is_line_available(line["id"]):
                logging.info(f"📞 Selected {line['display_name']} ({line['phone_number']}) for cross-number callback")
                return line

        logging.warning(f"⚠️ No alternative lines available for callback (excluding {exclude_line_id})")
        return None


def mark_line_busy(line_id: str):
    """Marks a line as currently in a call."""
    with _state_lock:
        states = _load_states()
        if line_id not in states:
            states[line_id] = {}
        states[line_id]["status"] = "in_call"
        states[line_id]["busy_since"] = time.time()
        states[line_id]["cool_until"] = None
        _save_states(states)
        logging.info(f"🔴 Line {line_id} marked as IN_CALL")


def mark_line_available(line_id: str, start_cooldown: bool = True):
    """Marks a line as available (optionally with a cooldown period).

    Args:
        line_id: The line ID to mark available
        start_cooldown: If True, enters cooling_down state first (default behavior after a call ends)
    """
    with _state_lock:
        states = _load_states()
        if line_id not in states:
            states[line_id] = {}
        if start_cooldown:
            config = _load_config()
            cooling_seconds = 60  # default
            for line in config.get("lines", []):
                if line["id"] == line_id:
                    cooling_seconds = line.get("cooling_seconds", 60)
                    break
            states[line_id]["status"] = "cooling_down"
            states[line_id]["cool_until"] = time.time() + cooling_seconds
            states[line_id]["busy_since"] = None
            logging.info(f"❄️ Line {line_id} entering cooldown ({cooling_seconds}s)")
        else:
            states[line_id]["status"] = "available"
            states[line_id]["busy_since"] = None
            states[line_id]["cool_until"] = None
            logging.info(f"🟢 Line {line_id} marked as AVAILABLE")
        _save_states(states)



def is_our_number(phone: str) -> bool:
    """Returns True if the given phone number belongs to one of our 3 Alex lines.
    Used to prevent self-calling loops.
    """
    if not phone:
        return False
    # Normalize: strip spaces, dashes, parens
    clean = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    for line in get_all_lines():
        if line["phone_number"] == clean:
            return True

    return False


def get_line_by_phone(phone: str) -> dict | None:
    """Returns the line config for a given phone number, or None."""
    if not phone:
        return None
    clean = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not clean.startswith("+"):
        clean = "+" + clean

    for line in get_all_lines():
        if line["phone_number"] == clean:
            return line
    return None


def get_line_by_id(line_id: str) -> dict | None:
    """Returns the line config for a given line ID, or None."""
    for line in get_all_lines():
        if line["id"] == line_id:
            return line
    return None


def get_line_status_summary() -> list[dict]:
    """Returns a human-readable summary of all line states."""
    summary = []
    for line in get_all_lines():
        state = _get_line_state(line["id"])
        # Check if cooling has expired
        _is_line_available(line["id"])
        state = _get_line_state(line["id"])

        info = {
            "id": line["id"],
            "phone": line["phone_number"],
            "name": line["display_name"],
            "status": state["status"],
        }
        if state["status"] == "cooling_down" and state.get("cool_until"):
            remaining = max(0, state["cool_until"] - time.time())
            info["cooldown_remaining_s"] = round(remaining, 1)
        summary.append(info)
    return summary


if __name__ == "__main__":
    # Quick self-test
    print("\n📞 Phone Lines Configuration:")
    print("-" * 50)
    for line in get_all_lines():
        print(f"  {line['display_name']}: {line['phone_number']} (Trunk: {line['sip_trunk_id']})")
    print()

    print("🔍 Self-call prevention test:")
    test_numbers = ["+14694616899", "+19453260478", "+19453260334", "+17068130213"]
    for num in test_numbers:
        print(f"  {num}: {'🚫 OUR NUMBER' if is_our_number(num) else '✅ External number'}")
    print()

    print("📋 Line rotation test:")
    for i in range(5):
        line = get_next_available_line()
        if line:
            print(f"  Call {i+1}: {line['display_name']} ({line['phone_number']})")
            mark_line_busy(line["id"])
            # Simulate instant completion for testing
            mark_line_available(line["id"], start_cooldown=False)
    print()
