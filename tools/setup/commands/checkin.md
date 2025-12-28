# Load Building Context

Query the Emergent Learning Framework for institutional knowledge and summarize recent sessions.

## Steps

1. Run the query system to load context:
   ```bash
   python ~/.claude/emergent-learning/src/query/query.py --context
   ```

2. **Summarize the previous session to database (background):**

   Use Python to find and summarize the previous session (avoids MSYS bash escaping issues):
   ```bash
   python -c "
from pathlib import Path
import subprocess
sessions = sorted(Path.home().glob('.claude/projects/*/*.jsonl'), key=lambda p: p.stat().st_mtime, reverse=True)
non_agent = [s for s in sessions if 'agent-' not in s.name]
if len(non_agent) >= 2:
    prev = non_agent[1].stem
    print(f'Summarizing previous session: {prev[:8]}...')
    subprocess.Popen(['python', str(Path.home() / '.claude/emergent-learning/scripts/summarize-session.py'), prev])
else:
    print('No previous session to summarize')
"
   ```

   This calls the proper summarize-session.py script which writes to the database.

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

9. **Database Health Check** (optional, on first checkin):

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
