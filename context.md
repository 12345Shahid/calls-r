Project Description: Automated Voice AI Sales Agent

1. Project Overview

The objective is to build a fully autonomous, closed-loop Voice AI agent for a marketing agency targeting US-based roofing contractors. The agent will execute a 500-dial outbound campaign, pitching a "Trojan Horse" offer: a completely free, custom-built roofing website. The ultimate business goal is to use this free upfront value to generate 10+ meaningful conversations, ultimately converting 1 to 2 roofers into paying clients for a $350 "Core Automation Hub" backend system.

2. Technical Stack

The system is optimized for ultra-low latency and maximum cost-efficiency, keeping the total campaign telecom and API costs under $7.00.

Orchestration & Hosting: LiveKit (Python Agents SDK, running on the free "Build" tier for 1,000 orchestration minutes).

Telephony (SIP Routing): SignalWire (using 2-4 local US phone numbers to avoid STIR/SHAKEN spam flags).

LLM (The Brain): Google Gemini 1.5 Flash (via Google AI Studio for blazing-fast conversational logic).

STT (The Ears): Deepgram (for real-time, low-latency speech-to-text).

TTS (The Voice): Microsoft Azure AI Speech (utilizing the 500,000 character free tier for natural neural voices).

3. Core Agent Capabilities (The Logic)

The Python application will not just act as a standard dialer; it must handle dynamic, real-world conversational edge cases.

Inbound vs. Outbound Routing: The system will check SIP metadata. If a roofer misses a cold call and calls the number back, the agent dynamically switches to an "Inbound" system prompt ("Hey, thanks for calling back, we reached out earlier...").

Voicemail Handling: Through system prompt instructions, the AI will listen for voicemail tones. If prompted to leave a message, it will pause for 2 seconds, read a specific 10-second voicemail drop script, and trigger a hangup function.

Data Extraction (Function Calling): The agent will be equipped with a Python Tool Call (save_lead_data). When a roofer agrees to receive the free website demo, the AI will ask them to spell out their email address or WhatsApp number. The AI will parse this spelling and trigger the Python function mid-conversation to save the lead to a local .csv file.

4. Execution Workflow

The Dialer (dialer.py): A script reads a list of targeted roofers from roofers.csv and uses the LiveKit Server API to trigger CreateSIPParticipant requests at a controlled, single-threaded pace.

The Bridge: SignalWire routes the outbound call to the roofer's cell phone and bridges the audio to the LiveKit cloud environment.

The Worker (agent.py): The LiveKit worker script drops the Gemini-powered voice agent into the room the moment the roofer answers the phone, managing the interruption logic (VAD) and conversational flow.









[ discussion about the free alternative of livekit]







Replacing LiveKit: 100% Free Alternatives

If you want to completely remove LiveKit from your tech stack, you must move to a self-hosted open-source architecture.

Here is exactly how you replace the three core components that LiveKit was handling for you, completely for free.

1. Replacing the Framework (The Logic)

LiveKit handles the complex math of Voice Activity Detection (VAD)—knowing when the AI should stop talking because the human interrupted.

The Free Replacement: You will use Pipecat (an open-source Python framework by Daily) or Vocode.

How it works: Just like LiveKit, you pip install pipecat-ai. It has built-in support for Gemini Flash, Deepgram, and Azure TTS. It handles the interruption logic and conversational flow perfectly for free.

2. Replacing the SIP Bridge (The Networking)

LiveKit was giving you a free SIP URI to paste into SignalWire.

The Free Replacement: You will use Daily's SIP Interconnect (which integrates directly with Pipecat) or a raw Python SIP library.

How it works: When SignalWire receives a call, it forwards it to your Pipecat SIP URI.

3. Replacing the Hosting (The Servers)

This is the biggest hurdle. LiveKit was hosting your Python script on their global servers for free. You now have to run this code yourself.

Option A: The "Localhost" Method (100% Free)

You can run the Pipecat Python script directly on your laptop in Bangladesh.

How to connect it: You use a free tool called Ngrok or Cloudflare Tunnels. This creates a public internet link that tunnels directly into your laptop. You paste that Ngrok link into SignalWire.

The Catch (Latency): SignalWire's servers are in the US. The roofer is in the US. If the audio has to travel from the US, across the ocean to your laptop in Bangladesh to be processed by your Python script, and then back to the US, it will add a 400ms to 600ms delay to the conversation. In Voice AI, a 500ms delay feels like an awkward, robotic pause. It will ruin the flow of the sales call.

Option B: The "Cheap Cloud" Method (~$4 to $5/month)

To fix the latency issue, your Python code must be hosted on a server in the United States, right next to SignalWire.

The Solution: You rent a tiny, unmanaged Linux VPS (Virtual Private Server) from Hetzner or DigitalOcean for roughly $4 to $5 a month.

How it works: You SSH into the server, upload your Pipecat code, and run it 24/7. Your latency drops to 10ms, and the AI sounds lightning-fast and human.

The Developer Reality Check

You mentioned earlier: "I really need money and I need one or two sales fast. I am already exhausted."

If speed to revenue is your #1 priority, do not replace LiveKit.

With LiveKit: You write the AI logic, hit "Deploy," and LiveKit handles all the complex networking, WebSocket chunking, and server management. You are making calls tomorrow.

With Pipecat + VPS / Ngrok: You have to manually configure Linux servers, handle Docker deployments, configure Ngrok tunnels, and fight with SIP networking errors. It turns a 1-day project into a 7-day DevOps headache.

The Verdict: Because LiveKit gives you 1,000 minutes of hosting completely for free, it is financially identical to hosting it yourself on Ngrok, but without the massive latency penalty or the DevOps exhaustion.












Replacing the 1,000 Minutes: The "Unlimited" Free Alternative

LiveKit tracks your 1,000 free minutes across two categories: Agent Compute Minutes (hosting the code) and SIP Minutes (routing the phone call).

If you abandon LiveKit, you trade those 1,000 metered minutes for unlimited unmetered minutes. Here is the exact 100% free replacement strategy.

1. Replacing "Agent Compute Minutes" (The Hosting)

LiveKit was running your Python script on their computers. To replace this for free (and avoid the terrible latency of running it on your laptop in Bangladesh), you will use an "Always Free" Cloud Server.

Major tech companies offer tiny US-based servers completely for free, forever, to get developers into their ecosystem.

The Replacements:

Google Cloud Compute Engine: Gives you 1 free e2-micro instance per month (located in the US).

Oracle Cloud: Gives you 2 free AMD Compute VMs.

AWS (Amazon): Gives you a free t2.micro server for your first 12 months.

How it works: You spin up a free Google Cloud e2-micro server in the United States. You SSH into it, upload your Pipecat (Open Source) Python code, and hit run.

The Result: Your code is now hosted in the US (solving the latency issue). Because you own the server, you can run the AI agent for unlimited minutes for $0.

2. Replacing the "SIP Minutes" (The Call Routing)

LiveKit was acting as the middleman bridge between the internet and SignalWire.

The Replacement: You will use the Pipecat SIP Transport library.

How it works: Pipecat has a built-in SIP server. When you run your Pipecat code on your free Google Cloud server, it opens a network port. You take the IP address of your Google Cloud server and paste it directly into your SignalWire dashboard.

The Result: SignalWire bypasses LiveKit entirely and sends the phone call directly to your free Google Cloud server. No middleman means unlimited SIP routing minutes for $0.

The Developer Reality (Why LiveKit is still recommended)

If you replace LiveKit with this "Pipecat + Free Google Cloud Server" method, your system will be 100% free and have unlimited minutes.

So why did I recommend staying with LiveKit for this campaign?

Because configuring a Linux server on Google Cloud, opening the correct SIP/RTP firewall ports, and keeping a Pipecat WebSocket connection stable requires serious DevOps engineering. If the server crashes mid-call, your AI hangs up on the roofer, and you have to manually reboot the server.

LiveKit gives you 1,000 minutes so you don't have to deal with Linux firewalls and server crashes. For a 500-dial validation campaign (which only uses 250 minutes), the 1,000 free LiveKit minutes are more than enough to get your first paying client without the DevOps headache.



[some features related with voicemail]




Call Handling: Voicemails, Extraction & Inbound Callbacks

When executing an AI outbound campaign, the actual conversation is only 50% of the battle. The other 50% is handling the edge cases: voicemails, data extraction, and missed call callbacks.

Here is how you program your LiveKit + SignalWire/Twilio stack to handle these seamlessly without adding complex external tools.

1. Voicemail Detection & Automated Drops

You asked if you have to leave voicemails manually. Absolutely not. Your AI can handle this automatically, and you have two ways to program it.

Method A: The SIP "AMD" Route (Answering Machine Detection)

When you use SignalWire or Twilio, their SIP network has built-in Answering Machine Detection (AMD).

Before connecting the call to your LiveKit server, Twilio/SignalWire listens for 2 seconds.

If it detects a machine, it can send a specific SIP Header or webhook payload to your code. Your Python script reads this flag and instantly plays a pre-recorded .mp3 file (your voicemail drop) and hangs up, saving LLM costs.

Method B: The "LLM Prompt" Route (Easiest for LiveKit)

If you don't want to mess with SIP headers, you just use your System Prompt.

You add this to your Groq/Gemini system instructions: "If the user says 'leave a message' or 'after the tone', you have reached a voicemail. Wait 2 seconds in silence, and then say exactly: 'Hey, it's 

$$Your Name$$

. I actually built a free custom website for your roofing company and just wanted to see if you wanted the link. Call me back at this number.' Then, trigger the hangup function."

The Result: The AI handles the voicemail dynamically, sounding completely human, and then hangs up.

2. Data Extraction: How to get the Email and Spelling

You asked how to get the exact spelling of their email or WhatsApp number without having to manually copy-paste the whole transcript into ChatGPT later.

The Solution: Function Calling (Tool Calling)

Both Groq (Llama 3) and Gemini Flash support "Function Calling." Because you are using LiveKit's Python framework, this is incredibly easy to set up.

Define a Python Function: In your LiveKit script, you write a standard Python function called save_lead_data(status, email, whatsapp_number). Inside this function, you write a simple line of code to save that data to a local .csv file or send it to a Google Sheet.

Give the Tool to the AI: You pass this function to your LLM plugin.

The Prompt Instructions: You tell the AI: "Your goal is to get their email address to send the demo. If they agree, ask them to spell it out letter by letter to ensure accuracy. Once they give you the email or phone number, IMMEDIATELY call the save_lead_data tool to save it."

The Result: The AI listens to the roofer spell "J - O - H - N @ G M A I L . C O M", parses it perfectly, and triggers your Python function in real-time while still on the phone. You don't need any extra external AI steps; the LLM does it mid-conversation.

3. Inbound Calling (The Missed Call Strategy)

You asked if you should have an inbound system on the same number for when they call you back. Yes, this is absolutely mandatory.

If you call 400 roofers, at least 40 of them will see a missed call from an unknown local number and call it back later that afternoon. If that number goes to a dead line or a generic robot, you just lost a warm lead.

How to set it up in LiveKit:

The SIP URI Routing: In your SignalWire/Twilio dashboard, you configure the phone number's "Inbound Webhook/SIP" settings. You point inbound calls to the exact same LiveKit SIP URI that you use for outbound.

The Logic Branch: In your Python code, when a call connects, you check the direction (Inbound vs. Outbound).

The Inbound Prompt: If the call is inbound, you load a different System Prompt into the AI: "You are an assistant for a marketing agency. The user is calling you back because they missed a call from us. Answer the phone by saying: 'Hey, thanks for calling back! We reached out earlier because we actually built a free custom website for your roofing company and wanted to see if we could send you the link...'"

The Verdict

By using Function Calling for data extraction and Conditional System Prompts for voicemails and inbound callbacks, your AI agent becomes a completely autonomous closed-loop system. You do not need to do any manual data entry or manual voicemail dropping.