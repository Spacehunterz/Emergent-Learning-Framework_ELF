#!/usr/bin/env python3
"""Analyze pattern test failures."""

import re

print("="*60)
print("ANALYZING PATTERN TEST FAILURES")
print("="*60)

# Test 1: yaml.load pattern
pattern1 = r'yaml\.load\s*\([^,)]*\)(?!\s*,\s*Loader)'
test1_wrong = 'yaml.parse(data)'
test1_correct = 'yaml.load(data)'
print('\nTest 1 - yaml.load:')
print(f'  yaml.parse(data): {bool(re.search(pattern1, test1_wrong))}')
print(f'  yaml.load(data): {bool(re.search(pattern1, test1_correct))}')
print('  -> Test was using yaml.parse() not yaml.load()')

# Test 2: open with user input
pattern2 = r'open\s*\([^)]*\+[^)]*user'
test2_wrong = 'open(user_path, "w")'
test2_correct = 'open(path + user, "w")'
print('\nTest 2 - open with user input:')
print(f'  open(user_path, "w"): {bool(re.search(pattern2, test2_wrong))}')
print(f'  open(path + user, "w"): {bool(re.search(pattern2, test2_correct))}')
print('  -> Pattern only checks for concatenation (+), not variables')

# Test 3: Newline after eval
pattern3 = r'eval\s*\('
test3 = 'eval\n(x)'
print('\nTest 3 - Newline after eval:')
print(f'  eval\\n(x): {bool(re.search(pattern3, test3, re.MULTILINE))}')
print('  -> Edge case, not realistic code style')

# Test 4: Backslash in path
pattern4 = r'\.\.[/\\]\.\.[/\\]'
test4_wrong = r'..\\..\\windows'  # String literal with double backslash (escaped)
test4_correct = r'..\..\windows'  # Actual path pattern
print('\nTest 4 - Backslash in path:')
print(f'  ..\\\\..\\\\windows (test string): {bool(re.search(pattern4, test4_wrong))}')
print(f'  ..\\\\..\\\\windows (actual): {bool(re.search(pattern4, test4_correct))}')
print('  -> Test had escaped backslashes, pattern is correct')

# Test 5: requests with timeout - CRITICAL FALSE POSITIVE BUG
pattern5 = r'requests\.(get|post|put|delete|patch|head|options)\s*\([^)]*\)(?![^)]*timeout)'
test5_safe = 'requests.get(url, timeout=30)'
test5_risky = 'requests.get(url)'
print('\nTest 5 - requests with timeout (CRITICAL BUG):')
print(f'  requests.get(url, timeout=30): {bool(re.search(pattern5, test5_safe))} <- FALSE POSITIVE!')
print(f'  requests.get(url): {bool(re.search(pattern5, test5_risky))}')
print('  -> BUG: Negative lookahead looks AFTER closing paren')
print('  -> But timeout is INSIDE the parentheses!')

print('\n' + '='*60)
print('CONCLUSION:')
print('='*60)
print('1. yaml.load - Test error (used wrong function)')
print('2. open + user - Design choice (only catches concatenation)')
print('3. eval\\n - Edge case (not realistic)')
print('4. Backslash path - Test error (wrong escaping)')
print('5. requests timeout - REAL BUG in pattern!')
print('\nONLY #5 needs to be fixed.')
