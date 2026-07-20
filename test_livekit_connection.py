#!/usr/bin/env python3
"""
Simple standalone script to test LiveKit Cloud API connectivity and diagnose geo-blocking/VPN issues.

Usage:
    export LIVEKIT_URL="wss://your-project.livekit.cloud"
    export LIVEKIT_API_KEY="your_api_key"
    export LIVEKIT_API_SECRET="your_api_secret"
    ./.venv/bin/python3 test_livekit_connection.py
"""
import os
import sys
import asyncio

# Ensure virtualenv is used if livekit is not found
try:
    from livekit import api
except ImportError:
    venv_path = os.path.join(os.path.dirname(__file__), ".venv", "lib")
    print("❌ Error: 'livekit-api' package is not found in the current Python environment.")
    print("👉 Please run using the virtualenv:")
    print("   ./.venv/bin/python3 test_livekit_connection.py")
    sys.exit(1)

async def test_connection():
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([url, api_key, api_secret]):
        if sys.stdin.isatty():
            print("⚠️ Missing environment variables. Please enter your LiveKit credentials:")
            url = url or input("Enter LIVEKIT_URL (e.g., wss://project.livekit.cloud): ").strip()
            api_key = api_key or input("Enter LIVEKIT_API_KEY: ").strip()
            api_secret = api_secret or input("Enter LIVEKIT_API_SECRET: ").strip()
        else:
            print("❌ Error: Missing required environment variables!")
            print("\nPlease set them in your terminal before running:")
            print('  export LIVEKIT_URL="wss://your-project.livekit.cloud"')
            print('  export LIVEKIT_API_KEY="your_api_key"')
            print('  export LIVEKIT_API_SECRET="your_api_secret"')
            print("  ./.venv/bin/python3 test_livekit_connection.py")
            return False

    if not url:
        print("❌ Error: LIVEKIT_URL is required.")
        return False

    if not url.startswith("ws://") and not url.startswith("wss://") and not url.startswith("http://") and not url.startswith("https://"):
        url = "wss://" + url

    print(f"\n🔍 Testing connection to LiveKit API at: {url}...")
    print("⏳ Sending test request (ListRooms) to check if IP/API key is allowed...")

    try:
        lkapi = api.LiveKitAPI(url, api_key, api_secret)
        rooms = await lkapi.room.list_rooms(api.ListRoomsRequest())
        print("\n✅ SUCCESS! Your LiveKit API key is working and not blocked!")
        print(f"Connected to project successfully. Active rooms found: {len(rooms.rooms)}")
        await lkapi.aclose()
        return True
    except Exception as e:
        print(f"\n❌ FAILED to connect to LiveKit API!")
        print(f"Error Details: {str(e)}")
        err_str = str(e).lower()
        if "403" in err_str or "forbidden" in err_str or "access denied" in err_str or "blocked" in err_str:
            print("\n⚠️ DIAGNOSIS: GEO-BLOCKING / IP RESTRICTION ERROR (403 Forbidden).")
            print("Your current IP address is being blocked by LiveKit Cloud / Cloudflare.")
            print("👉 Fix: Try enabling your VPN (routing through US or EU) or running this script from a US cloud server.")
        elif "401" in err_str or "unauthorized" in err_str or "jwt" in err_str or "signature" in err_str:
            print("\n⚠️ DIAGNOSIS: AUTHENTICATION ERROR.")
            print("Your LIVEKIT_API_KEY or LIVEKIT_API_SECRET is incorrect.")
        else:
            print("\n⚠️ DIAGNOSIS: NETWORK OR CONNECTION ERROR.")
            print("Please check your internet connection, URL format, or VPN status.")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())
