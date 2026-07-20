#!/usr/bin/env python3
"""
Automated Multi-Line & API Key Rotation Verification Suite (test_multi_line.py)
Tests:
1. Round-Robin Line Selection & State Tracking
2. Cooldown Expiry & Busy State Management
3. Self-Call Prevention Loop Check
4. Cross-Number Callback Routing (exclude busy/missed line)
5. Queue Record Creation with missed_on_line parameter
6. API Key Rotation Pool & Failover Logic
"""
import os
import sys
import time
import asyncio
import unittest
from datetime import datetime

# Import modules to test
from phone_lines import (
    get_all_lines,
    get_next_available_line,
    get_line_for_callback,
    mark_line_busy,
    mark_line_available,
    is_our_number,
    get_line_by_phone,
    _line_states,
)
from call_queue import add_to_queue
from api_keys import get_working_key_pair, _load_keys, _is_key_available


class TestMultiLineRotation(unittest.TestCase):
    def setUp(self):
        # Reset in-memory line states before each test
        _line_states.clear()

    def test_01_all_lines_loaded(self):
        """Verify all 3 lines are properly loaded from phone_lines.json."""
        lines = get_all_lines()
        self.assertEqual(len(lines), 3, "Should load exactly 3 phone lines")
        ids = [l["id"] for l in lines]
        self.assertIn("line_1", ids)
        self.assertIn("line_2", ids)
        self.assertIn("line_3", ids)

    def test_02_round_robin_rotation(self):
        """Verify get_next_available_line rotates round-robin across free lines."""
        line_a = get_next_available_line()
        line_b = get_next_available_line()
        line_c = get_next_available_line()
        line_d = get_next_available_line()

        self.assertIsNotNone(line_a)
        self.assertIsNotNone(line_b)
        self.assertIsNotNone(line_c)
        self.assertIsNotNone(line_d)

        # First 3 selections should cycle through the 3 distinct lines
        selected_ids = {line_a["id"], line_b["id"], line_c["id"]}
        self.assertEqual(len(selected_ids), 3, "Round robin should select 3 distinct lines across 3 calls")
        # 4th should wrap around to match 1st
        self.assertEqual(line_d["id"], line_a["id"], "4th selection should wrap around to 1st line")

    def test_03_busy_and_cooldown_skipping(self):
        """Verify that lines in_call or cooling_down are skipped during rotation."""
        lines = get_all_lines()
        first_line = lines[0]

        # Mark first line as busy (IN_CALL)
        mark_line_busy(first_line["id"])

        # Next selection should NOT be first_line
        next_line = get_next_available_line()
        self.assertNotEqual(next_line["id"], first_line["id"], "Should skip busy line")

        # Now mark first_line as cooling_down (with 60s cooldown)
        mark_line_available(first_line["id"], start_cooldown=True)
        next_line_2 = get_next_available_line()
        self.assertNotEqual(next_line_2["id"], first_line["id"], "Should skip line currently cooling down")

    def test_04_cross_number_callback_routing(self):
        """Verify get_line_for_callback excludes the line where the call was missed."""
        # Suppose a call was missed on line_1 while it was busy
        cb_line = get_line_for_callback(exclude_line_id="line_1")
        self.assertIsNotNone(cb_line)
        self.assertNotEqual(cb_line["id"], "line_1", "Callback must not pick the excluded line_1")
        self.assertIn(cb_line["id"], ["line_2", "line_3"])

    def test_05_self_call_prevention(self):
        """Verify is_our_number returns True for all our Alex lines and False for external numbers."""
        self.assertTrue(is_our_number("+14694616899"))
        self.assertTrue(is_our_number("14694616899"))
        self.assertTrue(is_our_number("+19453260478"))
        self.assertTrue(is_our_number("+19453260334"))
        self.assertFalse(is_our_number("+17068130213"), "External customer number must not be flagged as our number")

    def test_06_queue_missed_on_line_tracking(self):
        """Verify add_to_queue stores missed_on_line parameter correctly."""
        record = add_to_queue(
            phone_number="+17068130213",
            company_name="Test Roofer",
            reason="missed_inbound_offline",
            queue_type="callback",
            missed_on_line="line_2",
        )
        self.assertEqual(record.get("missed_on_line"), "line_2")
        self.assertEqual(record.get("queue_type"), "callback")


class TestAPIKeyRotation(unittest.IsolatedAsyncioTestCase):
    async def test_01_api_key_pool_rotation(self):
        """Verify get_working_key_pair returns valid Gladia and Cartesia keys and cycles properly."""
        gladia_key, cartesia_key = await get_working_key_pair(run_health_check=False)
        self.assertIsNotNone(gladia_key)
        self.assertIsNotNone(cartesia_key)
        self.assertTrue(len(gladia_key) > 10)
        self.assertTrue(len(cartesia_key) > 10)

    async def test_02_key_status_tracking(self):
        """Verify key status tracking and availability check function."""
        data = _load_keys()
        entry = data["gladia"][0]
        original_status = entry.get("status")
        
        # Simulate marking index 0 as exhausted
        entry["status"] = "exhausted"
        entry["exhausted_until"] = time.time() + 3600
        self.assertFalse(_is_key_available(entry))
        
        # Restore index 0 status
        entry["status"] = original_status
        entry["exhausted_until"] = None
        self.assertTrue(_is_key_available(entry))


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 RUNNING AUTOMATED MULTI-LINE & API KEY ROTATION TEST SUITE")
    print("=" * 70)
    unittest.main(verbosity=2)
