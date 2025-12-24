# Pylance/Pyright LSP Setup for Emergent Learning Framework

## Status: ✅ Configured and Running

The project is now configured with Pylance/Pyright language server for full code intelligence.

### Components Installed

- ✅ **Pyright** (v1.1.407) - Type checker and language server
- ✅ **Python LSP Server** - Language Server Protocol implementation
- ✅ **pylsp-mypy** - Type checking via mypy
- ✅ Configuration files:
  - `pyrightconfig.json` - Pyright configuration
  - `pylsp_config.py` - LSP server configuration
  - `.vscode/settings.json` - VS Code settings

### Starting the LSP Server

**Option 1: Manual Start**
```bash
cd emergent-learning
python .vscode/start-lsp-server.py
```
The server will start on port **2087** (or next available port).

**Option 2: Auto-Start (Windows)**
Create a batch file at project root:
```batch
@echo off
python .vscode/start-lsp-server.py
pause
```

**Option 3: System Service**
Configure as Windows Service or systemd service for persistent operation.

### Connecting Claude Code

The LSP server listens on: `tcp://127.0.0.1:2087`

Configure Claude Code LSP settings to connect to this server for Python files (.py).

### Type Checking Results

Latest run (2025-12-23):
- **69 errors** (mostly constant redefinition pattern issues)
- **479 warnings** (unused imports, type issues)
- **3665 informations** (type hints needed)

### Configuration Details

**Pyright (`pyrightconfig.json`):**
- Python version: 3.8+
- Type checking mode: `basic`
- Included paths: `src/`, `scripts/`, `query/`, `tools/`
- Excluded: `.venv/`, `.git/`, `__pycache__/`

**LSP Server (`pylsp_config.py`):**
- Pyright enabled
- Mypy integration enabled (live mode)
- Pylint enabled
- Pycodestyle (PEP 8) enabled

### Using in Claude Code

Once configured:

```python
# Claude Code can now use:
LSP(
    operation="goToDefinition",
    filePath="src/conductor/conductor.py",
    line=15,
    character=10
)

LSP(
    operation="findReferences",
    filePath="src/query/query.py",
    line=50,
    character=5
)

LSP(
    operation="hover",
    filePath="src/conductor/executor.py",
    line=100,
    character=20
)
```

### Troubleshooting

**Server not starting:**
```bash
# Check if port is in use
netstat -ano | findstr :2087

# Run type check to verify Pyright works
python -m pyright src/ --outputjson
```

**Connection refused:**
- Ensure server is running: `python .vscode/start-lsp-server.py`
- Check firewall doesn't block localhost:2087
- Verify port with: `netstat -ano | findstr 2087`

**Type errors in output:**
- See type check results above
- Focus on errors (69 total) before warnings

### Next Steps

1. **Fix Constant Redefinition Errors** (high priority)
   - Pattern: `VAR = condition or VAR = fallback`
   - Solution: Use `if not VAR:` pattern instead

2. **Add Type Hints** to reduce "Unknown" types
   - Focus on function signatures
   - Dictionary/list return types

3. **Fix Optional Call Errors**
   - Add None checks before calling potentially None objects
