#!/usr/bin/env python3
"""
Call History Module (call_history.py)
Persistent memory system: saves and retrieves previous conversations by phone number.
Used to recognize returning callers and resume context.
"""
import os
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

HISTORY_PATH = os.path.join(os.path.dirname(__file__), "call_history.jsonl")


def save_call_history(
    phone_number: str,
    company_name: str,
    transcript: list[dict],
    outcome: str,
    alex_line_used: str = None,
) -> None:
    """Saves a conversation record for future phone-number-based lookup.
    
    Args:
        phone_number: The customer's phone number (e.g., "+17068130213")
        company_name: The company name
        transcript: List of {"role": "assistant"|"user", "text": "..."} dicts
        outcome: The call outcome (email_collected, rejected, etc.)
        alex_line_used: The Alex line ID used for this call (e.g., "line_1")
    """
    record = {
        "timestamp": datetime.now().isoformat(),
        "phone_number": phone_number,
        "company_name": company_name,
        "outcome": outcome,
        "transcript": transcript,
        "alex_line_used": alex_line_used,
    }

    try:
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logging.info(f"🧠 Call history saved for {phone_number} (Line: {alex_line_used or 'default'})")
    except Exception as e:
        logging.error(f"❌ Failed to save call history: {e}")


def get_previous_conversations(phone_number: str) -> list[dict]:
    """Retrieves all previous conversations with a given phone number.
    
    Args:
        phone_number: The phone number to look up (e.g., "+17068130213")
    
    Returns:
        A list of previous conversation records, sorted by timestamp (oldest first).
        Empty list if no history found.
    """
    if not os.path.exists(HISTORY_PATH):
        return []

    matches = []
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record.get("phone_number") == phone_number:
                        matches.append(record)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logging.error(f"❌ Failed to read call history: {e}")

    return sorted(matches, key=lambda r: r.get("timestamp", ""))


def build_memory_context(phone_number: str) -> str:
    """Builds a context string summarizing previous interactions for prompt injection.
    
    Args:
        phone_number: The phone number to look up
    
    Returns:
        A formatted string to prepend to the system prompt, or empty string if no history.
    """
    conversations = get_previous_conversations(phone_number)
    if not conversations:
        return ""

    context_parts = []
    context_parts.append("# PREVIOUS CONVERSATION HISTORY")
    context_parts.append(f"You have spoken to this caller ({phone_number}) before. Here is the history:\n")

    for i, conv in enumerate(conversations, 1):
        timestamp = conv.get("timestamp", "Unknown time")
        company = conv.get("company_name", "Unknown company")
        outcome = conv.get("outcome", "unknown")
        line_used = conv.get("alex_line_used")
        transcript = conv.get("transcript", [])

        context_parts.append(f"## Call #{i} — {timestamp}")
        context_parts.append(f"Company: {company}")
        context_parts.append(f"Outcome: {outcome}")
        if line_used:
            context_parts.append(f"Alex Line Used: {line_used}")

        # Include the last few turns of the conversation for context
        # (not the full transcript to keep the prompt manageable)
        recent_turns = transcript[-8:] if len(transcript) > 8 else transcript
        if recent_turns:
            context_parts.append("Key conversation excerpt:")
            for turn in recent_turns:
                role_label = "Alex" if turn["role"] == "assistant" else "Customer"
                text = turn["text"]
                # Truncate very long turns
                if len(text) > 200:
                    text = text[:200] + "..."
                context_parts.append(f"- {role_label}: \"{text}\"")
        context_parts.append("")

    context_parts.append("IMPORTANT: Use this history naturally and conversationally. Adapt to whatever specific topics, questions, or unfinished steps appear in the excerpts above. Do NOT use strict or canned phrases—speak like a real human continuing a dialogue.\n")

    return "\n".join(context_parts)
