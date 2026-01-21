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
    
    # Run the function
    try:
        result = moderate_reply(user_state, draft_reply, rules)
        print(json.dumps(result, indent=2))
    except ValidationError as e:
        print("Validation Error:", file=sys.stderr)
        print(e.json(indent=2), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
