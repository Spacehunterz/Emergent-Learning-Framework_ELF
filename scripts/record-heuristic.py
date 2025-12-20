#!/usr/bin/env python3
"""
Record a heuristic in the Emergent Learning Framework.

This is the cross-platform Python version that works on Windows, macOS, and Linux
without requiring the sqlite3 CLI tool.

Usage (interactive): python record-heuristic.py
Usage (non-interactive):
    python record-heuristic.py --domain "domain" --rule "rule" --explanation "why"
    Optional: --source failure|success|observation --confidence 0.8

Environment variables also supported:
    HEURISTIC_DOMAIN, HEURISTIC_RULE, HEURISTIC_EXPLANATION, HEURISTIC_SOURCE, HEURISTIC_CONFIDENCE
"""

import argparse
import os
import re
import sqlite3
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

# Project context detection
PROJECT_CONTEXT_AVAILABLE = False
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "query"))
    from project import detect_project_context
    PROJECT_CONTEXT_AVAILABLE = True
except ImportError:
    pass

# Constants
MAX_RULE_LENGTH = 500
MAX_DOMAIN_LENGTH = 100
MAX_EXPLANATION_LENGTH = 5000
MAX_RETRY_ATTEMPTS = 5

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent
MEMORY_DIR = BASE_DIR / "memory"
DB_PATH = MEMORY_DIR / "index.db"
HEURISTICS_DIR = MEMORY_DIR / "heuristics"
LOGS_DIR = BASE_DIR / "logs"


def setup_logging() -> Path:
    """Setup logging directory and return log file path."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"{datetime.now().strftime('%Y%m%d')}.log"


LOG_FILE = setup_logging()


def log(level: str, message: str) -> None:
    """Log a message to file and optionally stderr."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] [{level}] [record-heuristic] {message}\n"

    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception:
        pass  # Don't fail on logging errors

    if level == "ERROR":
        print(f"ERROR: {message}", file=sys.stderr)


def sanitize_input(text: str) -> str:
    """Sanitize input: strip control chars, normalize whitespace."""
    if not text:
        return ""
    # Remove control characters (keep printable + space/tab/newline)
    text = ''.join(c for c in text if c.isprintable() or c in ' \t\n')
    # Normalize multiple spaces to single
    text = re.sub(r' +', ' ', text)
    # Trim leading/trailing whitespace
    return text.strip()


def sanitize_domain(domain: str) -> str:
    """Sanitize domain for use as filename and DB value."""
    # Lowercase, replace spaces with hyphens, keep only alphanumeric and hyphens
    domain = domain.lower()
    domain = domain.replace(' ', '-')
    domain = re.sub(r'[^a-z0-9-]', '', domain)
    # Remove leading/trailing hyphens
    domain = domain.strip('-')
    # Truncate to max length
    domain = domain[:MAX_DOMAIN_LENGTH]
    return domain


def check_symlink_safe(filepath: Path) -> bool:
    """Check for symlink attacks (TOCTOU protection)."""
    if filepath.is_symlink():
        log("ERROR", f"SECURITY: Target is a symlink: {filepath}")
        return False
    if filepath.parent.is_symlink():
        log("ERROR", f"SECURITY: Parent directory is a symlink: {filepath.parent}")
        return False
    return True


def check_hardlink_safe(filepath: Path) -> bool:
    """Check for hardlink attacks."""
    if not filepath.exists():
        return True

    try:
        stat_info = filepath.stat()
        if stat_info.st_nlink > 1:
            log("ERROR", f"SECURITY: File has {stat_info.st_nlink} hardlinks: {filepath}")
            return False
    except Exception:
        pass  # If we can't check, assume safe

    return True


def sqlite_with_retry(db_path: Path, query: str, params: tuple = ()) -> Tuple[bool, any]:
    """
    Execute SQLite query with retry logic for concurrent access.

    Returns: (success, result)
    """
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            conn = sqlite3.connect(str(db_path), timeout=10)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)

            # Get result before commit
            if query.strip().upper().startswith('INSERT'):
                result = cursor.lastrowid
            else:
                result = cursor.fetchall()

            conn.commit()
            conn.close()
            return True, result

        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() or "busy" in str(e).lower():
                log("WARN", f"SQLite busy, retry {attempt}/{MAX_RETRY_ATTEMPTS}...")
                print(f"SQLite busy, retry {attempt}/{MAX_RETRY_ATTEMPTS}...", file=sys.stderr)
                time.sleep(random.uniform(0.1, 0.5))
            else:
                log("ERROR", f"SQLite error: {e}")
                return False, None
        except Exception as e:
            log("ERROR", f"Database error: {e}")
            return False, None

    log("ERROR", f"SQLite failed after {MAX_RETRY_ATTEMPTS} attempts")
    return False, None


def parse_confidence(value: Optional[str]) -> float:
    """Parse confidence value, converting words to numbers."""
    if not value:
        return 0.7

    # Try parsing as float
    try:
        conf = float(value)
        if 0.0 <= conf <= 1.0:
            return conf
    except ValueError:
        pass

    # Convert word to number
    word_map = {
        'low': 0.3,
        'medium': 0.6,
        'high': 0.85,
    }
    return word_map.get(value.lower(), 0.7)


def preflight_check() -> bool:
    """Run pre-flight validation checks."""
    log("INFO", "Starting pre-flight checks")

    if not DB_PATH.exists():
        log("ERROR", f"Database not found: {DB_PATH}")
        return False

    # Check git repo (non-fatal warning)
    if not (BASE_DIR / ".git").exists():
        log("WARN", f"Not a git repository: {BASE_DIR}")

    log("INFO", "Pre-flight checks passed")
    return True


def check_similar_heuristics(domain: str, rule: str) -> list:
    """
    Check for existing similar heuristics in the same domain.

    Returns list of similar heuristics (id, rule, confidence).
    """
    query = """
        SELECT id, rule, confidence
        FROM heuristics
        WHERE domain = ?
        ORDER BY confidence DESC
    """
    success, results = sqlite_with_retry(DB_PATH, query, (domain,))

    if not success or not results:
        return []

    # Simple word overlap check for similarity
    rule_words = set(rule.lower().split())
    similar = []

    for row in results:
        existing_words = set(row['rule'].lower().split())
        overlap = len(rule_words & existing_words)
        total = len(rule_words | existing_words)

        if total > 0 and (overlap / total) > 0.5:  # >50% word overlap
            similar.append({
                'id': row['id'],
                'rule': row['rule'],
                'confidence': row['confidence'],
                'similarity': overlap / total
            })

    return sorted(similar, key=lambda x: x['similarity'], reverse=True)[:3]


def validate_heuristic_quality(rule: str, explanation: str) -> dict:
    """
    Validate heuristic quality against checklist criteria.

    Returns dict with 'passed', 'warnings', and 'suggestions'.
    """
    warnings = []
    suggestions = []

    # Check 1: Is it actionable? (Should contain action verbs)
    action_verbs = ['always', 'never', 'use', 'avoid', 'check', 'ensure',
                    'prefer', 'validate', 'test', 'verify', 'before', 'after',
                    'when', 'if', 'do', 'dont', "don't", 'should', 'must']
    rule_lower = rule.lower()
    has_action = any(verb in rule_lower for verb in action_verbs)

    if not has_action:
        warnings.append("Rule may not be actionable (no action verbs found)")
        suggestions.append("Consider rephrasing as 'Always X', 'Never Y', or 'When Z, do W'")

    # Check 2: Is it specific enough? (Not too short)
    if len(rule.split()) < 4:
        warnings.append("Rule is very short - may be too vague")
        suggestions.append("Add context: when does this apply? what's the scope?")

    # Check 3: Is it too long? (Should be memorable)
    if len(rule.split()) > 20:
        warnings.append("Rule is long - may be hard to remember")
        suggestions.append("Consider splitting into multiple rules or shortening")

    # Check 4: Does it have an explanation?
    if not explanation or len(explanation.strip()) < 10:
        warnings.append("No explanation provided")
        suggestions.append("Add WHY this heuristic works - future agents need context")

    # Check 5: Is it testable? (Contains conditions or measurable outcomes)
    testable_indicators = ['if', 'when', 'before', 'after', 'until', 'unless',
                          'error', 'fail', 'success', 'works', 'breaks']
    has_testable = any(ind in rule_lower for ind in testable_indicators)

    if not has_testable:
        warnings.append("May be hard to validate (no clear conditions)")
        suggestions.append("Consider adding: 'When X happens...' or 'To prevent Y...'")

    return {
        'passed': len(warnings) == 0,
        'warnings': warnings,
        'suggestions': suggestions,
        'score': max(0, 5 - len(warnings))  # Quality score out of 5
    }



def record_heuristic_with_location(
    domain: str,
    rule: str,
    explanation: str = '',
    source_type: str = 'observation',
    confidence: float = 0.7,
    project_path: Optional[str] = None,
    skip_validation: bool = False
) -> Optional[int]:
    """
    Record a heuristic to the global database with optional location tagging.

    Args:
        domain: Domain for the heuristic
        rule: The heuristic rule/statement
        explanation: Why this heuristic works
        source_type: failure|success|observation
        confidence: 0.0-1.0 confidence level
        project_path: Optional project path for location-specific heuristics.
                     NULL = global (available everywhere)
                     path = location-specific (only in that directory)
        skip_validation: Skip quality checks

    Returns: heuristic ID if successful, None otherwise
    """
    # Sanitize inputs
    domain = sanitize_domain(domain)
    if not domain:
        log("ERROR", "Domain resulted in empty string after sanitization")
        return None

    rule = sanitize_input(rule)
    explanation = sanitize_input(explanation)

    # Validate lengths
    if len(rule) > MAX_RULE_LENGTH:
        log("ERROR", f"Rule exceeds maximum length ({MAX_RULE_LENGTH} chars)")
        print(f"ERROR: Rule too long (max {MAX_RULE_LENGTH} characters)", file=sys.stderr)
        return None

    if len(explanation) > MAX_EXPLANATION_LENGTH:
        log("ERROR", "Explanation exceeds maximum length")
        print(f"ERROR: Explanation too long (max {MAX_EXPLANATION_LENGTH} characters)", file=sys.stderr)
        return None

    # Validate source_type
    valid_sources = {'failure', 'success', 'observation'}
    if source_type not in valid_sources:
        source_type = 'observation'

    # Validate confidence
    if not (0.0 <= confidence <= 1.0):
        confidence = 0.7

    # === QUALITY VALIDATION CHECKLIST ===
    if not skip_validation:
        print("\n--- Quality Validation ---")

        # Check for similar existing heuristics
        similar = check_similar_heuristics(domain, rule)
        if similar:
            print(f"\nSimilar heuristics found in '{domain}':")
            for s in similar:
                print(f"  [{s['id']}] {s['rule'][:60]}... ({s['similarity']*100:.0f}% similar)")
            print("  Consider updating existing heuristic instead of adding duplicate.")
            log("WARN", f"Similar heuristics found: {[s['id'] for s in similar]}")

        # Run quality checks
        quality = validate_heuristic_quality(rule, explanation)
        print(f"\nQuality Score: {quality['score']}/5")

        if quality['warnings']:
            print("\nWarnings:")
            for w in quality['warnings']:
                print(f"  - {w}")

        if quality['suggestions']:
            print("\nSuggestions:")
            for s in quality['suggestions']:
                print(f"  - {s}")

        if not quality['passed']:
            log("WARN", f"Quality validation warnings: {quality['warnings']}")

        print("--- End Validation ---\n")

    log("INFO", f"Recording heuristic: {rule} (domain: {domain}, confidence: {confidence}, project_path: {project_path})")

    # Insert into database with project_path for location awareness
    query = """
        INSERT INTO heuristics (domain, rule, explanation, source_type, confidence, project_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    success, heuristic_id = sqlite_with_retry(
        DB_PATH,
        query,
        (domain, rule, explanation, source_type, confidence, project_path)
    )

    if not success or not heuristic_id:
        log("ERROR", "Failed to insert into database")
        return None

    location_str = f" (location: {project_path})" if project_path else " (global)"
    print(f"Database record created (ID: {heuristic_id}){location_str}")
    log("INFO", f"Database record created (ID: {heuristic_id}){location_str}")

    # Ensure heuristics directory exists
    HEURISTICS_DIR.mkdir(parents=True, exist_ok=True)

    # Append to domain markdown file
    domain_file = HEURISTICS_DIR / f"{domain}.md"

    # Security checks before file write
    if not check_symlink_safe(domain_file):
        return None
    if not check_hardlink_safe(domain_file):
        return None

    # Create file header if new
    if not domain_file.exists():
        header = f"""# Heuristics: {domain}

Generated from failures, successes, and observations in the **{domain}** domain.

---

"""
        with open(domain_file, 'w', encoding='utf-8') as f:
            f.write(header)
        log("INFO", f"Created new domain file: {domain_file}")

    # Append heuristic entry
    location_tag = f"\n**Location**: {project_path}" if project_path else "\n**Location**: global"
    entry = f"""## H-{heuristic_id}: {rule}

**Confidence**: {confidence}
**Source**: {source_type}{location_tag}
**Created**: {datetime.now().strftime('%Y-%m-%d')}

{explanation}

---

"""
    with open(domain_file, 'a', encoding='utf-8') as f:
        f.write(entry)

    print(f"Appended to: {domain_file}")
    log("INFO", f"Appended heuristic to: {domain_file}")

    log("INFO", f"Heuristic recorded successfully: {rule}")
    print()
    print("Heuristic recorded successfully!")

    return heuristic_id


# Legacy function for backwards compatibility
def record_heuristic_to_project(
    project_db_path: Path,
    domain: str,
    rule: str,
    explanation: str = '',
    source_type: str = 'observation',
    confidence: float = 0.7,
) -> Optional[int]:
    """
    DEPRECATED: Record a heuristic to the project-specific database.

    This function is deprecated. Use record_heuristic_with_location() instead
    with project_path parameter to store location-specific heuristics in the
    global database.
    """
    log("WARN", "record_heuristic_to_project is deprecated - use single DB with project_path")
    # Convert to new approach: store in global DB with project_path
    project_path = str(project_db_path.parent.parent) if project_db_path else None
    return record_heuristic_with_location(
        domain=domain,
        rule=rule,
        explanation=explanation,
        source_type=source_type,
        confidence=confidence,
        project_path=project_path,
        skip_validation=True
    )


def record_heuristic(
    domain: str,
    rule: str,
    explanation: str = "",
    source_type: str = "observation",
    confidence: float = 0.7,
    skip_validation: bool = False
) -> Optional[int]:
    """
    Record a heuristic to the database and markdown file.

    Args:
        domain: Domain for the heuristic
        rule: The heuristic rule/statement
        explanation: Why this heuristic works
        source_type: failure|success|observation
        confidence: 0.0-1.0 confidence level
        skip_validation: Skip quality checks (use with caution)

    Returns: heuristic ID if successful, None otherwise
    """
    # Sanitize inputs
    domain = sanitize_domain(domain)
    if not domain:
        log("ERROR", "Domain resulted in empty string after sanitization")
        return None

    rule = sanitize_input(rule)
    explanation = sanitize_input(explanation)

    # Validate lengths
    if len(rule) > MAX_RULE_LENGTH:
        log("ERROR", f"Rule exceeds maximum length ({MAX_RULE_LENGTH} chars)")
        print(f"ERROR: Rule too long (max {MAX_RULE_LENGTH} characters)", file=sys.stderr)
        return None

    if len(explanation) > MAX_EXPLANATION_LENGTH:
        log("ERROR", "Explanation exceeds maximum length")
        print(f"ERROR: Explanation too long (max {MAX_EXPLANATION_LENGTH} characters)", file=sys.stderr)
        return None

    # Validate source_type
    valid_sources = {'failure', 'success', 'observation'}
    if source_type not in valid_sources:
        source_type = 'observation'

    # Validate confidence
    if not (0.0 <= confidence <= 1.0):
        confidence = 0.7

    # === QUALITY VALIDATION CHECKLIST ===
    if not skip_validation:
        print("\n--- Quality Validation ---")

        # Check for similar existing heuristics
        similar = check_similar_heuristics(domain, rule)
        if similar:
            print(f"\nSimilar heuristics found in '{domain}':")
            for s in similar:
                print(f"  [{s['id']}] {s['rule'][:60]}... ({s['similarity']*100:.0f}% similar)")
            print("  Consider updating existing heuristic instead of adding duplicate.")
            log("WARN", f"Similar heuristics found: {[s['id'] for s in similar]}")

        # Run quality checks
        quality = validate_heuristic_quality(rule, explanation)
        print(f"\nQuality Score: {quality['score']}/5")

        if quality['warnings']:
            print("\nWarnings:")
            for w in quality['warnings']:
                print(f"  - {w}")

        if quality['suggestions']:
            print("\nSuggestions:")
            for s in quality['suggestions']:
                print(f"  - {s}")

        if not quality['passed']:
            log("WARN", f"Quality validation warnings: {quality['warnings']}")

        print("--- End Validation ---\n")

    log("INFO", f"Recording heuristic: {rule} (domain: {domain}, confidence: {confidence})")

    # Insert into database
    query = """
        INSERT INTO heuristics (domain, rule, explanation, source_type, confidence)
        VALUES (?, ?, ?, ?, ?)
    """
    success, heuristic_id = sqlite_with_retry(
        DB_PATH,
        query,
        (domain, rule, explanation, source_type, confidence)
    )

    if not success or not heuristic_id:
        log("ERROR", "Failed to insert into database")
        return None

    print(f"Database record created (ID: {heuristic_id})")
    log("INFO", f"Database record created (ID: {heuristic_id})")

    # Ensure heuristics directory exists
    HEURISTICS_DIR.mkdir(parents=True, exist_ok=True)

    # Append to domain markdown file
    domain_file = HEURISTICS_DIR / f"{domain}.md"

    # Security checks before file write
    if not check_symlink_safe(domain_file):
        return None
    if not check_hardlink_safe(domain_file):
        return None

    # Create file header if new
    if not domain_file.exists():
        header = f"""# Heuristics: {domain}

Generated from failures, successes, and observations in the **{domain}** domain.

---

"""
        with open(domain_file, 'w', encoding='utf-8') as f:
            f.write(header)
        log("INFO", f"Created new domain file: {domain_file}")

    # Append heuristic entry
    entry = f"""## H-{heuristic_id}: {rule}

**Confidence**: {confidence}
**Source**: {source_type}
**Created**: {datetime.now().strftime('%Y-%m-%d')}

{explanation}

---

"""
    with open(domain_file, 'a', encoding='utf-8') as f:
        f.write(entry)

    print(f"Appended to: {domain_file}")
    log("INFO", f"Appended heuristic to: {domain_file}")

    log("INFO", f"Heuristic recorded successfully: {rule}")
    print()
    print("Heuristic recorded successfully!")

    return heuristic_id


def interactive_mode() -> dict:
    """Collect heuristic data interactively."""
    print("=== Record Heuristic ===")
    print()

    domain = input("Domain: ").strip()
    if not domain:
        log("ERROR", "Domain cannot be empty")
        print("ERROR: Domain cannot be empty", file=sys.stderr)
        sys.exit(1)

    rule = input("Rule (the heuristic): ").strip()
    if not rule:
        log("ERROR", "Rule cannot be empty")
        print("ERROR: Rule cannot be empty", file=sys.stderr)
        sys.exit(1)

    explanation = input("Explanation: ").strip()

    source_type = input("Source type (failure/success/observation): ").strip()
    if not source_type:
        source_type = "observation"

    confidence_str = input("Confidence (0.0-1.0): ").strip()
    confidence = parse_confidence(confidence_str) if confidence_str else 0.5

    return {
        'domain': domain,
        'rule': rule,
        'explanation': explanation,
        'source_type': source_type,
        'confidence': confidence,
    }


def main():
    parser = argparse.ArgumentParser(
        description='Record a heuristic in the Emergent Learning Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python record-heuristic.py

  # Non-interactive mode (global heuristic, available everywhere)
  python record-heuristic.py --domain "error-handling" --rule "Always log before raising"
  python record-heuristic.py --domain testing --rule "Mock at boundaries" --confidence 0.8

  # Location-specific heuristic (only shown when in current directory)
  python record-heuristic.py --project --domain "react" --rule "Use hooks for state"

  # Explicit location path
  python record-heuristic.py --location "/path/to/project" --domain "api" --rule "..."

  # Using environment variables
  HEURISTIC_DOMAIN="api" HEURISTIC_RULE="Validate inputs" python record-heuristic.py
"""
    )

    parser.add_argument('--domain', type=str, help='Domain for the heuristic')
    parser.add_argument('--rule', type=str, help='The heuristic rule/statement')
    parser.add_argument('--explanation', type=str, default='', help='Explanation of why this heuristic works')
    parser.add_argument('--source', type=str, default='observation',
                       choices=['failure', 'success', 'observation'],
                       help='Source type (default: observation)')
    parser.add_argument('--confidence', type=str, default='0.7',
                       help='Confidence level 0.0-1.0 or low/medium/high (default: 0.7)')
    parser.add_argument('--skip-validation', action='store_true',
                       help='Skip quality validation checks (use with caution)')
    
    # Location scope arguments
    parser.add_argument('--project', action='store_true',
                       help='Record as location-specific (tags with current directory)')
    parser.add_argument('--global', dest='global_scope', action='store_true',
                       help='Record as global (available everywhere, default)')
    parser.add_argument('--location', type=str,
                       help='Explicit location path for location-specific heuristic')

    args = parser.parse_args()

    # Check environment variables as fallback
    domain = args.domain or os.environ.get('HEURISTIC_DOMAIN')
    rule = args.rule or os.environ.get('HEURISTIC_RULE')
    explanation = args.explanation or os.environ.get('HEURISTIC_EXPLANATION', '')
    source_type = args.source or os.environ.get('HEURISTIC_SOURCE', 'observation')
    confidence_str = args.confidence or os.environ.get('HEURISTIC_CONFIDENCE', '0.7')

    # Pre-flight checks
    if not preflight_check():
        sys.exit(1)

    # Determine mode
    if domain and rule:
        # Non-interactive mode
        log("INFO", "Running in non-interactive mode")
        print("=== Record Heuristic (non-interactive) ===")
        confidence = parse_confidence(confidence_str)
        data = {
            'domain': domain,
            'rule': rule,
            'explanation': explanation,
            'source_type': source_type,
            'confidence': confidence,
        }
    elif sys.stdin.isatty():
        # Interactive mode (terminal attached)
        log("INFO", "Running in interactive mode")
        data = interactive_mode()
    else:
        # Not a terminal and no args - show usage
        log("INFO", "No terminal attached and no arguments provided - showing usage")
        print("Usage (non-interactive):")
        print('  python record-heuristic.py --domain "domain" --rule "the heuristic rule"')
        print('  Optional: --explanation "why" --source failure|success|observation --confidence 0.8')
        print()
        print("Or set environment variables:")
        print('  HEURISTIC_DOMAIN="domain" HEURISTIC_RULE="rule" python record-heuristic.py')
        sys.exit(0)

    # Determine location scope
    # New single-database approach: project_path column for location awareness
    # NULL = global (available everywhere)
    # path = location-specific (only shown when in that directory)
    project_path = None

    if args.location:
        # Explicit location path provided
        project_path = args.location
        print(f"[Recording with location: {project_path}]")
    elif args.project:
        # Use current working directory as location
        project_path = os.getcwd()
        print(f"[Recording with location: {project_path}]")
    elif args.global_scope:
        # Explicit global scope
        project_path = None
        print("[Recording as global heuristic]")
    else:
        # Default: global heuristic (NULL project_path)
        project_path = None

    # Record the heuristic using single-database with location tagging
    heuristic_id = record_heuristic_with_location(
        domain=data['domain'],
        rule=data['rule'],
        explanation=data['explanation'],
        source_type=data['source_type'],
        confidence=data['confidence'],
        project_path=project_path,
        skip_validation=args.skip_validation,
    )

    if heuristic_id is None:
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
