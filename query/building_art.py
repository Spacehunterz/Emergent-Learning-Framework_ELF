#!/usr/bin/env python3
"""
Building ASCII Art for Emergent Learning Framework check-in.
Uses a mix of box-drawing characters and braille for a polished look.
"""

# ANSI color codes
CYAN = "\033[96m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
WHITE = "\033[97m"
RESET = "\033[0m"
DIM = "\033[2m"


def get_building_art_v1() -> str:
    """Version 1: Classic stick figure with ASCII."""
    art = f"""
{CYAN} ⚡{RESET}  {YELLOW}│{RESET}  {CYAN}⚡{RESET}
     {YELLOW}╽{RESET}
  {WHITE}┌──┴──┐{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}o{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET} {WHITE}/|\\{RESET}
  {WHITE}│{RESET}{YELLOW}┌─┐{RESET}{WHITE}│{RESET} {WHITE}/ \\{RESET}
  {WHITE}└┴─┴┘{RESET}
"""
    return art


def get_building_art_v2() -> str:
    """Version 2: Braille body stick figure."""
    art = f"""
{CYAN} ⚡{RESET}  {YELLOW}│{RESET}  {CYAN}⚡{RESET}
     {YELLOW}╽{RESET}
  {WHITE}┌──┴──┐{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}⣀⡀{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}⢸⡇{RESET}
  {WHITE}│{RESET}{YELLOW}┌─┐{RESET}{WHITE}│{RESET}  {WHITE}⠸⠇{RESET}
  {WHITE}└┴─┴┘{RESET}
"""
    return art


def get_building_art_v3() -> str:
    """Version 3: Walking braille figure with round head."""
    art = f"""
{CYAN} ⚡{RESET}  {YELLOW}│{RESET}  {CYAN}⚡{RESET}
     {YELLOW}╽{RESET}
  {WHITE}┌──┴──┐{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}○{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET} {WHITE}⢱⡱{RESET}
  {WHITE}│{RESET}{YELLOW}┌─┐{RESET}{WHITE}│{RESET} {WHITE}⠈⠁{RESET}
  {WHITE}└┴─┴┘{RESET}
"""
    return art


def get_building_art_v4() -> str:
    """Version 4: Braille walking person - clean silhouette."""
    # ⣿ = full block, ⡗⢎ = walking legs, ⠁⠈ = feet
    art = f"""
{CYAN} ⚡{RESET}  {YELLOW}│{RESET}  {CYAN}⚡{RESET}
     {YELLOW}╽{RESET}
  {WHITE}┌──┴──┐{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}   {WHITE}○{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}⣿⣿{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}⡗⢎{RESET}
  {WHITE}│{RESET}{YELLOW}┌─┐{RESET}{WHITE}│{RESET}
  {WHITE}└┴─┴┘{RESET}
"""
    return art


def get_building_art_v5() -> str:
    """Version 5: Person with arm reaching toward door."""
    art = f"""
{CYAN} ⚡{RESET}  {YELLOW}│{RESET}  {CYAN}⚡{RESET}
     {YELLOW}╽{RESET}
  {WHITE}┌──┴──┐{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}   {WHITE}○{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET} {WHITE}⢀⣿⣀{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}⠋⠙{RESET}
  {WHITE}│{RESET}{YELLOW}┌─┐{RESET}{WHITE}│{RESET}
  {WHITE}└┴─┴┘{RESET}
"""
    return art


def get_building_art_v6() -> str:
    """Version 6: Running into the building (dynamic pose)."""
    art = f"""
{CYAN} ⚡{RESET}  {YELLOW}│{RESET}  {CYAN}⚡{RESET}
     {YELLOW}╽{RESET}
  {WHITE}┌──┴──┐{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}○{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET} {WHITE}⣠⣿⡄{RESET}
  {WHITE}│{RESET} {DIM}◦ ◦{RESET} {WHITE}│{RESET}  {WHITE}⠓⠚{RESET}
  {WHITE}│{RESET}{YELLOW}┌─┐{RESET}{WHITE}│{RESET}
  {WHITE}└┴─┴┘{RESET}
"""
    return art


def get_building_art_v7() -> str:
    """Version 7: Simple tall building with person - minimal tokens."""
    art = f"""
{CYAN}⚡{RESET} {YELLOW}│{RESET} {CYAN}⚡{RESET}
   {YELLOW}╽{RESET}
 {WHITE}┌─┴─┐{RESET}
 {WHITE}│{RESET}{DIM}◦ ◦{RESET}{WHITE}│{RESET}
 {WHITE}│{RESET}{DIM}◦ ◦{RESET}{WHITE}│{RESET}
 {WHITE}│{RESET}{DIM}◦ ◦{RESET}{WHITE}│{RESET}
 {WHITE}│{RESET}{DIM}◦ ◦{RESET}{WHITE}│{RESET}  {WHITE}○{RESET}
 {WHITE}│{RESET}{DIM}◦ ◦{RESET}{WHITE}│{RESET} {WHITE}⣿{RESET}
 {WHITE}│{RESET}{YELLOW}┌┐{RESET}{WHITE}│{RESET} {WHITE}⠿{RESET}
 {WHITE}└┴┴┘{RESET}
"""
    return art


GREEN = "\033[92m"
BOLD = "\033[1m"


def get_building_art_final() -> str:
    """
    FINAL: Clean building design with asymmetric bolts and enhanced colors.
    """
    art = f"""
               ⚡
     ⚡    │
          ┌┴┐
    ┌─────┴─┴─────┐
    │ {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} │
    │             │
    │ {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} │
    │             │
    │ {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} │
    │             │
    │ {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} │
    │             │
    │ {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} {CYAN}░░{RESET} │
    │    ┌───┐    │
    └────┴───┴────┘
"""
    return art


def get_checkin_display(golden_rules: list = None) -> str:
    """
    CHECK-IN COMPLETE display with building on left, golden rules on right.
    Hardcoded layout for perfect alignment.
    """
    # Hardcoded for perfect alignment - emojis and ANSI codes make dynamic padding unreliable
    # Bolt alignment matches get_building_art_final exactly
    return f"""
               {YELLOW}⚡{RESET}          {GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
     {YELLOW}⚡{RESET}    │             {GREEN}{BOLD}    ✓ CHECK-IN COMPLETE ✓{RESET}
          ┌┴┐            {GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}
    ┌─────┴─┴─────┐
    │ 🟦 🟦 🟦 🟦 │       {BOLD}Golden Rules:{RESET}
    │             │         1. Query Before Acting
    │ 🟦 🟦 🟦 🟦 │         2. Document Failures Immediately
    │             │         3. Extract Heuristics, Not Just Outcomes
    │ 🟦 🟦 🟦 🟦 │         4. Break It Before Shipping It
    │             │         5. Escalate Uncertainty
    │ 🟦 🟦 🟦 🟦 │         6. Record Learnings Before Ending Session
    │             │         7. Obey Direct Commands Immediately
    │ 🟦 🟦 🟦 🟦 │         8. Log Before Summary
    │    ┌───┐    │
    └────┴───┴────┘
"""


if __name__ == "__main__":
    import sys
    import io
    # Fix Windows console encoding for Unicode characters
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Check for flags
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        versions = [
            ("v1 - Classic ASCII stick figure", get_building_art_v1),
            ("v2 - Braille body", get_building_art_v2),
            ("v3 - Walking + round head", get_building_art_v3),
            ("v4 - Braille walking silhouette", get_building_art_v4),
            ("v5 - Arm reaching", get_building_art_v5),
            ("v6 - Running/dynamic", get_building_art_v6),
            ("v7 - Minimal tokens", get_building_art_v7),
            ("FINAL - Balanced design", get_building_art_final),
        ]
        for name, fn in versions:
            print(f"\n=== {name} ===")
            print(fn())
    elif len(sys.argv) > 1 and sys.argv[1] == "--checkin":
        # Full check-in display with building + golden rules
        print(get_checkin_display())
    else:
        # Default: just print the final version
        print(get_building_art_final())
