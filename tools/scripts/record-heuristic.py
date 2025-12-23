#!/usr/bin/env python3
"""
Record a heuristic in the Emergent Learning Framework

Usage (interactive): python record-heuristic.py
Usage (non-interactive):
  python record-heuristic.py --domain "domain" --rule "rule" --explanation "why"
  Optional: --source failure|success|observation --confidence 0.8
"""

import sqlite3
import argparse
import os
import sys
import re
from pathlib import Path
from datetime import datetime
import logging

# Setup logging
script_dir = Path(__file__).parent
base_dir = script_dir.parent
logs_dir = base_dir / "logs"
logs_dir.mkdir(exist_ok=True)

log_file = logs_dir / f"{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [record-heuristic] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stderr)
    ]
)
logger = logging.getLogger(__name__)

# Database path
db_path = base_dir / "memory" / "index.db"
heuristics_dir = base_dir / "memory" / "heuristics"

# Input constraints
MAX_RULE_LENGTH = 500
MAX_DOMAIN_LENGTH = 100
MAX_EXPLANATION_LENGTH = 5000


def sanitize_input(text):
    """Sanitize input: strip control chars, normalize whitespace"""
    if not text:
        return ""
    # Remove control characters (keep printable + space/tab)
    text = ''.join(c for c in text if c.isprintable() or c in '\t\n\r')
    # Normalize multiple spaces to single
    text = ' '.join(text.split())
    return text.strip()


def validate_confidence(confidence_str):
    """Validate and convert confidence to float"""
    if not confidence_str:
        return 0.7

    # Try to parse as float
    try:
        conf = float(confidence_str)
        if 0.0 <= conf <= 1.0:
            return conf
    except ValueError:
        pass

    # Try word conversion
    words = {
        'low': 0.3,
        'medium': 0.6,
        'high': 0.85
    }
    if confidence_str.lower() in words:
        return words[confidence_str.lower()]

    logger.warning(f"Invalid confidence '{confidence_str}', defaulting to 0.7")
    return 0.7


def sanitize_domain(domain):
    """Sanitize domain to prevent path traversal"""
    domain = domain.lower()
    domain = re.sub(r'[^a-z0-9\-]', '', domain.replace(' ', '-'))
    domain = domain.strip('-')[:100]
    return domain


def preflight_check():
    """Verify database and directory structure"""
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        print(f"ERROR: Database not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    heuristics_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Pre-flight checks passed")


def record_heuristic(domain, rule, explanation, source_type, confidence):
    """Record heuristic to database and markdown file"""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO heuristics
            (domain, rule, explanation, source_type, confidence, times_validated, times_violated, is_golden, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 0, 0, 0, ?, ?)
        """, (domain, rule, explanation, source_type, confidence, now, now))

        heuristic_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Database record created (ID: {heuristic_id})")
        print(f"Database record created (ID: {heuristic_id})")

        # Write to markdown file
        domain_file = heuristics_dir / f"{domain}.md"

        if not domain_file.exists():
            with open(domain_file, 'w') as f:
                f.write(f"# Heuristics: {domain}\n\n")
                f.write(f"Generated from failures, successes, and observations in the **{domain}** domain.\n\n")
                f.write("---\n\n")
            logger.info(f"Created new domain file: {domain_file}")

        with open(domain_file, 'a') as f:
            f.write(f"## H-{heuristic_id}: {rule}\n\n")
            f.write(f"**Confidence**: {confidence}\n")
            f.write(f"**Source**: {source_type}\n")
            f.write(f"**Created**: {datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write(f"{explanation}\n\n")
            f.write("---\n\n")

        print(f"Appended to: {domain_file}")
        logger.info(f"Appended heuristic to: {domain_file}")
        logger.info(f"Heuristic recorded successfully: {rule}")
        print("\nHeuristic recorded successfully!")

        return True

    except Exception as e:
        logger.error(f"Failed to record heuristic: {e}")
        print(f"ERROR: Failed to record heuristic: {e}", file=sys.stderr)
        return False


def interactive_mode():
    """Interactive prompt for heuristic input"""
    print("=== Record Heuristic ===\n")

    domain = input("Domain: ").strip()
    if not domain:
        logger.error("Domain cannot be empty")
        print("ERROR: Domain cannot be empty", file=sys.stderr)
        sys.exit(1)

    rule = input("Rule (the heuristic): ").strip()
    if not rule:
        logger.error("Rule cannot be empty")
        print("ERROR: Rule cannot be empty", file=sys.stderr)
        sys.exit(1)

    explanation = input("Explanation: ").strip()

    source_type = input("Source type (failure/success/observation) [observation]: ").strip()
    if not source_type:
        source_type = "observation"

    confidence = input("Confidence (0.0-1.0) [0.7]: ").strip()
    if not confidence:
        confidence = "0.7"

    return domain, rule, explanation, source_type, confidence


def main():
    preflight_check()

    parser = argparse.ArgumentParser(description="Record a heuristic in the Emergent Learning Framework")
    parser.add_argument('--domain', help='Domain for the heuristic')
    parser.add_argument('--rule', help='The heuristic rule')
    parser.add_argument('--explanation', help='Explanation of the heuristic')
    parser.add_argument('--source', dest='source_type', help='Source type (failure/success/observation)')
    parser.add_argument('--confidence', help='Confidence level (0.0-1.0)')

    args = parser.parse_args()

    logger.info("Script started")

    # Determine interactive vs non-interactive mode
    if args.domain and args.rule:
        domain = args.domain
        rule = args.rule
        explanation = args.explanation or ""
        source_type = args.source_type or "observation"
        confidence = args.confidence or "0.7"
        logger.info("Running in non-interactive mode")
        print("=== Record Heuristic (non-interactive) ===")
    elif not sys.stdin.isatty():
        logger.info("No terminal attached and no arguments provided - showing usage")
        print("Usage (non-interactive):")
        print(f"  python {sys.argv[0]} --domain \"domain\" --rule \"the heuristic rule\"")
        print("  Optional: --explanation \"why\" --source failure|success|observation --confidence 0.8")
        sys.exit(0)
    else:
        logger.info("Running in interactive mode")
        domain, rule, explanation, source_type, confidence = interactive_mode()

    # Validate and sanitize inputs
    domain = sanitize_domain(domain)
    if not domain:
        logger.error("Domain resulted in empty string after sanitization")
        print("ERROR: Domain resulted in empty string after sanitization", file=sys.stderr)
        sys.exit(1)

    if len(rule) > MAX_RULE_LENGTH:
        logger.error(f"Rule exceeds maximum length ({MAX_RULE_LENGTH} chars)")
        print(f"ERROR: Rule too long (max {MAX_RULE_LENGTH} characters)", file=sys.stderr)
        sys.exit(1)

    if len(explanation) > MAX_EXPLANATION_LENGTH:
        logger.error("Explanation exceeds maximum length")
        print(f"ERROR: Explanation too long (max {MAX_EXPLANATION_LENGTH} characters)", file=sys.stderr)
        sys.exit(1)

    rule = sanitize_input(rule)
    explanation = sanitize_input(explanation)
    confidence = validate_confidence(confidence)

    logger.info(f"Recording heuristic: {rule} (domain: {domain}, confidence: {confidence})")

    if record_heuristic(domain, rule, explanation, source_type, confidence):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
