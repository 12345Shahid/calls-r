#!/usr/bin/env python3
"""
Test Caller Agent (test_caller_agent.py)
Simulates a realistic roofer/contractor who CALLS Alex's phone number.

Architecture:
  1. This script dials Alex's number (+14694616899) via our existing LiveKit SIP trunk
  2. The call arrives at Alex's SignalWire number → LiveKit inbound trunk → agent.py picks up
  3. Meanwhile, this script runs a SEPARATE LiveKit agent worker (with agent_name="test_caller")
     in the outbound room, playing the role of the roofer
  4. The two AI agents talk to each other over the real phone network

Usage:
    # First, make sure agent.py is running:
    ./.venv/bin/python3 agent.py dev

    # Then in another terminal, start the test caller worker:
    ./.venv/bin/python3 test_caller_agent.py --worker --scenario interested

    # Then in a THIRD terminal, trigger the call:
    ./.venv/bin/python3 test_caller_agent.py --scenario interested

Test Scenarios:
    interested  — Friendly roofer, curious about the free website, gives contact info
    busy        — Roofer on a roof, very short answers, just wants a text
    skeptical   — Burned by marketing before, challenges everything, needs convincing
    callback    — Roofer calling BACK after seeing a missed call / voicemail
"""
import os
import sys
import uuid
import json
import asyncio
import logging
import argparse
import time
from datetime import datetime
from dotenv import load_dotenv
from livekit import api
from livekit.api import sip_service
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    Agent,
    AgentSession,
)
from livekit.plugins import openai, cartesia, gladia
from livekit.agents import stt

class MockSTT(stt.STT):
    def __init__(self):
        super().__init__(capabilities=stt.STTCapabilities(streaming=True, interim_results=False))
    async def _recognize_impl(self, buffer, language=None):
        return stt.SpeechEvent(type=stt.SpeechEventType.FINAL_TRANSCRIPT, alternatives=[])
    def update_options(self, *args, **kwargs):
        return self
    def stream(self, *, conn_options=None):
        return MockSTTStream(self, conn_options=conn_options)

class MockSTTStream(stt.RecognizeStream):
    def __init__(self, stt_instance, *, conn_options=None):
        super().__init__(stt=stt_instance, conn_options=conn_options or stt.APIConnectOptions())
    async def _run(self):
        while True:
            await asyncio.sleep(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
load_dotenv()

# ==========================================
# ALEX'S PHONE NUMBER (the agent we're testing)
# ==========================================
ALEX_PHONE_NUMBER = "+14694616899"

# ==========================================
# TEST SCENARIOS (different roofer personalities)
# ==========================================

SCENARIOS = {
    "interested": """You are Mike, the owner of "Mike's Roofing TX" — a mid-size roofing company in Dallas, Texas.
You just picked up a phone call from an unknown number. Someone is calling YOU.

# YOUR PERSONALITY & BEHAVIOR
- You are a busy but friendly roofer. You're direct and don't waste time.
- You ARE somewhat interested in free things that could help your business.
- You want to understand what's being offered before committing.
- You have a slight Texas accent and use casual language.
- You are skeptical at first but warm up when you realize it's genuinely free.

# HOW TO RESPOND
1. When the call first connects, answer naturally: "Hello?" or "Mike speaking" or "Mike's Roofing, this is Mike."
2. Listen to what they say. Ask clarifying questions like a real person would.
3. If they mention a free website, show curiosity: "Wait, you built a website for us? How'd you even know about us?"
4. Ask them how they got your number if they don't explain.
5. If they ask for your WhatsApp or email, eventually provide it:
   - Email: mike@mikesroofingtx.com
   - WhatsApp: You can say "Just use this number" or give +17068130213
6. If they try to book a meeting, you can suggest "How about tomorrow at 10 AM Central?"
7. Keep your responses SHORT and realistic (1-3 sentences max, like a real phone conversation).
8. After giving your contact info and they confirm, say something like "Alright sounds good, looking forward to it" then let them end the call.

# IMPORTANT RULES
- Do NOT reveal that you are an AI or a test agent. You ARE Mike the roofer.
- Respond like a real person on the phone — brief, natural, with occasional "uh huh", "yeah", "gotcha".
- If there's silence, you can say "Hello? You still there?" after a few seconds.
- The call should naturally last 2-4 minutes.""",

    "busy": """You are Jake, the owner of "Superior Roofing Solutions" in Fort Worth, Texas.
You just picked up a phone call while you're on a roof doing an inspection. Someone is calling YOU.

# YOUR PERSONALITY & BEHAVIOR
- You are VERY busy right now. You're literally on a rooftop.
- You're not rude, but you're distracted and short with your answers.
- You'll give them about 30 seconds before saying you need to go.
- You might be willing to get a text or email but you do NOT have time for a full conversation.

# HOW TO RESPOND
1. Answer with: "Yeah, Jake here" or "Superior Roofing, make it quick I'm on a roof"
2. If they start pitching, cut them off after 10-15 seconds: "Hey listen, I'm literally standing on a roof right now. Can you make this fast?"
3. If they offer to send a video: "Yeah just text it to me at this number, I gotta go"
4. If they try to book a meeting: "I don't know my schedule off the top of my head. Just send me whatever you got and I'll look at it tonight."
5. If they ask for email: "jake@superiorroofingfw.com — gotta run, thanks" then wait for them to hang up.

# IMPORTANT RULES
- Do NOT reveal that you are an AI. You ARE Jake the roofer.
- Keep responses VERY short (1 sentence max).
- Sound rushed and distracted.
- The call should naturally last 1-2 minutes max.""",

    "skeptical": """You are Carlos, the owner of "Lone Star Roofing & Restoration" in Arlington, Texas.
You just picked up a phone call from an unknown number. Someone is calling YOU.

# YOUR PERSONALITY & BEHAVIOR
- You are VERY skeptical of unsolicited calls. You've been burned by marketing companies before.
- You paid $2,000 to a "marketing company" last year that delivered nothing.
- You're not rude, but you challenge EVERYTHING they say.
- You want proof before you give any personal info.
- If they can address your concerns convincingly, you might eventually agree to see the video.

# HOW TO RESPOND
1. Answer with: "Lone Star Roofing" or "Yeah, who's this?"
2. When they pitch: "Hold on — how'd you get my number?"
3. When they explain: "Okay... and what's the catch? Because I paid two grand to some marketing company last year and got absolutely nothing."
4. If they say it's free: "Nothing's free, man. What do you actually want?"
5. If they persist and sound genuine: "Alright, fine. But I'm not clicking any random links. Can you just show me on a Zoom or something?"
6. If they offer Zoom: "Yeah okay. But keep it to 15 minutes, I got estimates to run."
7. For contact info: "You can email me at carlos@lonestarroofing.net"
8. After giving info: "Alright, we'll see. If this is legit, I'll be impressed. If not, don't call me again."

# IMPORTANT RULES
- Do NOT reveal that you are an AI. You ARE Carlos the roofer.
- Be challenging but not hostile. You're protecting your time and money.
- Ask tough questions that test Alex's objection handling.
- The call should naturally last 3-5 minutes.""",

    "callback": """You are David, the owner of "DFW Roofing Pros" in Plano, Texas.
You are CALLING BACK because you saw a missed call from this number. You may have also listened to a voicemail from Alex.
Someone just picked up — you are the one who initiated this call.

# YOUR PERSONALITY & BEHAVIOR
- You're calling back a missed call. You're curious but cautious.
- You vaguely remember hearing something about a free website in the voicemail (or you just saw the missed call).
- You're polite and professional.
- You're genuinely interested if this is real.

# HOW TO RESPOND
1. Start with: "Hey, I got a missed call from this number?" or "Yeah hi, someone called me from this number earlier? Something about a website?"
2. When they explain: "Oh okay, yeah I think I heard the voicemail. So you actually built a website for us already?"
3. Show genuine curiosity: "How does it look? Did you use our logo and everything?"
4. If they offer to send a video: "Yeah send it over. My WhatsApp is this number — +17068130213"
5. If they try to book a meeting: "Um, let me check... How about Thursday at 2 PM? I'm Central time."
6. After confirming: "Cool, looking forward to seeing it. Thanks Alex."

# IMPORTANT RULES
- Do NOT reveal that you are an AI. You ARE David the roofer.
- Be naturally curious and engaged.
- This tests Alex's INBOUND prompt and memory system.
- The call should naturally last 2-3 minutes.""",
    "returning": """You are David, the owner of "DFW Roofing Pros". You previously spoke with Alex.
You are calling back to follow up on your previous conversation.

# YOUR PERSONALITY & BEHAVIOR
- Friendly, professional, and familiar with Alex.
- You want to confirm if he sent the video walkthrough and confirm the Thursday appointment.

# HOW TO RESPOND
1. Start with: "Hey Alex, David here. Just calling back to see if you sent that video walkthrough to my WhatsApp yet?"
2. When he responds: "Awesome. And we're still good for our meeting on Thursday at 2 PM Central, right?"
3. When he confirms: "Perfect, looking forward to it. Thanks again, talk to you on Thursday!"
4. Let Alex hang up or wrap up the call.""",
}


# ==========================================
# TEST CALLER AGENT ENTRYPOINT (LiveKit Worker)
# ==========================================

async def test_caller_entrypoint(ctx: JobContext):
    """Entrypoint for the test caller agent — plays the role of a roofer in the outbound room."""
    logging.info(f"📞 Test Caller Agent connecting to Room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    call_start_time = time.time()

    # Get the scenario from environment variable
    scenario_name = os.getenv("TEST_SCENARIO", "interested")
    instructions = SCENARIOS.get(scenario_name, SCENARIOS["interested"])

    logging.info(f"🎭 Test Scenario: {scenario_name}")
    logging.info(f"🎤 Playing the role of a roofer, waiting for Alex to speak first...")

    # Create the test caller agent
    agent = Agent(instructions=instructions)

    # Use MockSTT to bypass Gladia API key rate limits/concurrency limits entirely
    stt = MockSTT()
    tts = cartesia.TTS() if os.getenv("CARTESIA_API_KEY") else openai.TTS()

    # Use a dummy LLM since we're using a pre-defined script
    base_url = "https://openrouter.ai/api/v1"
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("LLM_MODEL", "deepseek/deepseek-v4-pro")
    llm = openai.LLM(model=model, base_url=base_url, api_key=api_key)

    session = AgentSession(stt=stt, llm=llm, tts=tts)

    # Scenarios predefined scripts
    INTERESTED_RESPONSES = [
        "Yeah, I got a minute. Who's this?",
        "Wait, you built a website for us? How? We already have a website.",
        "Right, Lone Star Roofing. Yeah, we've had that site for a few years now. What's wrong with it?",
        "Wait, you built a whole new one for free? What's the catch?",
        "I see. Well, my email is carlos@lonestarroofing.net. Send me the video link there and I'll take a look tonight.",
        "Alright sounds good, looking forward to it. Take care."
    ]
    BUSY_RESPONSES = [
        "Superior Roofing, make it quick I'm on a roof.",
        "Hey listen, I'm literally standing on a roof right now. Can you make this fast?",
        "Yeah just text it to me at this number, I gotta go.",
        "I don't know my schedule off the top of my head. Just send me whatever you got and I'll look at it tonight.",
        "jake@superiorroofingfw.com — gotta run, thanks."
    ]
    SKEPTICAL_RESPONSES = [
        "Lone Star Roofing, this is Carlos.",
        "Hold on — how'd you get my number?",
        "Okay... and what's the catch? Because I paid two grand to some marketing company last year and got absolutely nothing.",
        "Nothing's free, man. What do you actually want?",
        "Alright, fine. But I'm not clicking any random links. Can you just show me on a Zoom or something?",
        "Yeah okay. But keep it to 15 minutes, I got estimates to run.",
        "You can email me at carlos@lonestarroofing.net.",
        "Alright, we'll see. If this is legit, I'll be impressed. If not, don't call me again."
    ]
    CALLBACK_RESPONSES = [
        "Oh okay, yeah I think I heard the voicemail. So you actually built a website for us already?",
        "How does it look? Did you use our logo and everything?",
        "Yeah send it over. My WhatsApp is this number — +17068130213",
        "Um, Thursday at 2 PM Central time works for me.",
        "Cool, looking forward to seeing it. Thanks Alex."
    ]
    RETURNING_RESPONSES = [
        "Hey Alex, David here. Just calling back to see if you sent that video walkthrough to my WhatsApp yet?",
        "Awesome. And we're still good for our meeting on Thursday at 2 PM Central, right?",
        "Perfect, looking forward to it. Thanks again, talk to you on Thursday!"
    ]

    responses = list(INTERESTED_RESPONSES)
    if scenario_name == "busy":
        responses = list(BUSY_RESPONSES)
    elif scenario_name == "skeptical":
        responses = list(SKEPTICAL_RESPONSES)
    elif scenario_name == "callback":
        responses = list(CALLBACK_RESPONSES)
    elif scenario_name == "returning":
        responses = list(RETURNING_RESPONSES)

    turn_index = 0
    speaking_lock = asyncio.Lock()
    transcript = []

    # Log the transcript when the session ends
    def on_session_close(event):
        call_duration = time.time() - call_start_time
        logging.info(f"📊 Test call ended. Duration: {call_duration:.1f}s")

        try:
            # Save test results
            result = {
                "timestamp": datetime.now().isoformat(),
                "scenario": scenario_name,
                "duration_seconds": round(call_duration, 1),
                "transcript": transcript,
                "alex_phone": ALEX_PHONE_NUMBER,
                "room": ctx.room.name,
            }

            results_path = os.path.join(os.path.dirname(__file__), "test_call_results.jsonl")
            with open(results_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

            logging.info(f"✅ Test call results saved to test_call_results.jsonl")

            # Print a nice summary
            logging.info("=" * 60)
            logging.info(f"📋 TEST CALL TRANSCRIPT ({scenario_name} scenario)")
            logging.info(f"⏱️  Duration: {call_duration:.1f}s")
            logging.info("=" * 60)
            for turn in transcript:
                speaker = turn['speaker']
                text = turn['text'][:120]
                logging.info(f"  {speaker}: {text}")
            logging.info("=" * 60)

        except Exception as e:
            logging.error(f"❌ Failed to log test transcript: {e}", exc_info=True)

    session.on("close", on_session_close)

    async def speak_next_turn():
        nonlocal turn_index
        async with speaking_lock:
            if turn_index < len(responses):
                response_text = responses[turn_index]
                turn_index += 1
                logging.info(f"🎤 Roofer speaking Turn {turn_index}: '{response_text}'")
                transcript.append({"role": "assistant", "speaker": "Roofer (Test)", "text": response_text})
                
                # Write to shared transit file for agent.py MockSTT
                try:
                    import json
                    transit_file = "/Users/shahidhasan/.gemini/antigravity-ide/brain/f7388b72-cc4f-4340-8a17-e42264db03fe/scratch/speech_transit.jsonl"
                    os.makedirs(os.path.dirname(transit_file), exist_ok=True)
                    with open(transit_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps({
                            "room": ctx.room.name,
                            "speaker": "roofer",
                            "text": response_text,
                            "timestamp": time.time()
                        }) + "\n")
                except Exception as e:
                    logging.error(f"Failed to write speech transit: {e}")
                    
                await asyncio.sleep(1.2)  # natural pause
                session.say(response_text)
            else:
                logging.info("🏁 Roofer scenario complete, hanging up call...")
                await asyncio.sleep(3.0)
                await ctx.room.disconnect()

    @session.on("user_state_changed")
    def on_user_state_changed(event):
        logging.info(f"👤 Participant (Alex) state: {event.old_state} -> {event.new_state}")
        # When Alex stops speaking (transitions from speaking to listening), Roofer speaks next turn
        if event.old_state == "speaking" and event.new_state == "listening":
            transcript.append({"role": "user", "speaker": "Alex (Agent)", "text": "[Alex speaking]"})
            asyncio.create_task(speak_next_turn())

    logging.info("🎙️ Starting Test Caller AI Session...")
    await session.start(agent, room=ctx.room)

    # Start a timer: if we don't hear Alex speak within 4 seconds, we speak first (say "Hello?")
    async def silence_watchdog():
        await asyncio.sleep(4.0)
        if turn_index == 0:
            logging.info("⏳ Silence detected: Roofer speaking first to initiate the call...")
            asyncio.create_task(speak_next_turn())
            
    asyncio.create_task(silence_watchdog())

    # For the "callback" and "returning" scenarios, the roofer initiates immediately
    if scenario_name in ("callback", "returning"):
        await asyncio.sleep(1.5)
        logging.info(f"📱 {scenario_name} scenario: Roofer initiating conversation...")
        asyncio.create_task(speak_next_turn())


# ==========================================
# STANDALONE LAUNCHER (triggers the SIP call)
# ==========================================

async def launch_test_call(scenario: str, target_phone: str = ALEX_PHONE_NUMBER):
    """Launches a test call: dials target_phone via SIP. The test_caller worker handles the roofer side."""
    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    trunk_id = os.getenv("LIVEKIT_SIP_TRUNK_ID")

    if not all([url, api_key, api_secret, trunk_id]):
        logging.error("❌ Missing LiveKit environment variables! Check your .env file.")
        sys.exit(1)

    room_name = f"test_call_{uuid.uuid4().hex[:8]}"

    logging.info("=" * 60)
    logging.info(f"📞 LAUNCHING AI vs AI TEST CALL")
    logging.info(f"🎭 Scenario: {scenario}")
    logging.info(f"📱 Calling Alex at: {target_phone}")
    logging.info(f"🏠 Room: {room_name}")
    logging.info("=" * 60)

    lkapi = api.LiveKitAPI(url, api_key, api_secret)

    try:
        # First, dispatch the test_caller worker into this room so it speaks as the roofer
        from livekit.api import agent_dispatch_service
        try:
            await lkapi.agent_dispatch.create_dispatch(
                agent_dispatch_service.CreateAgentDispatchRequest(
                    agent_name="test_caller",
                    room=room_name,
                )
            )
            logging.info(f"🎭 Dispatched 'test_caller' worker to room: {room_name}")
        except Exception as e:
            logging.warning(f"⚠️ Could not create explicit dispatch for test_caller: {e}")

        # Create SIP participant to dial Alex's number
        # This creates the outbound room where our test_caller worker will join
        req = sip_service.CreateSIPParticipantRequest(
            sip_trunk_id=trunk_id,
            sip_call_to=target_phone,
            room_name=room_name,
            participant_identity=f"test_roofer_{uuid.uuid4().hex[:6]}",
            participant_name=f"Test Roofer ({scenario})",
            participant_metadata="test_call",
            wait_until_answered=True,
        )

        res = await lkapi.sip.create_sip_participant(req)
        logging.info(f"✅ Call connected! SIP Participant ID: {res.participant_id}")
        logging.info(f"🎤 Alex (agent.py) should now be talking in room: {room_name}")
        logging.info(f"🎭 Test caller worker should be responding as a roofer...")

        # Keep alive while the call is in progress
        logging.info("⏳ Monitoring test call... (Press Ctrl+C to end early)")

        while True:
            await asyncio.sleep(5)
            try:
                rooms = await lkapi.room.list_rooms(api.ListRoomsRequest(names=[room_name]))
                if not rooms.rooms:
                    logging.info("📭 Room closed — test call completed!")
                    break
                room_info = rooms.rooms[0]
                if room_info.num_participants == 0:
                    logging.info("📭 All participants left — test call completed!")
                    break
                else:
                    elapsed = time.time()
                    logging.info(f"   📞 Call still active — {room_info.num_participants} participants in room")
            except Exception:
                break

    except KeyboardInterrupt:
        logging.info("\n⚠️ Test call cancelled by user.")
    except Exception as e:
        logging.error(f"❌ Failed to launch test call: {e}", exc_info=True)
    finally:
        await lkapi.aclose()

    logging.info("\n📋 Check test_call_results.jsonl for the full transcript!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI vs AI Test Caller — Simulates roofers calling/answering Alex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
QUICK START (3 terminals):
  Terminal 1: ./.venv/bin/python3 agent.py dev
  Terminal 2: ./.venv/bin/python3 test_caller_agent.py --worker --scenario interested
  Terminal 3: ./.venv/bin/python3 test_caller_agent.py --scenario interested

SCENARIOS:
  interested  — Friendly roofer, gives email/WhatsApp
  busy        — Roofer on a roof, wants a quick text
  skeptical   — Burned before, challenges everything
  callback    — Roofer calling BACK (tests inbound + memory)
        """,
    )
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        default="interested",
        help="Which roofer personality to simulate (default: interested)",
    )
    parser.add_argument(
        "--phone",
        default=ALEX_PHONE_NUMBER,
        help="Which target phone number to dial (default: Line 1 +14694616899)",
    )
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Run as a LiveKit worker (start this before triggering the call)",
    )
    args = parser.parse_args()

    if args.worker:
        # Run as a LiveKit agent worker
        os.environ["TEST_SCENARIO"] = args.scenario
        logging.info(f"🚀 Starting Test Caller Worker (scenario: {args.scenario})...")
        logging.info(f"   Waiting for test call rooms to be dispatched...")
        sys.argv = [sys.argv[0], "dev"]
        cli.run_app(
            WorkerOptions(
                entrypoint_fnc=test_caller_entrypoint,
                agent_name="test_caller",
            )
        )
    else:
        # Standalone mode: trigger the SIP call
        os.environ["TEST_SCENARIO"] = args.scenario
        asyncio.run(launch_test_call(args.scenario, args.phone))
