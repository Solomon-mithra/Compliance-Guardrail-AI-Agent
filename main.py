import json
import sys
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
    # Use loaded rules, ignore rules in input if any (or we could merge, but prompt implies external source is authority)


    # Run the function
    result = moderate_reply(user_state, draft_reply, rules)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
