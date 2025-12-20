# Load Building Context

Query the Emergent Learning Framework for institutional knowledge and summarize recent sessions.

## Steps

1. Run the query system to load context:
   ```bash
   python ~/.claude/emergent-learning/query/query.py --context
   ```

2. **IMMEDIATELY spawn an async haiku agent to summarize the previous session:**

   First, find the previous session file (second most recent non-agent JSONL):
   ```bash
   ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | grep -v "agent-" | head -2 | tail -1
   ```

   Then spawn a background haiku Task agent with this prompt:
   ```
   Task tool parameters:
   - subagent_type: "general-purpose"
   - model: "haiku"
   - run_in_background: true
   - prompt: "Summarize the Claude Code session at [SESSION_FILE_PATH].

     Instructions:
     1. Read the JSONL file
     2. Extract user and assistant messages (skip sidechains)
     3. CRITICAL: Capture the LAST 3 user prompts and Claude responses verbatim
     4. Generate a 300-500 token summary with:
        - Title (what was this session about)
        - Topics covered
        - What Claude did (key actions)
        - Files modified
        - Key learnings
        - ## Last Exchange section with final 3 user/assistant exchanges
     5. Save to ~/.claude/emergent-learning/memory/sessions/YYYY-MM-DD-HH-MM-topic-slug.md

     This is critical for session continuity - the Last Exchange section helps the next Claude instance understand where work left off."
   ```

   **DO NOT WAIT for this agent to complete.** Continue with the checkin immediately.

3. Show the latest session summary from the database (if available):
   ```bash
   python -c "
import sqlite3
from pathlib import Path
db = Path.home() / '.claude/emergent-learning/memory/index.db'
conn = sqlite3.connect(str(db))
cur = conn.cursor()
cur.execute('SELECT session_id, project, conversation_summary, tool_summary, summarized_at FROM session_summaries ORDER BY summarized_at DESC LIMIT 1')
row = cur.fetchone()
if row:
    print(f'Last Session: {row[0][:8]}... ({row[1]})')
    print(f'Summary: {row[2]}')
    print(f'Tools: {row[3]}')
    print(f'Summarized: {row[4]}')
else:
    print('No session summaries found')
conn.close()
"
   ```

4. Display the ELF banner (first checkin only):
   ```
   ┌────────────────────────────────────┐
   │    Emergent Learning Framework     │
   ├────────────────────────────────────┤
   │                                    │
   │      █████▒  █▒     █████▒         │
   │      █▒      █▒     █▒             │
   │      ████▒   █▒     ████▒          │
   │      █▒      █▒     █▒             │
   │      █████▒  █████▒ █▒             │
   │                                    │
   └────────────────────────────────────┘
   ```

5. Summarize for the user:
   - Active golden rules count
   - Relevant heuristics for current work
   - Any pending CEO decisions
   - Active experiments
   - **Last session summary** (from step 3)

6. Ask: "Start ELF Dashboard? [Y/n]"
   - Only ask on FIRST checkin of conversation
   - If Yes: `bash ~/.claude/emergent-learning/dashboard-app/run-dashboard.sh`
   - If No: Skip

7. If there are pending CEO decisions, list them and ask if the user wants to address them.

8. If there are active experiments, briefly note their status.

## Domain-Specific Queries

If the user includes a domain (e.g., "/checkin architecture"), also run:
```bash
python ~/.claude/emergent-learning/query/query.py --domain [domain]
```

## Available Domains
- coordination
- architecture
- debugging
- communication
- other
