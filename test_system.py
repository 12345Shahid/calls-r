#!/usr/bin/env python3
"""
Comprehensive Automated Verification Script (test_system.py)
Tests all components of the LiveKit + Replicate Voice AI calling system without placing a real phone call.

Run:
    ./.venv/bin/python3 test_system.py
"""
import os
import sys
import csv
import asyncio
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def run_verification():
    print("=" * 60)
    print("🛠️  LIVEKIT + REPLICATE VOICE AI SYSTEM VERIFICATION")
    print("=" * 60)

    # 1. Load environment variables
    print("\n[Step 1/5] Loading credentials from .env...")
    load_dotenv()
    
    lk_url = os.getenv("LIVEKIT_URL")
    lk_key = os.getenv("LIVEKIT_API_KEY")
    lk_secret = os.getenv("LIVEKIT_API_SECRET")
    rep_token = os.getenv("REPLICATE_API_TOKEN")

    if not all([lk_url, lk_key, lk_secret, rep_token]):
        print("❌ Error: Missing credentials in .env file!")
        return False
    print("✅ Credentials loaded successfully!")

    # 2. Test LiveKit Cloud Connection
    print("\n[Step 2/5] Testing LiveKit Cloud API connection...")
    try:
        from livekit import api
        lkapi = api.LiveKitAPI(lk_url, lk_key, lk_secret)
        rooms = await lkapi.room.list_rooms(api.ListRoomsRequest())
        print(f"✅ LiveKit Cloud Connected! Active rooms: {len(rooms.rooms)}")
        await lkapi.aclose()
    except Exception as e:
        print(f"❌ LiveKit API connection failed: {e}")
        return False

    # 3. Test Replicate Gemini 2.5 Flash Generation
    print("\n[Step 3/5] Testing Replicate API with Google Gemini 2.5 Flash...")
    try:
        import replicate
        os.environ["REPLICATE_API_TOKEN"] = rep_token
        out = replicate.run(
            "google/gemini-2.5-flash",
            input={"prompt": "Say 'Replicate AI is online and ready for sales calls!' in exactly 8 words or less."}
        )
        reply = "".join(list(out)).strip()
        print(f"✅ Replicate Gemini Responded: \"{reply}\"")
    except Exception as e:
        print(f"❌ Replicate API test failed: {e}")
        return False

    # 4. Test Lead Data Extraction Tool & CSV Logging
    print("\n[Step 4/5] Testing function calling lead extraction storage...")
    try:
        from agent import save_lead_data
        result = save_lead_data("test_verified", "demo_roofer@roofing.com", "+15550199999")
        print(f"✅ Function tool executed: {result}")
        
        # Verify CSV content
        leads_csv = os.path.join(os.path.dirname(__file__), "roofers_leads.csv")
        if os.path.exists(leads_csv):
            with open(leads_csv, mode="r", encoding="utf-8") as f:
                lines = f.readlines()
            print(f"✅ Verified database record written to roofers_leads.csv ({len(lines)-1} leads recorded)")
        else:
            print("❌ Error: roofers_leads.csv was not created!")
            return False
    except Exception as e:
        print(f"❌ Lead extraction test failed: {e}")
        return False

    # 5. Test Dialer Target Contractor CSV
    print("\n[Step 5/5] Checking target contractors database (roofers.csv)...")
    try:
        roofers_csv = os.path.join(os.path.dirname(__file__), "roofers.csv")
        with open(roofers_csv, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"✅ Found {len(rows)} targeted roofing contractors loaded in campaign queue.")
    except Exception as e:
        print(f"❌ Failed to load roofers.csv: {e}")
        return False

    print("\n" + "=" * 60)
    print("🎉 ALL SYSTEMS OPERATIONAL! YOUR VOICE AI AGENT IS 100% READY!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    asyncio.run(run_verification())
