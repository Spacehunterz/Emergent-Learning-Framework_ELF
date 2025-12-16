"""
Output formatting functions for the Query System.

Contains:
- format_output: Multi-format output (text, json, csv)
- generate_accountability_banner: Violation report banner
"""

import io
import csv
import json
from typing import Any, Dict


def generate_accountability_banner(summary: Dict[str, Any]) -> str:
    """
    Generate a visually distinct accountability banner showing violation status.

    Args:
        summary: Violation summary from get_violation_summary()

    Returns:
        Formatted banner string with box drawing characters
    """
    total = summary['total']
    days = summary['days']
    by_rule = summary['by_rule']
    recent = summary['recent']

    # Determine status level
    if total >= 10:
        status = "CRITICAL"
        status_color = "RED"
        message = "CEO ESCALATION REQUIRED"
    elif total >= 5:
        status = "PROBATION"
        status_color = "YELLOW"
        message = "INCREASED SCRUTINY MODE"
    elif total >= 3:
        status = "WARNING"
        status_color = "YELLOW"
        message = "Review adherence to rules"
    else:
        status = "NORMAL"
        status_color = "GREEN"
        message = "Acceptable compliance level"

    # Build banner
    banner = []
    banner.append("╔═══════════════════════════════════════════════════════════════════════╗")
    banner.append("║                    ACCOUNTABILITY TRACKING SYSTEM                     ║")
    banner.append("║                     Golden Rule Violation Report                      ║")
    banner.append("╠═══════════════════════════════════════════════════════════════════════╣")
    banner.append(f"║  Period: Last {days} days                                                     ║")
    banner.append(f"║  Total Violations: {total:<54} ║")
    banner.append(f"║  Status: {status:<60} ║")
    banner.append(f"║  {message:<68} ║")
    banner.append("╠═══════════════════════════════════════════════════════════════════════╣")

    if by_rule:
        banner.append("║  Violations by Rule:                                                  ║")
        for rule in by_rule[:5]:  # Top 5 rules
            rule_line = f"║    Rule #{rule['rule_id']}: {rule['rule_name'][:35]:<35} ({rule['count']:>2}x) ║"
            banner.append(rule_line)
        if len(by_rule) > 5:
            banner.append(f"║    ... and {len(by_rule) - 5} more                                                  ║")
        banner.append("╠═══════════════════════════════════════════════════════════════════════╣")

    if recent:
        banner.append("║  Recent Violations:                                                   ║")
        for v in recent[:3]:  # Top 3 recent
            date_str = v['date'][:16] if v['date'] else "Unknown"
            desc = v['description'][:45] if v['description'] else "No description"
            banner.append(f"║    [{date_str}] Rule #{v['rule_id']:<2}                                   ║")
            banner.append(f"║      {desc:<66} ║")
        banner.append("╠═══════════════════════════════════════════════════════════════════════╣")

    # Progressive consequences
    if total >= 10:
        banner.append("║  ⚠️  CONSEQUENCES: CEO escalation auto-created in ceo-inbox/          ║")
    elif total >= 5:
        banner.append("║  ⚠️  CONSEQUENCES: Under probation - violations logged prominently    ║")
    elif total >= 3:
        banner.append("║  ⚠️  CONSEQUENCES: Warning threshold - 2 more violations = probation  ║")
    else:
        banner.append("║  ✓  STATUS: Acceptable compliance. Keep up good practices.            ║")

    banner.append("╚═══════════════════════════════════════════════════════════════════════╝")

    return "\n".join(banner)


def format_output(data: Any, format_type: str = 'text') -> str:
    """
    Format query results for display.

    Args:
        data: Data to format
        format_type: Output format ('text', 'json', or 'csv')

    Returns:
        Formatted string
    """
    if format_type == 'json':
        return json.dumps(data, indent=2, default=str)

    elif format_type == 'csv':
        # CSV formatting for list data
        if isinstance(data, list) and data:
            output = io.StringIO()
            if isinstance(data[0], dict):
                writer = csv.DictWriter(output, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
            else:
                writer = csv.writer(output)
                for item in data:
                    writer.writerow([item])
            return output.getvalue()
        else:
            return str(data)

    # Text formatting
    if isinstance(data, dict):
        lines = []
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                lines.append(f"{key}:")
                lines.append(format_output(value, format_type))
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    elif isinstance(data, list):
        lines = []
        for i, item in enumerate(data, 1):
            lines.append(f"\n--- Item {i} ---")
            lines.append(format_output(item, format_type))
        return "\n".join(lines)

    else:
        return str(data)
