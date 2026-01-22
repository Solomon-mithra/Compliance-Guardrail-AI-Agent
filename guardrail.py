import re

from models import GuardrailRequest

def moderate_reply(user_state, draft_reply, rules):
    """
    Moderates a draft reply based on a list of deterministic rules.
    """
    # Validate Inputs using Pydantic
    # This throws ValidationError if inputs are invalid
    request = GuardrailRequest(
        user_state=user_state,
        draft_reply=draft_reply,
        rules=rules or []
    )
    
    # Use validated data
    current_reply = request.draft_reply
    user_state_obj = request.user_state # Pydantic model
    rules_objs = request.rules # List of Rule models
    
    applied_rule_ids = []
    is_rewritten = False
    status = "ALLOW"
    reason = None

    for rule in rules_objs:
        rule_type = rule.type
        rule_id = rule.id
        params = rule.params
        
        # Always track that we are processing this rule
        applied_rule_ids.append(rule_id)

        if rule_type == "BLOCK_PHRASE":
            phrases = params.get("phrases", [])
            lower_reply = current_reply.lower()
            for phrase in phrases:
                if phrase.lower() in lower_reply:
                    return {
                        "status": "BLOCK",
                        "final_reply": "",
                        "applied_rules": applied_rule_ids,
                        "reason": f"Blocked phrase: {phrase}"
                    }

        elif rule_type == "REQUIRE_PHRASE":
            phrase = params.get("phrase")
            condition = params.get("when")
            
            condition_met = True
            if condition:
                field = condition.get("field")
                expected_value = condition.get("equals")
                # Access user_state fields via Pydantic model (dot attribute) or getattr 
                # user_state_obj is a Pydantic model now
                if getattr(user_state_obj, field, None) != expected_value:
                    condition_met = False
            
            if condition_met and phrase:
                # Check using exact substring match as per spec
                if phrase not in current_reply:
                    current_reply = f"{phrase} {current_reply}"
                    is_rewritten = True

        elif rule_type == "REWRITE_REGEX":
            pattern = params.get("pattern")
            replacement = params.get("replacement")
            
            if pattern and replacement is not None:
                try:
                    new_reply = re.sub(pattern, replacement, current_reply)
                    if new_reply != current_reply:
                        current_reply = new_reply
                        is_rewritten = True
                except re.error:
                    # Invalid regex: treat as no-op but still recorded in applied_rules
                    pass

        elif rule_type == "MAX_LENGTH":
            max_chars = params.get("max_chars")
            if max_chars is not None and len(current_reply) > max_chars:
                truncated = current_reply[:max_chars]
                
                last_space_idx = -1
                for i in range(len(truncated) - 1, -1, -1):
                    if truncated[i].isspace():
                        last_space_idx = i
                        break
                
                if last_space_idx != -1:
                    current_reply = truncated[:last_space_idx].rstrip()
                else:
                    current_reply = truncated.rstrip()
                
                is_rewritten = True

    if is_rewritten:
        status = "REWRITE"

    return {
        "status": status,
        "final_reply": current_reply,
        "applied_rules": applied_rule_ids,
        "reason": reason or ""
    }

def early_block_check(current_text: str, rules_objs) -> tuple[bool, str | None, str | None]:
    """
    Returns: (should_block, reason, rule_id)
    Only checks fast BLOCK_PHRASE rules (or any other early-block rules you decide).
    """
    lower_text = current_text.lower()

    for rule in rules_objs:
        if rule.type == "BLOCK_PHRASE":
            phrases = rule.params.get("phrases", []) or []
            for phrase in phrases:
                if phrase and phrase.lower() in lower_text:
                    return True, f"Blocked phrase: {phrase}", rule.id

    return False, None, None

from dataclasses import dataclass, field

@dataclass
class ModerationSession:
    user_state: dict
    rules: list
    buffer: str = ""
    applied_rules: list[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None
    block_rule_id: str | None = None

    def _validate(self):
        # reuse your Pydantic validation once per session
        req = GuardrailRequest(user_state=self.user_state, draft_reply="", rules=self.rules or [])
        return req.user_state, req.rules

    def on_chunk(self, text_delta: str) -> dict[str, any]:
        """
        Called whenever you receive a partial transcript chunk.
        """
        if self.blocked:
            return {
                "status": "BLOCK",
                "final_reply": "",
                "applied_rules": self.applied_rules,
                "reason": self.block_reason or "Blocked"
            }

        # Append new text
        self.buffer += text_delta

        user_state_obj, rules_objs = self._validate()

        # Early block check
        should_block, reason, rid = early_block_check(self.buffer, rules_objs)

        # For auditability, record that we evaluated early-block rules (optional granularity)
        # Simplest: record only when block happens
        if should_block:
            self.blocked = True
            self.block_reason = reason
            self.block_rule_id = rid
            self.applied_rules.append(rid)

            return {
                "status": "BLOCK",
                "final_reply": "",
                "applied_rules": self.applied_rules,
                "reason": reason
            }

        # Otherwise we don't rewrite on partials; we just say "ALLOW so far"
        return {
            "status": "ALLOW",
            "final_reply": self.buffer,   # or "" if you don't want to expose partial
            "applied_rules": self.applied_rules,
            "reason": ""
        }

    def finalize(self) -> dict[str, any]:
        """
        Called when the transcript is final for this turn.
        Runs full moderation and returns final decision.
        """
        if self.blocked:
            return {
                "status": "BLOCK",
                "final_reply": "",
                "applied_rules": self.applied_rules,
                "reason": self.block_reason or "Blocked"
            }

        # Run the full moderation on the finalized text
        result = moderate_reply(self.user_state, self.buffer, self.rules)

        # Merge applied rules from early stage + full pass (avoid duplicates if you want)
        merged = self.applied_rules + [rid for rid in result.get("applied_rules", []) if rid not in self.applied_rules]
        result["applied_rules"] = merged
        return result
