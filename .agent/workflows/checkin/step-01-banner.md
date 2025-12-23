# Step 1: Display Banner

**Goal:** Show the ELF ASCII banner to signal the start of checkin.

## Implementation

```
┌────────────────────────────────────┐
│    Emergent Learning Framework     │
├────────────────────────────────────┤
│                                    │
│      █████▒  █▒     █████▒         │
│      █▒      █▒     █▒             │
│      ████▒   █▒     ████▒          │
│      █▒      █▒     █▒             │
│      █████▒  █████▒ █▒             │
│                                    │
└────────────────────────────────────┘
```

## Why This Step

The banner serves as:
- Visual confirmation that the checkin process started
- A recognizable signal to the user that they're in ELF context
- Consistency across all sessions

## Technical Details

- Displayed in `checkin.py` in `display_banner()` method
- Uses unicode box drawing characters (should work on all terminals)
- Always shown on every checkin (not conditional)
- Executed first, before any loading or prompting

## Output

- Blank line before banner
- Banner itself (8 lines)
- Blank line after banner
