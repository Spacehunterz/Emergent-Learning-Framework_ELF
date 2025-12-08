# Getting Started with ELF (Emergent Learning Framework)

Complete setup guide - from zero to running.

---

## Step 0: Prerequisites

### Required: Claude Code CLI

ELF extends Claude Code. You need it installed first.

**Check if you have it:**
```bash
claude --version
```

**If not installed:**
```bash
npm install -g @anthropic-ai/claude-code
```
Or visit: https://docs.anthropic.com/en/docs/claude-code for installation options.
Then verify with `claude --version`.

### Required: Python 3.8+

**Check:**
```bash
python --version    # or python3 --version
```

**If not installed:**
- **Windows:** https://www.python.org/downloads/ (check "Add to PATH")
- **Mac:** `brew install python` or https://www.python.org/downloads/
- **Linux:** `sudo apt install python3` or your package manager

### Optional: Node.js or Bun (for Dashboard only)

Only needed if you want the visual dashboard.

**Check:**
```bash
node --version    # or
bun --version
```

**If not installed:**
- **Node.js:** https://nodejs.org/ (LTS version recommended)
- **Bun (faster):** https://bun.sh/

---

## Step 1: Download ELF

**Option A: Git clone**
```bash
git clone https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF.git
cd Emergent-Learning-Framework_ELF
```

**Option B: Download ZIP**
1. Go to the GitHub repo
2. Click "Code" > "Download ZIP"
3. Extract to a folder
4. Open terminal in that folder

---

## Step 2: Run the Installer

**Windows (PowerShell):**
```powershell
# If you get execution policy error, run this first:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Then run installer:
.\install.ps1
```

**Mac/Linux:**
```bash
chmod +x install.sh
./install.sh
```

### Installation Options

| Command | What it installs |
|---------|------------------|
| `./install.sh` | Everything (recommended for first time) |
| `./install.sh --core-only` | Just memory system, no dashboard or swarm |
| `./install.sh --no-dashboard` | Memory + swarm, skip dashboard |
| `./install.sh --no-swarm` | Memory + dashboard, skip multi-agent |

---

## Step 3: Verify Installation

Run this to check everything is working:

```bash
python ~/.claude/emergent-learning/query/query.py --validate
```

You should see:
```
Database validation passed
Tables: learnings, heuristics, metrics...
```

---

## Step 4: Start Using It

### Basic Usage (Automatic)

Just use Claude Code normally! The hooks will:
- Query the building before tasks
- Record outcomes after tasks

```bash
claude
```

That's it. The framework works in the background.

### View Your Dashboard (Optional)

If you installed the dashboard:

**Windows:**
```powershell
cd ~/.claude/emergent-learning/dashboard-app
.\run-dashboard.ps1
```

**Mac/Linux:**
```bash
cd ~/.claude/emergent-learning/dashboard-app
./run-dashboard.sh
```

Then open: http://localhost:3000

### Query the Building Manually

```bash
# See what Claude sees before tasks
python ~/.claude/emergent-learning/query/query.py --context

# Search by domain
python ~/.claude/emergent-learning/query/query.py --domain testing

# View statistics
python ~/.claude/emergent-learning/query/query.py --stats
```

---

## What Happens Next

### Day 1-7: Building Up
- Framework records successes and failures
- You won't notice much difference yet
- Heuristics start forming

### Week 2+: Patterns Emerge
- Repeated patterns gain confidence
- Claude starts receiving relevant context
- Fewer repeated mistakes

### Month 1+: Compound Effect
- High-confidence heuristics get promoted
- Your project has institutional memory
- Claude "knows" your project's quirks

---

## Troubleshooting

### "claude: command not found"
Claude Code isn't installed or not in PATH. See Step 0.

### "python: command not found"
Try `python3` instead, or install Python. See Step 0.

### "Permission denied" on Mac/Linux
```bash
chmod +x install.sh
chmod +x ~/.claude/emergent-learning/dashboard-app/run-dashboard.sh
```

### Dashboard won't start
- Check Node.js/Bun is installed: `node --version`
- Try reinstalling dependencies:
  ```bash
  cd ~/.claude/emergent-learning/dashboard-app/frontend
  npm install   # or: bun install
  ```

### Hooks not working
Check your settings file exists:
```bash
cat ~/.claude/settings.json
```

Should contain `"hooks"` with `"PreToolUse"` and `"PostToolUse"`.

### Want to start fresh
See `UNINSTALL.md` for clean removal instructions.

---

## Getting Help

- **Issues:** GitHub Issues on the repo
- **README:** Full documentation in README.md
- **Dashboard:** Visual interface at localhost:3000 (if installed)

---

## Quick Reference

| Task | Command |
|------|---------|
| Query building | `python ~/.claude/emergent-learning/query/query.py --context` |
| View stats | `python ~/.claude/emergent-learning/query/query.py --stats` |
| Start dashboard | `cd ~/.claude/emergent-learning/dashboard-app && ./run-dashboard.sh` |
| Validate install | `python ~/.claude/emergent-learning/query/query.py --validate` |
