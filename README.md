# Compliance Guardrail for AI Agents Replies

A deterministic, auditable compliance guardrail for Voice/LLM agents. This system moderates agent replies based on configurable rules (blocking phrases, required disclosures, PII redaction, and length limits) before they are sent to customers.

## Features
- **Deterministic Rules**:
  - `BLOCK_PHRASE`: Immediately blocks risky content.
  - `REQUIRE_PHRASE`: Ensures mandatory disclosures are present.
  - `REWRITE_REGEX`: Sanitizes sensitve data (PII).
  - `MAX_LENGTH`: Truncates long responses intelligently.
- **Audit Logging**: Returns a full trace of applied rules and modifications.
- **Configurable**: Rules are defined in `rules.json`.
- **Easy CLI**: Run via `python3 main.py`.

## Usage

### 1. Configuration
Define your rules in `rules.json`:
```json
[
  {
    "id": "block_guarantee",
    "type": "BLOCK_PHRASE",
    "params": { "phrases": ["guarantee", "100% approved"] }
  }
]
```

### 2. Run from CLI
Pass a JSON file containing the user state and draft reply:

```bash
python3 main.py input.json
```

Or pipe input:
```bash
echo '{...}' | python3 main.py
```

### 3. Output
```json
{
  "status": "REWRITE",
  "final_reply": "This call may be recorded...",
  "applied_rules": ["rule_req", "rule_rewrite"],
  "reason": null
}
```

## Testing
Run the unit test suite:
```bash
python3 -m unittest test_guardrail.py
```
