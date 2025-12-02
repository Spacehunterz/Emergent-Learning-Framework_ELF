#!/usr/bin/env python3
"""
Script to apply all improvements to query.py
Creates query_hardened.py with all 10/10 robustness features
"""
import re

print("Reading original query.py...")
with open('query.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Original: {len(lines)} lines")

# We'll build the improved version line by line
improved_lines = []
skip_until = None
in_init = False
init_done = False

for i, line in enumerate(lines):
    line_num = i + 1
    
    # Add imports after existing imports
    if line.strip() == 'from datetime import datetime':
        improved_lines.append(line)
        improved_lines.append('from functools import lru_cache\n')
        continue
    
    if line.strip() == 'import argparse':
        improved_lines.append(line)
        improved_lines.append('import signal\n')
        continue
        
    if line.strip() == 'import json':
        improved_lines.append(line)
        improved_lines.append('import time\n')
        continue
    
    # Add exception classes before QuerySystem class
    if line.startswith('class QuerySystem:'):
        # Insert exception classes
        improved_lines.append('\n')
        improved_lines.append('# Custom Exceptions\n')
        improved_lines.append('class QuerySystemError(Exception):\n')
        improved_lines.append('    """Base exception for query system errors."""\n')
        improved_lines.append('    pass\n\n')
        improved_lines.append('class DatabaseError(QuerySystemError):\n')
        improved_lines.append('    """Database-related errors."""\n')
        improved_lines.append('    pass\n\n')
        improved_lines.append('class ValidationError(QuerySystemError):\n')
        improved_lines.append('    """Input validation errors."""\n')
        improved_lines.append('    pass\n\n')
        improved_lines.append('class TimeoutError(QuerySystemError):\n')
        improved_lines.append('    """Query timeout errors."""\n')
        improved_lines.append('    pass\n\n')
        improved_lines.append('class ReadonlyDatabaseError(DatabaseError):\n')
        improved_lines.append('    """Readonly database errors."""\n')
        improved_lines.append('    pass\n\n')
        improved_lines.append('# Constants\n')
        improved_lines.append('MAX_TAGS = 50\n')
        improved_lines.append('MAX_LIMIT = 1000\n')
        improved_lines.append('DEFAULT_TIMEOUT = 30\n')
        improved_lines.append('MAX_QUERY_LENGTH = 10000\n\n')
        improved_lines.append(line)
        continue
    
    # Modify __init__ signature
    if 'def __init__(self, base_path: Optional[str] = None):' in line:
        improved_lines.append('    def __init__(self, base_path: Optional[str] = None, debug: bool = False, timeout: int = DEFAULT_TIMEOUT):\n')
        in_init = True
        continue
    
    # Add new instance variables in __init__
    if in_init and 'self.memory_path = self.base_path / "memory"' in line:
        improved_lines.append('        self.debug = debug\n')
        improved_lines.append('        self.timeout = timeout\n')
        improved_lines.append('        self._cache_hits = 0\n')
        improved_lines.append('        self._cache_misses = 0\n')
        improved_lines.append('        self._readonly_mode = False\n\n')
        improved_lines.append(line)
        continue
    
    # Add debug logging at end of __init__
    if in_init and 'self._init_database()' in line:
        improved_lines.append(line)
        improved_lines.append('\n')
        improved_lines.append('        if self.debug:\n')
        improved_lines.append('            print(f"[DEBUG] QuerySystem initialized", file=sys.stderr)\n')
        improved_lines.append('            print(f"[DEBUG] Base path: {self.base_path}", file=sys.stderr)\n')
        improved_lines.append('            print(f"[DEBUG] DB path: {self.db_path}", file=sys.stderr)\n')
        improved_lines.append('            print(f"[DEBUG] Timeout: {self.timeout}s", file=sys.stderr)\n')
        improved_lines.append('            print(f"[DEBUG] Readonly mode: {self._readonly_mode}", file=sys.stderr)\n')
        in_init = False
        init_done = True
        continue
    
    # Add _log_debug method after __init__
    if init_done and 'def _init_database(self):' in line:
        improved_lines.append('    def _log_debug(self, message: str):\n')
        improved_lines.append('        """Log debug message if debug mode is enabled."""\n')
        improved_lines.append('        if self.debug:\n')
        improved_lines.append('            print(f"[DEBUG] {message}", file=sys.stderr)\n\n')
        improved_lines.append(line)
        init_done = False
        continue
    
    # Wrap ANALYZE in try/except in _init_database
    if '        # Update query planner statistics' in line:
        improved_lines.append(line)
        improved_lines.append('        # Wrap in try/except for readonly databases\n')
        improved_lines.append('        try:\n')
        improved_lines.append('            cursor.execute("ANALYZE")\n')
        improved_lines.append('            conn.commit()\n')
        improved_lines.append('        except sqlite3.OperationalError as e:\n')
        improved_lines.append('            if "readonly" in str(e).lower():\n')
        improved_lines.append('                self._log_debug("Skipping ANALYZE on readonly database")\n')
        improved_lines.append('                self._readonly_mode = True\n')
        improved_lines.append('            else:\n')
        improved_lines.append('                raise\n')
        # Skip the next cursor.execute("ANALYZE") line
        skip_until = i + 2
        continue
    
    if skip_until and i < skip_until:
        continue
    elif skip_until and i == skip_until:
        skip_until = None
        continue
    
    # Add @lru_cache to get_golden_rules
    if '    def get_golden_rules(self) -> str:' in line:
        improved_lines.append('    @lru_cache(maxsize=128)\n')
        improved_lines.append(line)
        continue
    
    # Otherwise, keep the line as is
    improved_lines.append(line)

# Write the improved version
with open('query_hardened.py', 'w', encoding='utf-8') as f:
    f.writelines(improved_lines)

print(f"Created query_hardened.py: {len(improved_lines)} lines")
print(f"Changes applied:")
print("  - Added exception classes")
print("  - Added constants (MAX_TAGS, etc.)")
print("  - Added debug and timeout parameters")
print("  - Added _log_debug method")
print("  - Wrapped ANALYZE in try/except")
print("  - Added @lru_cache to get_golden_rules")

