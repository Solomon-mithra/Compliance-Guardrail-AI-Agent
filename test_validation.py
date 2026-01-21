import unittest
from pydantic import ValidationError
# Import from the venv environment is expected when running "python3 -m unittest" via the venv
# The local relative import should work if running from the root
from guardrail import moderate_reply
from models import Rule

class TestValidation(unittest.TestCase):
    
    def test_valid_input(self):
        """Test with completely valid input"""
        user_state = {
            "consent_to_recording": True,
            "jurisdiction": "CA",
            "is_debt_collection": True
        }
        draft_reply = "Hello"
        rules = [
            {
                "id": "r1",
                "type": "BLOCK_PHRASE",
                "params": {"phrases": ["bad"]}
            }
        ]
        result = moderate_reply(user_state, draft_reply, rules)
        self.assertEqual(result["status"], "ALLOW")

    def test_missing_field_user_state(self):
        """Test missing required field in user_state"""
        user_state = {
            "jurisdiction": "CA" 
            # Missing consent_to_recording, is_debt_collection
        }
        draft_reply = "Hello"
        rules = []
        
        with self.assertRaises(ValidationError) as cm:
            moderate_reply(user_state, draft_reply, rules)
        
        errors = cm.exception.errors()
        self.assertTrue(any(e['loc'] == ('user_state', 'consent_to_recording') for e in errors))

    def test_invalid_rule_type(self):
        """Test invalid rule type"""
        user_state = {
            "consent_to_recording": True, 
            "jurisdiction": "CA", "is_debt_collection": True
        }
        draft_reply = "Hello"
        rules = [
            {
                "id": "r1",
                "type": "INVALID_TYPE",
                "params": {}
            }
        ]
        
        with self.assertRaises(ValidationError) as cm:
            moderate_reply(user_state, draft_reply, rules)
            
    def test_strict_string_phrases(self):
        """Test stricter validation: BLOCK_PHRASE phrases must be strings"""
        user_state = {
            "consent_to_recording": True, 
            "jurisdiction": "CA", "is_debt_collection": True
        }
        draft_reply = "Hello"
        # Phrases contains an int, should fail
        rules = [
            {
                "id": "r1",
                "type": "BLOCK_PHRASE",
                "params": {"phrases": ["bad", 123]}
            }
        ]
        
        with self.assertRaises(ValidationError) as cm:
            moderate_reply(user_state, draft_reply, rules)
        
        # Check if the error message mentions the specific value error
        # Note: Pydantic wrapping might hide the custom ValueError string in 'msg', let's check.
        self.assertIn("strings", str(cm.exception))

    def test_strict_string_replacement(self):
        """Test stricter validation: REWRITE_REGEX replacement must be string"""
        user_state = {
            "consent_to_recording": True, 
            "jurisdiction": "CA", "is_debt_collection": True
        }
        draft_reply = "Hello"
        # Replacement is None (not string) or int
        rules = [
            {
                "id": "r1",
                "type": "REWRITE_REGEX",
                "params": {"pattern": "foo", "replacement": 123}
            }
        ]
        
        with self.assertRaises(ValidationError) as cm:
            moderate_reply(user_state, draft_reply, rules)
            
        self.assertIn("must be a string", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
