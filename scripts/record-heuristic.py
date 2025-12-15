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


def record_heuristic(
    domain: str,
    rule: str,
    explanation: str = "",
    source_type: str = "observation",
    confidence: float = 0.7
) -> Optional[int]:
    """
    Record a heuristic to the database and markdown file.

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

  # Non-interactive mode
  python record-heuristic.py --domain "error-handling" --rule "Always log before raising"
  python record-heuristic.py --domain testing --rule "Mock at boundaries" --confidence 0.8

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

    # Record the heuristic
    heuristic_id = record_heuristic(
        domain=data['domain'],
        rule=data['rule'],
        explanation=data['explanation'],
        source_type=data['source_type'],
        confidence=data['confidence'],
    )

    if heuristic_id is None:
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
