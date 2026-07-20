# LiveKit Telephony Current Configuration & Setup Analysis

This document records the exact configuration extracted from the LiveKit dashboard screenshots provided on 2026-07-18, and analyzes what can be reused versus what needs to be created fresh for our 3-number rotation system.

---

## 1. Project & SIP URI Details
- **Project ID / SIP Domain Prefix:** `4zah1qs1e7j`
- **Global SIP Inbound URI:** `sip:4zah1qs1e7j.sip.livekit.cloud`
- **Project Name:** `ex11`

---

## 2. Inbound SIP Trunks (`TOTAL INBOUND TRUNKS: 1`)

### Trunk 1: `SignalWire Inbound Trunk`
- **Trunk ID:** `ST_jqoyBZhdL2Ps`
- **Trunk Name:** `SignalWire Inbound Trunk`
- **Direction:** `Inbound`
- **Numbers Configured:** `+14694616899,4zah1qs1e7j,anonymous,default`
  *(Note: The overview badge shows `+14694616899 [+3]` because of the 3 extra strings/wildcards (`4zah1qs1e7j`, `anonymous`, `default`)*
- **Allowed Addresses:** `0.0.0.0/0` (Allows inbound traffic from any SignalWire IP)
- **Media Encryption (SRTP):** `Media encryption disabled`
- **Include Headers:** `No headers`
- **Created At:** `17 Jul 2026, 09:57:20`

---

## 3. Outbound SIP Trunks (`TOTAL OUTBOUND TRUNKS: 1`)

### Trunk 1: `SignalWire Outbound` (Line 1 Outbound)
- **Trunk ID:** `ST_PRdJLAHpjkg3`
- **Trunk Name:** `SignalWire Outbound`
- **Direction:** `Outbound`
- **Address / Domain:** `ch-solutions-outbound.dapp.signalwire.com`
- **Transport:** `Auto`
- **Numbers Configured:** `+14694616899`
- **Media Encryption (SRTP):** `Media encryption disabled`
- **Username:** `livekit-agent`
- **Password:** `********` *(Masked)*
- **Created At:** `4 Jul 2026, 19:59:47`

---

## 4. Dispatch Rules (`TOTAL DISPATCH RULES: 1`)

### Rule 1: `Roofer Inbound Callback Rule`
- **Rule Name:** `Roofer Inbound Callback Rule`
- **Rule Type:** `Individual` (Creates an individual LiveKit room for each incoming call)
- **Room Prefix / Destination Room:** `inbound_call_<caller-number>` (Specifically set to `inbound_call_` in editor)
- **Agent Dispatch:** `No agents selected` *(Note: Since `agent.py` connects via `AutoSubscribe` or checks `inbound_call_` rooms dynamically, or relies on SIP attributes, worker entry points connect automatically)*
- **Inbound Routing / Filtering:** `No number or trunk is selected, the rule will be applied to all.` (Any call entering `sip:4zah1qs1e7j.sip.livekit.cloud` gets routed to `inbound_call_<caller-number>`)
- **Created At:** `4 Jul 2026, 20:18:02`
- **Updated At:** `17 Jul 2026, 09:58:22`

---

## 5. Evaluation: What to Reuse vs. What to Create Fresh

### ✅ What We Can Reuse Exactly As-Is (No changes needed):
1. **Inbound SIP Trunk (`ST_jqoyBZhdL2Ps`):**
   - **Reuse Status:** **REUSE AS-IS (with minor number addition).**
   - Because `Allowed addresses` is `0.0.0.0/0` and it accepts `anonymous/default`, any inbound call coming from SignalWire to your LiveKit SIP URI (`sip:4zah1qs1e7j.sip.livekit.cloud`) is already accepted by this trunk.
   - **Optional Enhancement:** We can simply add your two other numbers (`+19453260478` and `+19453260334`) to the `Numbers` field of this single Inbound Trunk (`+14694616899,+19453260478,+19453260334,4zah1qs1e7j,anonymous,default`), OR leave it accepting all anonymous/default calls. No new inbound trunks needed!

2. **Dispatch Rule (`Roofer Inbound Callback Rule`):**
   - **Reuse Status:** **REUSE AS-IS.**
   - Since it applies to **all** incoming calls across all trunks/numbers and directs them to `inbound_call_<caller-number>`, whenever someone calls back Line 1, Line 2, or Line 3, they will land in an `inbound_call_...` room. Our `agent.py` and `missed_call_watcher.py` already track `inbound_call_` and check `sip.callTo` to know which line was dialed.

3. **Line 1 Outbound Trunk (`ST_PRdJLAHpjkg3`):**
   - **Reuse Status:** **REUSE AS-IS.**
   - This trunk is already configured for `+14694616899` and is currently active as `line_1` in our `phone_lines.json`.

---

### 🆕 What We Need to Create Fresh (For Lines 2 & 3 Outbound Calling):
Because LiveKit requires each Outbound SIP Trunk to be tied to a specific caller ID / SIP configuration when making outbound calls, we need two new outbound trunks to enable round-robin outbound calling from Lines 2 and 3:

1. **Line 2 Outbound Trunk (`SignalWire Outbound Line 2`):**
   - **Action:** Create **Fresh** in LiveKit under `Telephony` → `SIP Trunks` → `Create new trunk` → `Outbound`.
   - **Trunk Name:** `SignalWire Outbound Line 2`
   - **Address:** `ch-solutions-outbound.dapp.signalwire.com` *(Same as Line 1)*
   - **Transport:** `Auto`
   - **Numbers:** `+19453260478`
   - **Username:** `livekit-agent` *(Or your SignalWire SIP credentials)*
   - **Password:** *(Your SignalWire SIP password)*
   - **Result:** Will generate a new Trunk ID (`ST_...`) which we put into `phone_lines.json` for `line_2`.

2. **Line 3 Outbound Trunk (`SignalWire Outbound Line 3`):**
   - **Action:** Create **Fresh** in LiveKit under `Telephony` → `SIP Trunks` → `Create new trunk` → `Outbound`.
   - **Trunk Name:** `SignalWire Outbound Line 3`
   - **Address:** `ch-solutions-outbound.dapp.signalwire.com` *(Same as Line 1)*
   - **Transport:** `Auto`
   - **Numbers:** `+19453260334`
   - **Username:** `livekit-agent` *(Or your SignalWire SIP credentials)*
   - **Password:** *(Your SignalWire SIP password)*
   - **Result:** Will generate a new Trunk ID (`ST_...`) which we put into `phone_lines.json` for `line_3`.

---

## 6. SignalWire Telephony Current Configuration

Extracted from the 4 SignalWire screenshots provided on 2026-07-18 (`CH Solutions` Space):

### A. Phone Number Inbound Routing (`+1 (469) 461-6899`)
- **Phone Number:** `+1 (469) 461-6899`
- **Friendly Name:** `+1 (469) 461-6899`
- **Inbound Call Settings → Assigned Resource:** `Route to LiveKit` *(This resource forwards incoming calls directly to your LiveKit SIP domain `sip:4zah1qs1e7j.sip.livekit.cloud`)*
- **Inbound Message Settings:** Unassigned (`+ Assign Resource`)

### B. SIP Credential Resource (`livekit-agent`)
- **Resource ID:** `b8859637-1b80-4d93-ba54-4d378d00cd45`
- **Resource Type:** `SIP Credential`
- **SIP URI:** `livekit-agent@ch-solutions-6feb4b2c8c97.sip.signalwire.com`
- **Password:** `********` *(Masked)*
- **Associated With:** `1 Address`
- **Last Registered:** `Never` *(Note: Since LiveKit cloud connects via outbound trunk SIP requests or IP authentication, registration state may show never depending on mode)*

### C. SIP Credential Caller ID & Encryption Settings
- **Send As:** `Use Default Behavior`
- **SIP Caller ID:** `+1 (469) 461-6899` *(CRITICAL: This SIP Credential `livekit-agent` is currently hardcoded to send `+1 (469) 461-6899` as the outbound caller ID when dialing out to PSTN!)*
- **Encryption:** `Use Default Setting`
- **Codecs & Ciphers:** `Default Codecs`, `Default Ciphers`

### D. SIP Credential Call Handler Settings
- **Call Handler:** `a Resource`
- **Assigned Resource:** `Outbound to PSTN` *(Routes outbound SIP calls initiated by `livekit-agent` directly to external phone numbers on the public telephone network using the hardcoded SIP Caller ID)*

---

## 7. End-to-End Evaluation & Recommendations (LiveKit + SignalWire)

### Why Outbound Caller ID Needs Attention for Multi-Line Rotation:
Currently, your LiveKit Outbound Trunk authenticates with SignalWire using the username `livekit-agent`. In SignalWire, the `livekit-agent` SIP Credential has its **SIP Caller ID** hardcoded to `+1 (469) 461-6899`.
That means even if we create new outbound trunks in LiveKit for `+19453260478` (Line 2) and `+19453260334` (Line 3) using the same `livekit-agent` username/password, SignalWire will override and force the caller ID to show as `+1 (469) 461-6899` for all calls!

### How to Configure SignalWire for Lines 2 & 3 Outbound Calling:
To ensure each line displays its own distinct phone number when calling leads:

1. **Option 1 (Recommended & Cleanest — Separate SIP Credentials per Line):**
   - In SignalWire under **My Resources** → **SIP**, create two new SIP Credentials:
     - **SIP Credential 2:** Username `livekit-agent-line2`, set **SIP Caller ID** to `+1 (945) 326-0478`, Assigned Resource `Outbound to PSTN`.
     - **SIP Credential 3:** Username `livekit-agent-line3`, set **SIP Caller ID** to `+1 (945) 326-0334`, Assigned Resource `Outbound to PSTN`.
   - Then in LiveKit, enter `livekit-agent-line2` for the Line 2 Outbound Trunk, and `livekit-agent-line3` for the Line 3 Outbound Trunk.

2. **Inbound Routing for Lines 2 & 3:**
   - In SignalWire under **Phone Numbers**, click `+1 (945) 326-0478` and `+1 (945) 326-0334`.
   - Set **Inbound Call Settings → Assigned Resource** to `Route to LiveKit` *(or dedicated inbound scripts per line)*.

---

## 8. SWML Scripts Analysis (`Outbound to PSTN` & `Route to LiveKit`)

Extracted from the 4 additional SWML Script screenshots provided on 2026-07-18 (`CH Solutions` Space under **My Resources → Scripts**):

### A. `Outbound to PSTN` (SWML Script for Outbound Calls)
- **Resource ID:** `f3fc1a79-e37b-4bf1-ab84-48770374f46b`
- **Script Type:** `Calling`
- **Associated With:** `2 Addresses`
- **SWML Code:**
  ```yaml
  version: 1.0.0
  sections:
    main:
      - connect:
          answer_on_bridge: true
          from: "+14694616899"
          to: "%{call.to.replace(/^sip:/i, '').replace(/@.*/, '')}"
  ```
- **Critical Discovery:** Notice `from: "+14694616899"`. This script hardcodes the outbound caller ID! Whenever any SIP Credential uses this script to dial out, the script overrides the caller ID and sends `+14694616899` to the telephone network.

### B. `Route to LiveKit` (SWML Script for Inbound Calls)
- **Resource ID:** `34b0ec56-74e8-48ee-b4fb-b4abd34058b8`
- **Script Type:** `Calling`
- **Associated With:** `2 Addresses`
- **SWML Code:**
  ```json
  {
    "version": "1.0.0",
    "sections": {
      "main": [
        {
          "answer": {}
        },
        {
          "connect": {
            "to": "sip:+14694616899@4zah1qs1e7j.sip.livekit.cloud"
          }
        }
      ]
    }
  }
  ```
- **Critical Discovery:** Notice `"to": "sip:+14694616899@4zah1qs1e7j.sip.livekit.cloud"`. This script answers incoming calls and forwards them to LiveKit specifically as `+14694616899`. If Lines 2 or 3 are pointed to this exact script without changes, incoming calls on Lines 2 & 3 will arrive in LiveKit looking like `+14694616899`.

---

## 9. Final Answer: Can We Just Add Numbers to Existing Trunks?

**Answer:** If we just add multiple numbers into the existing LiveKit outbound/inbound trunks without updating these two SWML scripts, **it will NOT work correctly for multi-number rotation** because:
1. Every outbound call across all 3 lines would go out displaying `+14694616899` (due to `from: "+14694616899"` inside `Outbound to PSTN`).
2. Every inbound call across all 3 lines would arrive at LiveKit forwarded to `sip:+14694616899@...` (due to `"to": "sip:+14694616899@..."` inside `Route to LiveKit`), making it impossible for `missed_call_watcher.py` to know which specific roofer number (`+19453260478` vs `+19453260334`) was dialed.

### The Two Solutions to Fix This:

#### Solution A (Dynamic Scripts — Simplest if you want to keep fewer resources):
1. **Update `Outbound to PSTN` SWML:** Change `from: "+14694616899"` to dynamic `from: "%{call.from}"` (so it dynamically uses whichever SIP Caller ID is passed by the calling trunk/credential).
2. **Update `Route to LiveKit` SWML:** Change `"to": "sip:+14694616899@..."` to dynamic `"to": "sip:%{call.to}@4zah1qs1e7j.sip.livekit.cloud"` (so incoming calls on any number get forwarded cleanly with their actual destination phone number).

#### Solution B (Dedicated Scripts & Trunks per Line — Most robust & transparent):
1. Create dedicated SWML scripts for each line:
   - `Outbound to PSTN Line 2` (with `from: "+19453260478"`)
   - `Outbound to PSTN Line 3` (with `from: "+19453260334"`)
   - `Route to LiveKit Line 2` (with `"to": "sip:+19453260478@4zah1qs1e7j.sip.livekit.cloud"`)
   - `Route to LiveKit Line 3` (with `"to": "sip:+19453260334@4zah1qs1e7j.sip.livekit.cloud"`)
2. Create dedicated SIP Credentials and LiveKit Outbound Trunks for Line 2 and Line 3.
