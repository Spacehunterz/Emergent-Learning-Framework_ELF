#!/usr/bin/env python3
"""
Sync golden-rules.md with heuristics database.

Whenever the markdown file is updated, this script:
1. Extracts rule titles from golden-rules.md
2. Finds matching heuristics in the database
3. Updates is_golden flag to match markdown

Usage:
    python sync-golden-rules.py [--verbose]
"""

import sqlite3
import re
from pathlib import Path
import sys

def get_markdown_golden_rules():
    """Extract golden rule titles from markdown file."""
    markdown_file = Path.home() / '.claude/emergent-learning/memory/golden-rules.md'
    
    if not markdown_file.exists():
        raise FileNotFoundError(f"Golden rules file not found: {markdown_file}")
    
    with open(markdown_file) as f:
        content = f.read()
    
    titles = re.findall(r'^## \d+\. (.+)$', content, re.MULTILINE)
    return titles

def sync_database(verbose=False):
    """Sync database with markdown golden rules."""
    db = Path.home() / '.claude/emergent-learning/memory/index.db'
    
    # Get markdown rules
    golden_titles = get_markdown_golden_rules()
    if verbose:
        print(f"[SYNC] Found {len(golden_titles)} golden rules in markdown")
    
    # Connect to database
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    
    # Get all heuristics (no status column exists)
    cur.execute('SELECT id, rule, is_golden FROM heuristics')
    all_heuristics = cur.fetchall()
    
    updates = 0
    marked_golden = []
    unmarked = []
    
    for heuristic_id, rule_text, is_golden in all_heuristics:
        # Check if rule matches any golden rule title
        should_be_golden = any(
            title.lower() in rule_text.lower() 
            for title in golden_titles
        )
        
        # Update if mismatch
        if should_be_golden != bool(is_golden):
            cur.execute('UPDATE heuristics SET is_golden=? WHERE id=?', 
                       (1 if should_be_golden else 0, heuristic_id))
            updates += 1
            
            if should_be_golden:
                marked_golden.append(rule_text[:70])
            else:
                unmarked.append(rule_text[:70])
    
    conn.commit()
    
    # Verify result
    cur.execute('SELECT COUNT(*) FROM heuristics WHERE is_golden=1')
    final_golden_count = cur.fetchone()[0]
    
    conn.close()
    
    if verbose:
        print(f"[SYNC] Updates: {updates}")
        if marked_golden:
            print(f"[SYNC] Marked as golden: {len(marked_golden)}")
        if unmarked:
            print(f"[SYNC] Unmarked: {len(unmarked)}")
        print(f"[SYNC] Final count: {final_golden_count} golden rules")
    
    return {
        'updates': updates,
        'marked_golden': len(marked_golden),
        'unmarked': len(unmarked),
        'final_golden_count': final_golden_count
    }

if __name__ == '__main__':
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    try:
        result = sync_database(verbose=verbose)
        if not verbose:
            print(f"Synced: {result['updates']} updates, {result['final_golden_count']} golden rules total")
    except Exception as e:
        print(f"Error syncing golden rules: {e}", file=sys.stderr)
        sys.exit(1)
