# LSP Configuration Summary - Complete Setup

## Overview

Your project now has Language Server Protocol (LSP) configured for both **Python** and **TypeScript**, enabling full code intelligence across the entire codebase.

---

## Python LSP Setup

**Location:** `C:\Users\Evede\.gemini\antigravity\scratch\emergent-learning\`

### Components
- **Pyright** (v1.1.407) - Python type checker
- **Python LSP Server** - Protocol implementation
- **pylsp-mypy** - Type checking

### Configuration Files
- `pyrightconfig.json` - Pyright settings
- `pylsp_config.py` - LSP server configuration
- `.vscode/settings.json` - VS Code settings
- `.vscode/start-lsp-server.py` - Startup script
- `.vscode/LSP-SETUP.md` - Full documentation

### Server Status
- **Port:** `127.0.0.1:2087`
- **Status:** ✅ Running
- **Mode:** TCP socket
- **Start command:** `python .vscode/start-lsp-server.py`

### Type Check Results
```
69 errors | 479 warnings | 3665 informations
```

**Key Issues:**
- Constant redefinition (53 errors) - pattern: `VAR = condition or VAR = fallback`
- Optional calls (2 errors) - calling None values
- Missing type hints - Unknown types

### Supported Operations
```python
LSP(operation="goToDefinition", filePath="src/query/query.py", line=10, character=5)
LSP(operation="findReferences", filePath="src/conductor/conductor.py", line=50, character=10)
LSP(operation="hover", filePath="src/query/context.py", line=25, character=15)
LSP(operation="documentSymbol", filePath="src/watcher/watcher_loop.py", line=1, character=1)
```

---

## TypeScript LSP Setup

**Location:** `C:\Users\Evede\.gemini\antigravity\scratch\emergent-learning\apps\dashboard\frontend\`

### Components
- **TypeScript** (v5.9.3) - Language and type checker
- **typescript-language-server** - LSP implementation

### Configuration Files
- `tsconfig.json` - TypeScript compiler settings (strict mode)
- `.vscode/settings.json` - VS Code settings
- `.vscode/start-ts-lsp-server.js` - Startup script
- `.vscode/TS-LSP-SETUP.md` - Full documentation

### Server Status
- **Mode:** stdio (standard input/output)
- **Default Port:** 2088 (when using TCP)
- **Start command:** `node .vscode/start-ts-lsp-server.js`
- **Alt command:** `npx typescript-language-server --stdio`

### Type Check Results
```
146 TypeScript errors
```

**Key Issues:**
- Unused variables/imports (majority)
- Type mismatches (property doesn't exist)
- Union type issues (value not in type)
- Missing type hints (inferred as `unknown`)

### Supported Operations
```python
LSP(operation="goToDefinition", filePath="apps/dashboard/frontend/src/App.tsx", line=20, character=10)
LSP(operation="findReferences", filePath="apps/dashboard/frontend/src/components/CommandPalette.tsx", line=30, character=5)
LSP(operation="hover", filePath="apps/dashboard/frontend/src/hooks/useWebSocket.ts", line=15, character=20)
LSP(operation="documentSymbol", filePath="apps/dashboard/frontend/src/App.tsx", line=1, character=1)
```

---

## Comparison

| Aspect | Python | TypeScript |
|--------|--------|-----------|
| **Root** | Project root | `apps/dashboard/frontend/` |
| **LSP Server** | Pyright | typescript-language-server |
| **Configuration** | `pyrightconfig.json` | `tsconfig.json` |
| **Protocol** | TCP (stdio possible) | stdio (TCP possible) |
| **Port** | 2087 | 2088 |
| **Type Errors** | 69 | 146 |
| **Warnings** | 479 | N/A (counted in errors) |
| **Startup** | Python script | Node.js script |
| **Strictness** | Basic mode | Strict mode |

---

## Using LSP in Claude Code

### Prerequisites
1. Both LSP servers must be running
2. File paths must be absolute or relative to project root
3. Line and character numbers are 1-based

### Common Operations

**Navigate to Function Definition:**
```python
LSP(
    operation="goToDefinition",
    filePath="src/conductor/conductor.py",
    line=42,
    character=15
)
```

**Find All References to a Variable:**
```python
LSP(
    operation="findReferences",
    filePath="src/query/query.py",
    line=88,
    character=5
)
```

**Get Type Information:**
```python
LSP(
    operation="hover",
    filePath="apps/dashboard/frontend/src/App.tsx",
    line=25,
    character=10
)
```

**List All Symbols in File:**
```python
LSP(
    operation="documentSymbol",
    filePath="src/watcher/watcher_loop.py",
    line=1,
    character=1
)
```

**Search for Symbol Across Workspace:**
```python
LSP(
    operation="workspaceSymbol",
    filePath="src/query/query.py",
    line=1,
    character=1
)
```

---

## Starting Both Servers

**Terminal 1 - Python LSP:**
```bash
cd C:\Users\Evede\.gemini\antigravity\scratch\emergent-learning
python .vscode/start-lsp-server.py
```

**Terminal 2 - TypeScript LSP:**
```bash
cd C:\Users\Evede\.gemini\antigravity\scratch\emergent-learning\apps\dashboard\frontend
node .vscode/start-ts-lsp-server.js
```

Both servers will run continuously and accept connections from Claude Code.

---

## Troubleshooting

### Python LSP Issues
```bash
# Verify Pyright works
python -m pyright src/ --outputjson

# Check port
netstat -ano | findstr :2087

# Restart server
python .vscode/start-lsp-server.py
```

### TypeScript LSP Issues
```bash
# Verify TypeScript works
npx tsc --noEmit

# Check installation
npm list typescript-language-server

# Restart server
node .vscode/start-ts-lsp-server.js
```

### Connection Issues
- Ensure servers are running (check ports with netstat)
- Verify file paths are correct (absolute or relative to root)
- Check line/character numbers are 1-based
- Ensure file exists before querying

---

## Shell Script LSP Setup

**Location:** Project root

### Components
- **bash-language-server** (v5.6.0) - Bash LSP implementation
- **ShellCheck** - Optional Bash linting (improves diagnostics)

### Configuration Files
- `.shellcheckrc` - ShellCheck configuration
- `.vscode/start-bash-lsp-server.sh` - LSP startup script
- `.vscode/BASH-LSP-SETUP.md` - Full documentation

### Server Status
- **Mode:** stdio (standard input/output)
- **Start command:** `bash .vscode/start-bash-lsp-server.sh`
- **Features:** Syntax checking, variable analysis, diagnostics

### Shell Scripts in Project
Found **~30 shell scripts**:
- Installation scripts
- Test suites
- Utility scripts
- Dashboard startup

---

## PowerShell LSP Setup

**Location:** `tools/scripts/`

### Components
- **PSScriptAnalyzer** - PowerShell code analysis
- **PowerShell 5.0+** - Required

### Configuration Files
- `tools/scripts/start-powershell-lsp.ps1` - Analysis script
- `tools/scripts/POWERSHELL-LSP-SETUP.md` - Full documentation

### Features
- Best practices checking
- Naming convention validation
- Code style analysis
- Security issue detection

### PowerShell Scripts in Project
Found **~10 PowerShell scripts**:
- Installation scripts
- Dashboard startup
- Utility scripts

### Optional Upgrade
Install PowerShell Editor Services for full LSP:
```powershell
Install-Module PowerShellEditorServices -Scope CurrentUser -Force
```

---

## Next Steps

**For Python:**
1. Fix constant redefinition errors (patterns)
2. Add type hints to reduce Unknown types
3. Fix optional call errors

**For TypeScript:**
1. Remove unused variables/imports
2. Fix type mismatches
3. Add proper type guards for union types

**For Shell Scripts:**
1. Install ShellCheck (if not already available)
2. Run analysis on all .sh files
3. Fix quote issues (SC2086) and exit code checks (SC2181)

**For PowerShell Scripts:**
1. Run PSScriptAnalyzer analysis
2. Fix cmdlet naming and aliases
3. Remove hardcoded passwords
4. Use approved verbs in function names

---

## Documentation

Full setup guides available at:
- Python: `.vscode/LSP-SETUP.md`
- TypeScript: `apps/dashboard/frontend/.vscode/TS-LSP-SETUP.md`
- Shell (Bash): `.vscode/BASH-LSP-SETUP.md`
- PowerShell: `tools/scripts/POWERSHELL-LSP-SETUP.md`
- Complete Overview: `LSP-CONFIGURATION-SUMMARY.md` (this file)
