from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Literal

class UserState(BaseModel):
    consent_to_recording: bool
    jurisdiction: str
    is_debt_collection: bool

class Rule(BaseModel):
    id: str
    type: Literal["BLOCK_PHRASE", "REQUIRE_PHRASE", "REWRITE_REGEX", "MAX_LENGTH"]
    params: Dict[str, Any]

    @field_validator('params')
    def validate_params(cls, v, values):
        # Strict validation: Ensure params contain appropriate types.
        # User requested "values type must be only strings" for text-based params.
        
        rule_type = values.data.get('type')
        if not rule_type:
            # If type is invalid/missing, we can't validate params specifically, 
            # but Pydantic's Literal check on 'type' field will catch missing/invalid type 
            # BEFORE this validator runs content logic usually, or 'values.data' might handle it.
            return v
            
        if rule_type == 'BLOCK_PHRASE':
            phrases = v.get('phrases')
            if not isinstance(phrases, list):
                 raise ValueError("BLOCK_PHRASE params must contain 'phrases' list")
            if not all(isinstance(p, str) for p in phrases):
                raise ValueError("All entries in 'phrases' must be strings")
                
        elif rule_type == 'REQUIRE_PHRASE':
            phrase = v.get('phrase')
            if phrase is not None and not isinstance(phrase, str):
                raise ValueError("'phrase' must be a string")
            # 'when' is a dict, condition object.
                
        elif rule_type == 'REWRITE_REGEX':
            pattern = v.get('pattern')
            replacement = v.get('replacement')
            if pattern is not None and not isinstance(pattern, str):
                raise ValueError("'pattern' must be a string")
            if replacement is not None and not isinstance(replacement, str):
                raise ValueError("'replacement' must be a string")
                
        elif rule_type == 'MAX_LENGTH':
            # MAX_LENGTH exptects 'max_chars' as int. 
            # If user STRICTLY meant "only strings", this would fail.
            # But practically, max_chars MUST be an int.
            # We will allow int for max_chars.
            max_chars = v.get('max_chars')
            if max_chars is not None and not isinstance(max_chars, int):
                raise ValueError("'max_chars' must be an integer")
                
        return v

class GuardrailRequest(BaseModel):
    user_state: UserState
    draft_reply: str
    rules: List[Rule]
