import unittest
import json
from guardrail import moderate_reply

class TestGuardrail(unittest.TestCase):
    
    def setUp(self):
        with open("rules.json", "r") as f:
            self.rules = json.load(f)
        
        # Valid default state for tests
        self.default_state = {
            "consent_to_recording": False,
            "jurisdiction": "NY",
            "is_debt_collection": False
        }

    
    def test_block_phrase(self):
        """Test Case 1: BLOCK_PHRASE logic"""
        # User state must be complete
        user_state = self.default_state.copy()
        draft_reply = "Hi, we guarantee you'll be approved."
        rules = [
            {
                "id": "block_guarantee",
                "type": "BLOCK_PHRASE",
                "params": {"phrases": ["guarantee", "likely"]}
            }
        ]
        
        result = moderate_reply(user_state, draft_reply, rules)
        
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["final_reply"], "")
        self.assertEqual(result["applied_rules"], ["block_guarantee"])
        self.assertIn("guarantee", result["reason"])

    def test_require_phrase(self):
        """Test Case 2: REQUIRE_PHRASE logic (and no double-prepend)"""
        user_state = self.default_state.copy()
        user_state["consent_to_recording"] = True
        
        draft_reply = "Hello there."
        rules = [
            {
                "id": "req_recording",
                "type": "REQUIRE_PHRASE",
                "params": {
                    "phrase": "This call may be recorded.",
                    "when": {"field": "consent_to_recording", "equals": True}
                }
            }
        ]
        
        # Sub-case A: Phrase missing -> Prepend
        result = moderate_reply(user_state, draft_reply, rules)
        self.assertEqual(result["status"], "REWRITE")
        self.assertEqual(result["final_reply"], "This call may be recorded. Hello there.")
        self.assertEqual(result["applied_rules"], ["req_recording"])
        self.assertEqual(result["reason"], "")
        
        # Sub-case B: Phrase present -> No change
        draft_reply_existing = "This call may be recorded. Hello there."
        result_existing = moderate_reply(user_state, draft_reply_existing, rules)
        self.assertEqual(result_existing["status"], "ALLOW")
        self.assertEqual(result_existing["final_reply"], "This call may be recorded. Hello there.")
        self.assertEqual(result_existing["applied_rules"], ["req_recording"]) # Still tracked
        self.assertEqual(result_existing["reason"], "")

    def test_rewrite_regex(self):
        """Test Case 3: REWRITE_REGEX redaction"""
        user_state = self.default_state.copy()
        draft_reply = "Call me at 555-123-4567 or 444-555-6666."
        rules = [
            {
                "id": "redact_phone",
                "type": "REWRITE_REGEX",
                "params": {
                    "pattern": r"\d{3}-\d{3}-\d{4}",
                    "replacement": "[REDACTED]"
                }
            }
        ]
        
        result = moderate_reply(user_state, draft_reply, rules)
        self.assertEqual(result["status"], "REWRITE")
        self.assertEqual(result["final_reply"], "Call me at [REDACTED] or [REDACTED].")
        self.assertEqual(result["applied_rules"], ["redact_phone"])

    def test_max_length(self):
        """Test Case 4: MAX_LENGTH truncation logic"""
        user_state = self.default_state.copy()
        draft_reply = "Short message."
        rules = [
            {
                "id": "max_len",
                "type": "MAX_LENGTH",
                "params": {"max_chars": 10}
            }
        ]
        
        result = moderate_reply(user_state, draft_reply, rules)
        self.assertEqual(result["status"], "REWRITE")
        self.assertEqual(result["final_reply"], "Short") 
        self.assertEqual(result["applied_rules"], ["max_len"])
        
        # Edge case: No whitespace
        draft_reply_long = "Supercalifragilisticexpialidocious"
        rules[0]["params"]["max_chars"] = 5
        result_hard = moderate_reply(user_state, draft_reply_long, rules)
        self.assertEqual(result_hard["final_reply"], "Super")

    def test_complex_flow(self):
        """Test Case 5: Complex multi-rule flow & Invalid Regex Edge Case"""
        user_state = {
            "consent_to_recording": True, 
            "jurisdiction": "CA", 
            "is_debt_collection": True
        }
        draft_reply = "Hi, we guarantee nothing. Call 555-123-4567."
        
        rules = [
            # 1. Require "This call may be recorded."
            {
                "id": "rule_req",
                "type": "REQUIRE_PHRASE",
                "params": {
                    "phrase": "This call may be recorded.",
                    "when": {"field": "consent_to_recording", "equals": True}
                }
            },
            # 2. Invalid Regex (Should be ignored but tracked)
            {
                "id": "rule_bad_regex",
                "type": "REWRITE_REGEX",
                "params": {
                    "pattern": "[", # Invalid
                    "replacement": ""
                }
            },
            # 3. Redact Phone
            {
                "id": "rule_redact",
                "type": "REWRITE_REGEX",
                "params": {
                    "pattern": r"\d{3}-\d{3}-\d{4}",
                    "replacement": "[PHONE]"
                }
            },
            # 4. Max Length (set high enough to encompass valid output)
            {
                "id": "rule_max",
                "type": "MAX_LENGTH",
                "params": {"max_chars": 100}
            }
        ]
        
        result = moderate_reply(user_state, draft_reply, rules)
        
        expected_reply = "This call may be recorded. Hi, we guarantee nothing. Call [PHONE]."
        self.assertEqual(result["status"], "REWRITE")
        self.assertEqual(result["final_reply"], expected_reply)
        # All rules should be in applied_rules now
        self.assertEqual(result["applied_rules"], ["rule_req", "rule_bad_regex", "rule_redact", "rule_max"])


    def test_external_rules_configuration(self):
        """Test Case 6: Verify rules.json configuration works as expected"""
        # This test uses the actual rules.json file
        user_state = {
            "consent_to_recording": True,
            "jurisdiction": "CA",
            "is_debt_collection": True
        }
        draft_reply = "Hi, we guarantee detection. Call 555-123-4567."
        
        # rules.json contains: Block(guarantee), Require(recording), Rewrite(phone), MaxLength(80)
        
        # 1. "guarantee" should trigger BLOCK immediately
        result = moderate_reply(user_state, draft_reply, self.rules)
        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["applied_rules"], ["rule_block"])
        
        # Test 2: Safe message that needs rewrite
        draft_reply_safe = "Please call 555-123-4567."
        result_safe = moderate_reply(user_state, draft_reply_safe, self.rules)
        
        # Should:
        # 1. Require "This call may be recorded." -> Prepend
        # 2. Rewrite phone -> [REDACTED_PHONE]
        
        expected_reply = "This call may be recorded. Please call [REDACTED_PHONE]."
        self.assertEqual(result_safe["status"], "REWRITE")
        self.assertEqual(result_safe["final_reply"], expected_reply)
        self.assertIn("rule_req", result_safe["applied_rules"])
        self.assertIn("rule_rewrite", result_safe["applied_rules"])

if __name__ == '__main__':
    unittest.main()
