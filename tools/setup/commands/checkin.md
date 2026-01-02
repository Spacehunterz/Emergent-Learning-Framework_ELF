# Load Building Context

Query the Emergent Learning Framework for institutional knowledge and summarize recent sessions.

## Steps

1. Run the query system to load context:
   ```bash
   python ~/.claude/emergent-learning/src/query/query.py --context
   ```

2. **Summarize the previous session using Task(model="haiku"):**

   First, extract session data:
   ```bash
   python -c "
from pathlib import Path
import json
import sqlite3

sessions = sorted(Path.home().glob('.claude/projects/*/*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
non_agent = [s for s in sessions if 'agent-' not in s.name]

if len(non_agent) >= 2:
    prev = non_agent[1]
    session_id = prev.stem
    project = prev.parent.name

    # Check if already summarized with haiku
    db = Path.home() / '.claude/emergent-learning/memory/index.db'
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute('SELECT summarizer_model FROM session_summaries WHERE session_id = ?', (session_id,))
    row = cur.fetchone()
    conn.close()

    if row and row[0] == 'haiku':
        print(f'ALREADY_SUMMARIZED:{session_id[:8]}')
    else:
        # Extract data for haiku
        tool_counts = {}
        msg_count = 0
        with open(prev, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    if data.get('isSidechain'):
                        continue
                    if data.get('type') == 'user':
                        msg_count += 1
                    elif data.get('type') == 'assistant':
                        for item in data.get('message', {}).get('content', []):
                            if isinstance(item, dict) and item.get('type') == 'tool_use':
                                name = item.get('name', 'unknown')
                                tool_counts[name] = tool_counts.get(name, 0) + 1
                except:
                    pass
        tools_str = ', '.join(f'{v}x {k}' for k, v in sorted(tool_counts.items(), key=lambda x: -x[1])[:5])
        print(f'NEEDS_SUMMARY:{session_id}|{project}|{msg_count}|{tools_str}')
else:
    print('NO_PREVIOUS_SESSION')
"
   ```

   If output shows `NEEDS_SUMMARY:session_id|project|msg_count|tools`:
   - Use `Task(model="haiku", subagent_type="general-purpose")` to summarize
   - Prompt: "Summarize this session. Return JSON only: {tool_summary, content_summary, conversation_summary}"
   - Save result to database with `summarizer_model = 'haiku'`

   **IMPORTANT:** Per Golden Rule #11, use Task tool (Max subscription) NOT subprocess API calls.

3. Show the latest session summary from database:
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

5. Get ELF stats (IMPORTANT: golden rules are stored in heuristics table with is_golden=1, NOT a separate golden_rules table):
   ```bash
   python -c "
import sqlite3
from pathlib import Path
db = Path.home() / '.claude/emergent-learning/memory/index.db'
conn = sqlite3.connect(str(db))
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM heuristics WHERE status=\"active\"')
heuristics = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM heuristics WHERE is_golden=1 AND status=\"active\"')
golden = cur.fetchone()[0]
cur.execute('SELECT COUNT(*) FROM experiments WHERE status=\"active\"')
experiments = cur.fetchone()[0]
print(f'Active heuristics: {heuristics}')
print(f'Golden rules: {golden}')
print(f'Active experiments: {experiments}')
conn.close()
"
   ```

6. Summarize for the user:
   - Stats from step 5 (heuristics, golden rules, experiments)
   - Relevant heuristics for current work (from step 1 context)
   - Any pending CEO decisions (from step 10 health check)
   - **Last session summary** (from step 3)

7. Ask: "Start ELF Dashboard? [Y/n]"
   - Only ask on FIRST checkin of conversation
   - If Yes (run both in background):
     - Dashboard: `cd ~/.claude/emergent-learning/apps/dashboard && bash run-dashboard.sh`
     - TalkinHead: `cd ~/.claude/emergent-learning/apps/dashboard/TalkinHead && python main.py`
   - If No: Skip

8. If there are pending CEO decisions, list them and ask if the user wants to address them.

9. If there are active experiments, briefly note their status.

10. **Database Health Check** (optional, on first checkin):

   Run quick health check:
   ```bash
   python -c "
import sqlite3
from pathlib import Path
db = Path.home() / '.claude/emergent-learning/memory/index.db'
conn = sqlite3.connect(str(db))
cur = conn.cursor()

# Check key tables
issues = []
cur.execute('SELECT COUNT(*) FROM heuristics WHERE status=\"active\" AND last_fraud_check IS NULL AND (times_validated + times_violated) >= 10')
unchecked = cur.fetchone()[0]
if unchecked > 10:
    issues.append(f'{unchecked} heuristics need fraud check')

cur.execute('SELECT COUNT(*) FROM fraud_reports WHERE review_outcome IS NULL AND classification IN (\"fraud_likely\", \"fraud_confirmed\")')
pending_fraud = cur.fetchone()[0]
if pending_fraud > 0:
    issues.append(f'{pending_fraud} fraud reports pending review')

cur.execute('SELECT COUNT(*) FROM ceo_reviews WHERE status=\"pending\"')
pending_ceo = cur.fetchone()[0]
if pending_ceo > 0:
    issues.append(f'{pending_ceo} CEO reviews pending')

cur.execute('SELECT COUNT(*) FROM invariants WHERE violation_count > 0 AND status=\"active\"')
violations = cur.fetchone()[0]
if violations > 0:
    issues.append(f'{violations} invariant violations')

if issues:
    print('Database Issues:')
    for i in issues:
        print(f'  - {i}')
    print('Run /maintenance to address these.')
else:
    print('Database health: OK')
conn.close()
"
   ```

   If issues found, suggest: "Run `/maintenance` to fix database issues?"

## Domain-Specific Queries

If the user includes a domain (e.g., "/checkin architecture"), also run:
```bash
python ~/.claude/emergent-learning/src/query/query.py --domain [domain]
```

## Available Domains
- coordination
- architecture
- debugging
- communication
- other
