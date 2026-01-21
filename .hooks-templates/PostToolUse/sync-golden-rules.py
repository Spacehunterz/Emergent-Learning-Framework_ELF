#!/usr/bin/env python3
"""
Post-tool hook: Auto-sync golden-rules.md to database

Runs after every tool use. If golden-rules.md was modified, syncs to database.
"""

import sqlite3
import re
from pathlib import Path
import hashlib
import json
from datetime import datetime

STATE_FILE = Path.home() / '.claude/hooks/investigation-state.json'
MARKDOWN_FILE = Path.home() / '.claude/emergent-learning/memory/golden-rules.md'
DB_FILE = Path.home() / '.claude/emergent-learning/memory/index.db'

def get_file_hash(filepath):
    """Get SHA256 hash of file."""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def load_state():
    """Load last known state."""
    try:
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
    except:
        pass
    return {}

def save_state(state):
    """Save current state."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except:
        pass

def sync_golden_rules():
    """Sync markdown to database."""
    try:
        # Read markdown
        with open(MARKDOWN_FILE) as f:
            content = f.read()
        
        golden_titles = re.findall(r'^## \d+\. (.+)$', content, re.MULTILINE)
        
        # Connect to database
        conn = sqlite3.connect(str(DB_FILE))
        cur = conn.cursor()
        
        # Get all heuristics (no status column exists)
        cur.execute('SELECT id, rule, is_golden FROM heuristics')
        all_heuristics = cur.fetchall()
        
        updates = 0
        for heuristic_id, rule_text, is_golden in all_heuristics:
            should_be_golden = any(
                title.lower() in rule_text.lower() 
                for title in golden_titles
            )
            
            if should_be_golden != bool(is_golden):
                cur.execute('UPDATE heuristics SET is_golden=? WHERE id=?', 
                           (1 if should_be_golden else 0, heuristic_id))
                updates += 1
        
        conn.commit()
        conn.close()
        
        return updates > 0
    except Exception as e:
        print(f"[WARN] Golden rules sync failed: {e}")
        return False

def run():
    """Check if sync is needed and run it."""
    state = load_state()
    current_hash = get_file_hash(MARKDOWN_FILE)
    last_hash = state.get('golden_rules_hash')
    
    # If markdown changed, sync to database
    if current_hash and current_hash != last_hash:
        if sync_golden_rules():
            state['golden_rules_hash'] = current_hash
            state['golden_rules_last_sync'] = datetime.now().isoformat()
            save_state(state)
            return "Synced golden-rules.md to database"
    
    return None

if __name__ == '__main__':
    result = run()
    if result:
        print(f"[SYNC] {result}")
