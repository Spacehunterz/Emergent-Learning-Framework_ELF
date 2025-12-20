---
description: Trigger a check-in to summarize the most recent session
---

1. [TURBO] Find the most recent session file (excluding the current one if possible, or just the latest .jsonl).
   ```bash
   # Find the latest JSONL file in projects
   # (This is a simplified logic, ideally we use the python script to find it)
   python scripts/summarize-session.py --limit 1 --older-than 0m --batch
   ```

2. Run the summarizer on it.
   ```bash
    python scripts/summarize-session.py --limit 1 --older-than 0m --batch
   ```

3. Report the result to the user.
