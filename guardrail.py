import re

def moderate_reply(user_state, draft_reply, rules):
    """
    Moderates a draft reply based on a list of deterministic rules.
    
    Args:
        user_state (dict): Context about the user (jurisdiction, consent, etc.)
        draft_reply (str): The proposed reply from the agent.
        rules (list): List of rule dictionaries.
        
    Returns:
        dict: {
            "status": "ALLOW" | "BLOCK" | "REWRITE",
            "final_reply": str,
            "applied_rules": list[str],
            "reason": str (optional)
        }
    """
    current_reply = draft_reply
    applied_rule_ids = []
    is_rewritten = False
    status = "ALLOW"
    reason = None

    for rule in rules:
        rule_type = rule.get("type")
        rule_id = rule.get("id")
        params = rule.get("params", {})
        
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
                if user_state.get(field) != expected_value:
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
                    current_reply = truncated[:last_space_idx]
                else:
                    current_reply = truncated
                
                is_rewritten = True

    if is_rewritten:
        status = "REWRITE"

    return {
        "status": status,
        "final_reply": current_reply,
        "applied_rules": applied_rule_ids,
        "reason": reason
    }
