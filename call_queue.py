#!/usr/bin/env python3
"""
Call Queue & Retry Management Module (call_queue.py)
Manages persistent queueing for:
1. Missed Inbound Calls (`queue_type="callback"`) — when someone calls and lines are busy or unanswered.
2. Unanswered Outbound Calls (`queue_type="retry"`) — when dialer gets busy signal or no answer.
"""
import os
import json
import time
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

QUEUE_PATH = os.path.join(os.path.dirname(__file__), "call_queue.jsonl")


def add_to_queue(
    phone_number: str,
    company_name: str,
    reason: str,
    queue_type: str = "callback",  # "callback" (priority missed call) or "retry" (outbound busy)
    available_after: float = None,
    missed_on_line: str = None,
) -> dict:
    """Adds a phone number to the auto-callback or retry queue.
    
    Args:
        phone_number: Phone number string (e.g. "+17068130213")
        company_name: Company name string
        reason: Reason for queueing (e.g., "missed_inbound", "outbound_busy", "no_answer")
        queue_type: "callback" (highest priority) or "retry"
        available_after: Unix timestamp when this call should be dialed (default: now for callbacks, +1800s for retries)
        missed_on_line: The line ID where the call was originally missed (for cross-number callbacks)
    """
    if not phone_number:
        return {}

    now = time.time()
    if available_after is None:
        if queue_type == "callback":
            available_after = now  # Call right back immediately as soon as a line is free!
        else:
            available_after = now + 1800  # Default retry after 30 minutes for outbound busy

    record = {
        "id": f"q_{int(now * 1000)}",
        "created_at": datetime.now().isoformat(),
        "created_ts": now,
        "phone_number": phone_number,
        "company_name": company_name or f"Roofer ({phone_number})",
        "reason": reason,
        "queue_type": queue_type,
        "status": "pending",  # pending, in_progress, completed, failed
        "available_after_ts": available_after,
        "attempts": 0,
        "missed_on_line": missed_on_line,
    }

    try:
        with open(QUEUE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logging.info(f"📋 Added to Queue [{queue_type.upper()}] -> {phone_number} ({company_name}) | Reason: {reason}")
    except Exception as e:
        logging.error(f"❌ Failed to write to call queue: {e}")

    return record


def get_pending_calls(now_ts: float = None) -> list[dict]:
    """Retrieves all pending calls that are ready to be dialed right now.
    Sorted by priority: 'callback' (missed inbound) comes FIRST, then 'retry' (outbound no-answer).
    """
    if not os.path.exists(QUEUE_PATH):
        return []

    if now_ts is None:
        now_ts = time.time()

    pending = []
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get("status") == "pending" and record.get("available_after_ts", 0) <= now_ts:
                        pending.append(record)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logging.error(f"❌ Failed to read call queue: {e}")

    # Sort: callback first (priority 0), retry second (priority 1), then by created_ts
    return sorted(pending, key=lambda r: (0 if r.get("queue_type") == "callback" else 1, r.get("created_ts", 0)))


def update_queue_status(queue_id: str, new_status: str, attempts_increment: int = 0) -> bool:
    """Updates the status of a queue record (e.g. to 'completed', 'in_progress', or 'failed')."""
    if not os.path.exists(QUEUE_PATH):
        return False

    updated = False
    lines = []
    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get("id") == queue_id or (queue_id.startswith("+") and record.get("phone_number") == queue_id and record.get("status") == "pending"):
                        record["status"] = new_status
                        record["updated_at"] = datetime.now().isoformat()
                        if attempts_increment > 0:
                            record["attempts"] = record.get("attempts", 0) + attempts_increment
                        updated = True
                    lines.append(json.dumps(record, ensure_ascii=False))
                except json.JSONDecodeError:
                    lines.append(line)

        if updated:
            with open(QUEUE_PATH, "w", encoding="utf-8") as f:
                for line in lines:
                    f.write(line + "\n")
            logging.info(f"📋 Updated queue item {queue_id} -> status: {new_status}")
    except Exception as e:
        logging.error(f"❌ Failed to update queue status: {e}")

    return updated


def get_queue_stats() -> dict:
    """Returns counts of pending callbacks, pending retries, and completed queue items."""
    stats = {"pending_callback": 0, "pending_retry": 0, "completed": 0, "failed": 0}
    if not os.path.exists(QUEUE_PATH):
        return stats

    try:
        with open(QUEUE_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    status = record.get("status", "")
                    qtype = record.get("queue_type", "retry")
                    if status == "pending":
                        if qtype == "callback":
                            stats["pending_callback"] += 1
                        else:
                            stats["pending_retry"] += 1
                    elif status == "completed":
                        stats["completed"] += 1
                    elif status == "failed":
                        stats["failed"] += 1
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        pass
    return stats
