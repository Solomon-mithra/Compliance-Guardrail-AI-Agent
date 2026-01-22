import json
import sys
from pydantic import ValidationError
from guardrail import moderate_reply

def main():
    # Load rules from external file
    try:
        with open("rules.json", "r") as rf:
            rules = json.load(rf)
    except FileNotFoundError:
        print("Error: rules.json not found.")
        sys.exit(1)

    if len(sys.argv) > 1:
        # Read from file if provided
        with open(sys.argv[1], 'r') as f:
            data = json.load(f)
    else:
        # Read from stdin
        try:
            data = json.load(sys.stdin)
        except json.JSONDecodeError:
            print("Error: Please provide input via file argument or pipe JSON to stdin.")
            sys.exit(1)

    user_state = data.get("user_state")
    draft_reply = data.get("draft_reply")
    is_stream = data.get("stream", False)
    
    try:
        if is_stream:
            # Simulate streaming by chunking the draft_reply
            from guardrail import ModerationSession
            session = ModerationSession(user_state=user_state, rules=rules)
            
            print("--- Streaming Start ---")
            # Simulate chunks of 5 characters
            chunk_size = 5
            for i in range(0, len(draft_reply), chunk_size):
                chunk = draft_reply[i:i+chunk_size]
                result = session.on_chunk(chunk)
                
                # Only print interesting events to avoid noise
                if result["status"] == "BLOCK":
                    print(f"Chunk '{chunk}': BLOCKED ({result['reason']})")
                    break
                else:
                    print(f"Chunk '{chunk}': ALLOW")
            
            if not session.blocked:
                final_result = session.finalize()
                print("--- Finalize ---")
                print(json.dumps(final_result, indent=2))
        else:
            # Standard single-pass moderation
            result = moderate_reply(user_state, draft_reply, rules)
            print(json.dumps(result, indent=2))

    except ValidationError as e:
        print("Validation Error:", file=sys.stderr)
        print(e.json(indent=2), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
