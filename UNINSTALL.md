# Uninstalling ELF (Emergent Learning Framework)

This guide helps you cleanly remove ELF without breaking your Claude Code setup.

---

## Quick Uninstall

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

If ELF created your `~/.claude/CLAUDE.md` file and you don't want it:

```bash
# View it first
cat ~/.claude/CLAUDE.md

# Remove if you don't need it
rm ~/.claude/CLAUDE.md
```

**Warning:** If you had your own CLAUDE.md before installing ELF, the installer didn't overwrite it. Only remove if ELF created it.

---

## Keep Your Data (Optional)

If you want to keep your learned heuristics and history for later:

**Before uninstalling, backup:**
```bash
# Copy database
cp ~/.claude/emergent-learning/memory/index.db ~/elf-backup.db

# Copy golden rules (if you customized them)
cp ~/.claude/emergent-learning/memory/golden-rules.md ~/elf-golden-rules-backup.md
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
