#!/usr/bin/env python3
"""
Missed Call Watcher & Auto-Callback Engine (missed_call_watcher.py)
Monitors LiveKit rooms & call_queue.jsonl to:
1. Detect missed inbound calls when agent is busy/offline.
2. Automatically process the callback queue (`queue_type="callback"`) immediately when lines are free.
3. Automatically process scheduled retries (`queue_type="retry"`).

Run continuously:
    ./.venv/bin/python3 missed_call_watcher.py --poll-interval 10
"""
import os
import sys
import time
import asyncio
import argparse
import logging
from dotenv import load_dotenv
from livekit import api
from call_queue import add_to_queue, get_pending_calls, update_queue_status, get_queue_stats
from dialer import trigger_call
from phone_lines import get_next_available_line, get_line_for_callback, get_line_by_phone, mark_line_busy

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()


async def check_active_rooms_for_missed(lkapi: api.LiveKitAPI, tracked_rooms: dict):
    """Checks active rooms on LiveKit. If an inbound SIP call rings for >15s without an agent joining,
    or if an inbound room closes without an agent ever joining, marks it as a missed call.
    """
    try:
        res = await lkapi.room.list_rooms(api.ListRoomsRequest())
        active_room_names = set()

        for r in res.rooms:
            room_name = r.name
            active_room_names.add(room_name)

            if room_name.startswith("sip_inbound") or room_name.startswith("in_") or "inbound" in room_name.lower():
                if room_name not in tracked_rooms:
                    tracked_rooms[room_name] = {"seen_at": time.time(), "agent_joined": False, "phone": "", "company": "", "missed_on_line": None}

                # Check participants
                try:
                    p_res = await lkapi.room.list_participants(api.ListParticipantsRequest(room=room_name))
                    for p in p_res.participants:
                        attrs = dict(p.attributes) if hasattr(p, "attributes") and p.attributes else {}
                        if p.identity.startswith("agent") or p.identity.startswith("AI") or p.name == "Alex":
                            tracked_rooms[room_name]["agent_joined"] = True
                        elif attrs.get("sip.phoneNumber") or attrs.get("sip.callFrom"):
                            tracked_rooms[room_name]["phone"] = attrs.get("sip.phoneNumber") or attrs.get("sip.callFrom")
                            tracked_rooms[room_name]["company"] = p.name or f"Caller ({tracked_rooms[room_name]['phone']})"
                        
                        # Identify which of our lines was called
                        our_phone = attrs.get("sip.callTo") or attrs.get("sip.trunkPhoneNumber")
                        if our_phone and not tracked_rooms[room_name]["missed_on_line"]:
                            line_obj = get_line_by_phone(our_phone)
                            if line_obj:
                                tracked_rooms[room_name]["missed_on_line"] = line_obj["id"]
                except Exception:
                    pass

        # Check for closed rooms that were tracked as inbound but agent NEVER joined
        closed_rooms = [r for r in list(tracked_rooms.keys()) if r not in active_room_names]
        for c_room in closed_rooms:
            data = tracked_rooms.pop(c_room)
            if not data.get("agent_joined") and data.get("phone"):
                logging.info(f"⚡ Room {c_room} closed without AI answering! Adding {data['phone']} to priority callback queue.")
                add_to_queue(data["phone"], data.get("company", ""), reason="missed_inbound_offline", queue_type="callback", missed_on_line=data.get("missed_on_line"))

    except Exception as e:
        logging.error(f"⚠️ Error checking rooms for missed calls: {e}")


async def auto_callback_loop(lkapi: api.LiveKitAPI, trunk_id: str, poll_interval: int = 10):
    """Continuous background engine that watches rooms and dials pending queue items."""
    tracked_rooms = {}
    logging.info(f"🚀 Missed Call Watcher & Auto-Callback Engine started (polling every {poll_interval}s)...")
    
    while True:
        try:
            # 1. Watch for missed rooms
            await check_active_rooms_for_missed(lkapi, tracked_rooms)

            # 2. Check if any line is available right now
            pending = get_pending_calls()
            if not pending:
                await asyncio.sleep(poll_interval)
                continue

            item = pending[0]
            q_id = item.get("id")
            phone = item.get("phone_number")
            company = item.get("company_name", "Caller")
            q_type = item.get("queue_type", "retry")
            attempts = item.get("attempts", 0)
            missed_on_line = item.get("missed_on_line")

            is_cb = (q_type == "callback")
            contact = "Missed Caller" if is_cb else "Owner"

            # For cross-number callback, prefer a different line than where it was missed
            if is_cb and missed_on_line:
                line = get_line_for_callback(exclude_line_id=missed_on_line)
                if not line:
                    # If other lines are busy, allow using the original line or wait
                    line = get_next_available_line()
            else:
                line = get_next_available_line()

            if not line:
                logging.debug("⏳ All phone lines currently busy or cooling. Waiting for free line to process queue...")
                await asyncio.sleep(poll_interval)
                continue

            logging.info(f"\n--- ⚡ AUTO-PROCESSING QUEUE [{q_type.upper()}] -> {phone} ({company}) via {line['display_name']} ---")
            update_queue_status(q_id, "in_progress", attempts_increment=1)

            success, room_name = await trigger_call(lkapi, trunk_id or "auto", phone, company, contact, is_auto_callback=is_cb, line=line)
            if success:
                update_queue_status(q_id, "completed")
                logging.info(f"✅ Auto-call connected! Waiting 20 seconds before next check...")
                await asyncio.sleep(20)
            else:
                if attempts + 1 >= 3:
                    logging.warning(f"⚠️ Max attempts reached for {phone}. Marking as failed.")
                    update_queue_status(q_id, "failed")
                else:
                    logging.warning(f"⚠️ Auto-call failed. Rescheduling...")
                    update_queue_status(q_id, "pending")
                await asyncio.sleep(5)

        except Exception as e:
            logging.error(f"❌ Error in auto_callback_loop: {e}")

        await asyncio.sleep(poll_interval)


async def main():
    parser = argparse.ArgumentParser(description="Missed Call Watcher & Auto-Callback Engine")
    parser.add_argument("--poll-interval", type=int, default=10, help="Seconds between queue and room checks")
    args = parser.parse_args()

    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    trunk_id = os.getenv("LIVEKIT_SIP_TRUNK_ID", "auto")

    if not all([url, api_key, api_secret]):
        logging.error("❌ Missing required LiveKit API environment variables.")
        sys.exit(1)

    lkapi = api.LiveKitAPI(url, api_key, api_secret)
    try:
        await auto_callback_loop(lkapi, trunk_id, args.poll_interval)
    finally:
        await lkapi.aclose()

if __name__ == "__main__":
    asyncio.run(main())
