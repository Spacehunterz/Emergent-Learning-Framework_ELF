# Uninstalling ELF (Emergent Learning Framework)

This guide helps you cleanly remove ELF without breaking your Claude Code setup.

---

## Automated Uninstall Script (Recommended)

For the easiest uninstall experience, use the automated script:

### Windows (PowerShell)
```powershell
# Download and run uninstall script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/your-repo/ELF/main/scripts/uninstall.ps1" -OutFile "$env:TEMP\uninstall-elf.ps1"
PowerShell -ExecutionPolicy Bypass -File "$env:TEMP\uninstall-elf.ps1"
```

### Mac/Linux
```bash
# Download and run uninstall script
curl -fsSL https://raw.githubusercontent.com/your-repo/ELF/main/scripts/uninstall.sh | bash
```

The automated script will:
- Remove all ELF directories safely
- Clean up hooks from settings.json automatically
- Offer to backup your data before removal
- Validate that Claude Code still works after uninstall

**Note:** If you prefer manual control, use the manual steps below.

---

## Manual Quick Uninstall

### Windows (PowerShell)
```powershell
# Remove ELF files (keeps your Claude Code working)
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\emergent-learning"
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\hooks\learning-loop"

# Note: You'll need to manually edit settings.json to remove hooks
# See "Restore settings.json" below
```

### Mac/Linux
```bash
# Remove ELF files (keeps your Claude Code working)
rm -rf ~/.claude/emergent-learning
rm -rf ~/.claude/hooks/learning-loop

# Note: You'll need to manually edit settings.json to remove hooks
# See "Restore settings.json" below
```

---

## Restore settings.json

The installer added hooks to your `~/.claude/settings.json`. To remove them:

1. Open `~/.claude/settings.json` in a text editor

2. Find and remove the `PreToolUse` and `PostToolUse` sections that reference `learning-loop`:

   **Remove these blocks:**
   ```json
   "PreToolUse": [
     {
       "matcher": "Task",
       "hooks": [
         {
           "type": "command",
           "command": "python \"...learning-loop/pre_tool_learning.py\""
         }
       ]
     }
   ],
   "PostToolUse": [
     {
       "matcher": "Task",
       "hooks": [
         {
           "type": "command",
           "command": "python \"...learning-loop/post_tool_learning.py\""
         }
       ]
     }
   ]
   ```

3. If you had no other hooks, you can remove the entire `"hooks"` section, or leave it as:
   ```json
   {
     "hooks": {}
   }
   ```

4. Save the file

---

## Optional: Remove CLAUDE.md Changes

**WARNING:** CLAUDE.md contains important instructions for how Claude Code operates. Removing it will affect ALL your Claude Code sessions, not just ELF.

### Before Removing CLAUDE.md:

1. **Check if you had a pre-existing CLAUDE.md:**
   - If you installed ELF on a fresh system, ELF created this file
   - If you had Claude Code configured before ELF, you likely had your own CLAUDE.md
   - **The ELF installer preserves existing CLAUDE.md files** - it does NOT overwrite them

2. **Determine what's in your CLAUDE.md:**
   ```bash
   # View your CLAUDE.md file
   cat ~/.claude/CLAUDE.md
   
   # Check if it contains only ELF instructions
   grep -i "emergent learning" ~/.claude/CLAUDE.md
   ```

3. **Safe removal options:**

   **Option A: If ELF created it (safe to remove):**
   ```bash
   # Only remove if the file contains ONLY ELF instructions
   rm ~/.claude/CLAUDE.md
   ```

   **Option B: If you're unsure (safest):**
   ```bash
   # Backup first, then remove ELF sections manually
   cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.backup
   
   # Edit the file and remove only the ELF-related sections
   nano ~/.claude/CLAUDE.md  # or use your preferred editor
   ```

   **Option C: If you had pre-existing content (keep and edit):**
   ```bash
   # Just remove the ELF sections from CLAUDE.md
   # Keep your original Claude Code instructions
   ```

**What happens if you remove CLAUDE.md:**
- Claude Code will no longer follow the ELF query-before-acting protocol
- Any other custom instructions you had will also be removed
- Your Claude Code sessions will use default behavior only

**Recommendation:** Unless you're certain ELF created this file and you have no other use for CLAUDE.md, consider keeping it and removing only the ELF-specific sections.

---

## Keep Your Data (Optional)

If you want to keep your learned heuristics and history for later:

**What the backup includes:**
- Your learned heuristics and confidence scores
- Success/failure records
- Custom golden rules (if you modified them)
- CEO inbox items
- Agent run history

**What the backup does NOT include:**
- The ELF code itself (re-download from GitHub when reinstalling)
- Dashboard dependencies (will be reinstalled)
- Hook configurations (will be reconfigured during reinstall)

**Before uninstalling, backup:**
```bash
# Copy database (contains heuristics, failures, successes)
cp ~/.claude/emergent-learning/memory/index.db ~/elf-backup.db

# Copy golden rules (if you customized them)
cp ~/.claude/emergent-learning/memory/golden-rules.md ~/elf-golden-rules-backup.md

# Copy CEO inbox (pending decisions)
cp -r ~/.claude/emergent-learning/ceo-inbox ~/elf-ceo-inbox-backup

# Optional: Copy entire memory directory for complete backup
cp -r ~/.claude/emergent-learning/memory ~/elf-memory-backup
```

**To restore later after reinstalling:**
```bash
cp ~/elf-backup.db ~/.claude/emergent-learning/memory/index.db
```

---

## Verify Uninstall

After removing, verify Claude Code still works:

```bash
claude --version
```

And check no ELF directories remain:

```bash
ls ~/.claude/emergent-learning    # Should say "No such file or directory"
ls ~/.claude/hooks/learning-loop  # Should say "No such file or directory"
```

---

## Reinstalling

If you change your mind, just run the installer again:

```bash
./install.sh        # Mac/Linux
.\install.ps1       # Windows
```

Your previous database (if backed up) can be restored to preserve history.
