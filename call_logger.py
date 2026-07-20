#!/usr/bin/env python3
"""
Call Logger Module (call_logger.py)
Logs every call to call_logs.jsonl with full transcript, and generates a CSV summary.
"""
import os
import json
import csv
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

LOGS_DIR = os.path.dirname(__file__)
JSONL_PATH = os.path.join(LOGS_DIR, "call_logs.jsonl")
CSV_PATH = os.path.join(LOGS_DIR, "call_summary.csv")


def log_call(
    phone_number: str,
    company_name: str,
    picked_up: bool,
    duration_seconds: float,
    outcome: str,
    transcript: list[dict],
) -> None:
    """Appends a call record to call_logs.jsonl and updates the CSV summary.
    
    Args:
        phone_number: The phone number dialed (e.g., "+17068130213")
        company_name: The company name from the CSV or metadata
        picked_up: Whether the call was answered
        duration_seconds: Total call duration in seconds
        outcome: One of: email_collected, whatsapp_collected, meeting_booked,
                 voicemail_left, rejected, gatekeeper_blocked, disconnected_early,
                 max_duration_reached
        transcript: List of {"role": "assistant"|"user", "text": "..."} dicts
    """
    record = {
        "timestamp": datetime.now().isoformat(),
        "phone_number": phone_number,
        "company_name": company_name,
        "picked_up": picked_up,
        "call_duration_seconds": round(duration_seconds, 1),
        "outcome": outcome,
        "full_transcript": transcript,
    }

    try:
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logging.info(f"📝 Call logged to {JSONL_PATH} | Phone: {phone_number} | Outcome: {outcome}")
    except Exception as e:
        logging.error(f"❌ Failed to log call: {e}")

    # Update the CSV summary
    _update_csv_summary(record)


def _update_csv_summary(record: dict) -> None:
    """Appends a summary row to the CSV file."""
    file_exists = os.path.exists(CSV_PATH)
    duration_secs = record["call_duration_seconds"]
    minutes = int(duration_secs // 60)
    seconds = int(duration_secs % 60)
    duration_str = f"{minutes}m{seconds:02d}s"

    try:
        with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "Timestamp", "PhoneNumber", "CompanyName", 
                    "PickedUp", "Duration", "Outcome", "TranscriptTurns"
                ])
            writer.writerow([
                record["timestamp"],
                record["phone_number"],
                record["company_name"],
                "Yes" if record["picked_up"] else "No",
                duration_str,
                record["outcome"],
                len(record["full_transcript"]),
            ])
        logging.info(f"📊 CSV summary updated: {CSV_PATH}")
    except Exception as e:
        logging.error(f"❌ Failed to update CSV summary: {e}")


def extract_transcript_from_history(history_dict: dict) -> list[dict]:
    """Extracts a clean transcript from LiveKit's session.history.to_dict() output.
    
    Returns a list of {"role": "assistant"|"user", "text": "..."} dicts.
    """
    transcript = []
    for item in history_dict.get("items", []):
        if item.get("type") != "message":
            continue
        role = item.get("role", "")
        if role not in ("assistant", "user"):
            continue
        # Extract text content from the content list
        text_parts = []
        for content_piece in item.get("content", []):
            if isinstance(content_piece, dict) and content_piece.get("type") == "text":
                text_parts.append(content_piece.get("text", ""))
            elif isinstance(content_piece, str):
                text_parts.append(content_piece)
        full_text = " ".join(text_parts).strip()
        if full_text:
            transcript.append({"role": role, "text": full_text})
    return transcript
