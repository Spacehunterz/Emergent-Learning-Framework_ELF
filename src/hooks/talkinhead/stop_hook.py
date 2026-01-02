#!/usr/bin/env python3
"""
Stop Hook - Triggers TalkinHead 'completed' phrase when Claude finishes responding.
"""

import json
import time
from pathlib import Path

EVENT_FILE = Path.home() / ".claude" / "ivy_events.json"


def main():
    event = {
        "event": "completed",
        "message": "Response complete",
        "timestamp": time.time()
    }
    EVENT_FILE.write_text(json.dumps(event))


if __name__ == "__main__":
    main()
