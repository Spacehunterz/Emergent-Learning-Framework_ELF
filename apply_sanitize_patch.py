#!/usr/bin/env python3
"""Apply sanitize_input patch to record-failure.sh and record-heuristic.sh"""

import os

SANITIZE_FUNC = '''# Sanitize input: strip ANSI escapes, control chars, CRLF
sanitize_input() {
    local input="$1"
    # Remove ANSI escape sequences
    input=$(printf '%s' "$input" | sed 's/\\x1b\\[[0-9;]*[mGKHF]//g')
    # Remove control characters except newline/tab
    input=$(printf '%s' "$input" | tr -d '\\000-\\010\\013-\\037\\177')
    # Convert CRLF to space
    input=$(printf '%s' "$input" | tr '\\r\\n' '  ')
    printf '%s' "$input"
}

'''

def patch_failure_script(script_path):
    """Patch record-failure.sh"""
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'sanitize_input()' in content:
        print(f"{script_path}: Already patched")
        return False

    # Insert sanitize function before escape_sql
    marker = '# Escape single quotes for SQL injection protection'
    if marker not in content:
        print(f"{script_path}: escape_sql marker not found")
        return False

    content = content.replace(marker, SANITIZE_FUNC + marker)

    # Insert sanitize calls before title_escaped
    sanitize_calls = '''
# SECURITY: Sanitize ALL user inputs before processing
title=$(sanitize_input "$title")
domain=$(sanitize_input "$domain")
summary=$(sanitize_input "$summary")
tags=$(sanitize_input "$tags")

'''
    call_marker = 'title_escaped=$(escape_sql'
    if call_marker not in content:
        print(f"{script_path}: escape_sql call marker not found")
        return False

    content = content.replace(call_marker, sanitize_calls + call_marker)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"{script_path}: Successfully patched!")
    return True

def patch_heuristic_script(script_path):
    """Patch record-heuristic.sh"""
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'sanitize_input()' in content:
        print(f"{script_path}: Already patched")
        return False

    # Insert sanitize function before escape_sql
    marker = '# Escape single quotes for SQL'
    if marker not in content:
        print(f"{script_path}: escape_sql marker not found")
        return False

    content = content.replace(marker, SANITIZE_FUNC + marker, 1)

    # Insert sanitize calls before domain_escaped
    sanitize_calls = '''
# SECURITY: Sanitize ALL user inputs before processing
domain=$(sanitize_input "$domain")
rule=$(sanitize_input "$rule")
explanation=$(sanitize_input "$explanation")

'''
    call_marker = 'domain_escaped=$(escape_sql'
    if call_marker not in content:
        print(f"{script_path}: escape_sql call marker not found")
        return False

    content = content.replace(call_marker, sanitize_calls + call_marker)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"{script_path}: Successfully patched!")
    return True

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(base_dir, 'scripts')

    failure_script = os.path.join(scripts_dir, 'record-failure.sh')
    heuristic_script = os.path.join(scripts_dir, 'record-heuristic.sh')

    if os.path.exists(failure_script):
        patch_failure_script(failure_script)
    else:
        print(f"{failure_script}: File not found")

    if os.path.exists(heuristic_script):
        patch_heuristic_script(heuristic_script)
    else:
        print(f"{heuristic_script}: File not found")
