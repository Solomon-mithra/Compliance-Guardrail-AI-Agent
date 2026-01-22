import unittest
import json
from guardrail import ModerationSession

class TestStreaming(unittest.TestCase):
    
    def setUp(self):
        with open("rules.json", "r") as f:
            self.rules = json.load(f)
        
        self.default_state = {
            "consent_to_recording": False,
            "jurisdiction": "NY",
            "is_debt_collection": False
        }

    def test_early_block(self):
        """Test Case 1: Early block on partial chunks"""
        session = ModerationSession(user_state=self.default_state, rules=self.rules)
        
        # Chunk 1: "We guar" - Safe so far
        res1 = session.on_chunk("We guar")
        self.assertEqual(res1["status"], "ALLOW")
        self.assertEqual(res1["final_reply"], "We guar")
        
        # Chunk 2: "antee" - Completes "guarantee" -> BLOCK
        res2 = session.on_chunk("antee")
        self.assertEqual(res2["status"], "BLOCK")
        self.assertEqual(res2["final_reply"], "")
        self.assertTrue(session.blocked)
        self.assertIn("rule_block", res2["applied_rules"])

    def test_deferred_rewrite(self):
        """Test Case 2: Rewrites (phone) are deferred until finalize()"""
        session = ModerationSession(user_state=self.default_state, rules=self.rules)
        
        # Feed partial phone number
        session.on_chunk("Call 555")
        session.on_chunk("-123-4567")
        
        # Check buffer is intact
        self.assertEqual(session.buffer, "Call 555-123-4567")
        
        # Finalize should redact
        final_res = session.finalize()
        self.assertEqual(final_res["status"], "REWRITE")
        self.assertIn("[REDACTED_PHONE]", final_res["final_reply"])
        self.assertIn("rule_rewrite", final_res["applied_rules"])

    def test_finalize_all_rules(self):
        """Test Case 3: Finalize runs all rules (Require, Rewrite, MaxLength)"""
        # Ensure 'require' rule triggers
        state = self.default_state.copy()
        state["consent_to_recording"] = True
        
        session = ModerationSession(user_state=state, rules=self.rules)
        
        # Feed long text with phone
        session.on_chunk("Hello. Call 555-123-4567. ")
        session.on_chunk("This is a very long message that should definitely trigger the ")
        session.on_chunk("maximum length truncation rule because it is way over 80 chars.")
        
        final_res = session.finalize()
        
        # 1. Require phrase prepended?
        self.assertTrue(final_res["final_reply"].startswith("This call may be recorded."))
        
        # 2. Phone redacted?
        self.assertIn("[REDACTED_PHONE]", final_res["final_reply"])
        
        # 3. Truncated?
        self.assertLessEqual(len(final_res["final_reply"]), 80)
        self.assertFalse(final_res["final_reply"].endswith(" ")) # Check rstrip
        
        # Check rule IDs
        self.assertIn("rule_req", final_res["applied_rules"])
        self.assertIn("rule_rewrite", final_res["applied_rules"])
        self.assertIn("rule_max", final_res["applied_rules"])

if __name__ == '__main__':
    unittest.main()
