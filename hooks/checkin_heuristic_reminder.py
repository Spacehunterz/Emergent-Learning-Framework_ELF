#!/usr/bin/env python3
"""
UserPromptSubmit hook: Detect "check in" command and inject heuristic reminder.
Addresses issue #40 - ensures Claude proactively suggests heuristic recording.
"""

import sys
import json

CHECKIN_TRIGGERS = ["check in", "checkin", "/checkin"]

REMINDER = """<checkin-reminder>
MANDATORY POST-SESSION PROTOCOL ACTIVATED

Before providing your checkin summary, you MUST:

1. ANALYZE this session for learnings:
   - Patterns discovered -> potential heuristics
   - Failures encountered -> record candidates
   - Debugging insights -> domain knowledge

2. LIST potential heuristics in this format:
   ## Session Learnings

   I identified N potential heuristic(s) from this session:

   1. "Rule statement here"
      - Domain: [domain]
      - Why: [explanation]
      - Source: failure|success|observation

   Should I record these to the building?

3. ONLY THEN provide the status summary.

Do NOT skip heuristic analysis. This is enforced by hook.
</checkin-reminder>"""

def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            print(json.dumps({"result": "continue"}))
            return 0

        data = json.loads(input_data)
        prompt = data.get("prompt", "").lower().strip()

        is_checkin = any(trigger in prompt for trigger in CHECKIN_TRIGGERS)

        if is_checkin:
            print(json.dumps({
                "result": "continue",
                "message": REMINDER
            }))
        else:
            print(json.dumps({"result": "continue"}))

    except Exception as e:
        print(json.dumps({"result": "continue"}), file=sys.stdout)

    return 0

if __name__ == "__main__":
    sys.exit(main())
