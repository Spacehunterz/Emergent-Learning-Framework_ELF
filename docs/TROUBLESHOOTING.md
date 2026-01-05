# Troubleshooting Guide

Solutions for common issues when developing with the Emergent Learning Framework.

## Setup Issues

### Issue: "Module not found" errors when running Python

**Symptoms:**
```
ModuleNotFoundError: No module named 'emergent_learning'
```

**Solution:**
Make sure your virtual environment is activated and dependencies are installed:

```bash
# Activate virtual environment
source .venv/bin/activate        # macOS/Linux
.venv\Scripts\activate           # Windows (cmd)
.venv\Scripts\Activate.ps1       # Windows (PowerShell)

# Install dependencies
pip install -r requirements.txt
cd apps/dashboard/backend && pip install -r requirements.txt
```

### Issue: Python version mismatch

**Symptoms:**
```
AttributeError: module 'sys' has no attribute 'version_info'
SyntaxError: invalid syntax (f-strings not supported)
```

**Solution:**
Check your Python version. ELF requires Python 3.8+:

```bash
python --version  # Must be 3.8+

# If wrong version:
# 1. Reinstall virtual environment
rm -rf .venv
python -m venv .venv

# 2. Activate and reinstall
source .venv/bin/activate
pip install -r requirements.txt
```

### Issue: Virtual environment won't activate on Windows

**Symptoms:**
```
PowerShell: cannot be loaded because running scripts is disabled on this system
```

**Solution:**
Try alternative activation methods:

```powershell
# Method 1: Using cmd.exe
cmd /c .venv\Scripts\activate.bat

# Method 2: Direct execution
.venv\Scripts\python.exe -m pip list

# Method 3: PowerShell with execution policy
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.venv\Scripts\Activate.ps1
```

### Issue: npm install hangs or fails

**Symptoms:**
```
npm ERR! 404 Not Found - GET https://registry.npmjs.org/...
npm WARN tarball tarball data for ... seems to be corrupted
```

**Solution:**
Clear npm cache and reinstall:

```bash
# Clear cache
npm cache clean --force

# Remove node_modules
rm -rf apps/dashboard/frontend/node_modules package-lock.json

# Reinstall with verbose output
cd apps/dashboard/frontend
npm ci --verbose
```

### Issue: Node.js version incompatibility

**Symptoms:**
```
npm ERR! This version of npm is incompatible with `node@...`
```

**Solution:**
Update Node.js or use compatible version manager:

```bash
# Check Node version (should be 16+)
node --version
npm --version

# Update npm if needed
npm install -g npm@latest

# Or use nvm (Node Version Manager)
nvm list
nvm use 18
```

---

## Development Server Issues

### Issue: Backend API won't start

**Symptoms:**
```
ERROR: address already in use
Port 8888 is in use
```

**Solution:**
The port is occupied. Either kill the process or use a different port:

```bash
# macOS/Linux: Find and kill process
lsof -i :8888
kill -9 <PID>

# Windows: Find and kill process
netstat -ano | findstr :8888
taskkill /PID <PID> /F

# Or use a different port
cd apps/dashboard/backend
python -m uvicorn main:app --port 8889
```

### Issue: Frontend dev server won't start

**Symptoms:**
```
Port 5173 is in use
EACCES: permission denied
```

**Solution:**
```bash
# Check if port is in use
lsof -i :5173  # macOS/Linux
netstat -ano | findstr :5173  # Windows

# Kill the process or use different port
cd apps/dashboard/frontend
npm run dev -- --port 5174
```

### Issue: Dashboard doesn't load at localhost:3001

**Symptoms:**
```
Connection refused
localhost:3001 refused to connect
```

**Solution:**
1. Verify backend and frontend are both running
2. Check that ports are correct:
   - Backend: http://localhost:8888/docs (FastAPI docs)
   - Frontend: http://localhost:5173 (Vite dev server)
   - Dashboard: Depends on where it's hosted

```bash
# Test backend is running
curl http://localhost:8888/docs

# Test frontend is running
curl http://localhost:5173

# Restart services
make dev
```

### Issue: "Connection refused" when accessing API

**Symptoms:**
```
Failed to fetch from http://localhost:8888
CORS error
```

**Solution:**
1. Verify backend is running on port 8888
2. Check CORS configuration in `apps/dashboard/backend/main.py`
3. Try accessing API directly:

```bash
# Test API is responding
curl -v http://localhost:8888/api/health

# If connection refused, backend isn't running
make dev-backend
```

---

## Testing Issues

### Issue: Tests fail with database errors

**Symptoms:**
```
sqlite3.OperationalError: no such table
ProgrammingError: relation does not exist
```

**Solution:**
Database may not be initialized or test database is corrupted:

```bash
# Run migrations
python scripts/migrate_db.py

# Or clear and reinit
rm -f *.db
python scripts/init-db.py

# Then run tests
make test
```

### Issue: Tests hang or timeout

**Symptoms:**
```
Test takes forever to complete
Timeout waiting for database
```

**Solution:**
Check for infinite loops or missing cleanup:

```bash
# Run with timeout
pytest tests/ --timeout=30

# Run single test with verbose output
pytest tests/test_example.py::test_function -vv -s

# Kill hanging processes
pkill -f pytest
```

### Issue: "Permission denied" when running tests

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: '...'
```

**Solution:**
Fix file permissions:

```bash
# macOS/Linux: Add execute permission to scripts
chmod +x scripts/*.sh
chmod +x scripts/*.py

# Or run with correct privileges
sudo make test  # (last resort)
```

---

## Code Quality Issues

### Issue: MyPy complains about type errors

**Symptoms:**
```
error: Incompatible types in assignment
error: Name "x" is not defined
```

**Solution:**
Add type hints or ignore specific lines:

```python
# Add type annotation
from typing import Optional
def my_function(value: Optional[str]) -> None:
    ...

# Or ignore specific error
x = some_function()  # type: ignore
```

To skip type checking temporarily:
```bash
# Run mypy in report-only mode
mypy src/ --no-error-summary --html mypy-report

# View results
open mypy-report/index.html
```

### Issue: Formatting conflicts between Black and Prettier

**Symptoms:**
```
Code passes Black but fails Prettier
Line length conflicts
```

**Solution:**
Configure both tools to agree:

Create `pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py38']
```

Create `apps/dashboard/frontend/.prettierrc.json`:
```json
{
  "printWidth": 100,
  "semi": true,
  "singleQuote": true,
  "trailingComma": "es5"
}
```

Then run:
```bash
make format  # Apply both Black and Prettier
```

---

## IDE/Editor Issues

### Issue: VSCode doesn't recognize Python path

**Symptoms:**
```
Pylance can't find module
IntelliSense not working for project code
```

**Solution:**
Update `.vscode/settings.json`:

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "python.analysis.extraPaths": ["${workspaceFolder}/src"],
  "python.analysis.include": ["src", "tests", "scripts"]
}
```

Or select interpreter:
- VSCode: Ctrl+Shift+P → "Python: Select Interpreter"
- Choose `.venv/bin/python` or `.venv\Scripts\python.exe`

### Issue: Debugger won't work

**Symptoms:**
```
Breakpoints not hit
Debugger session crashes
```

**Solution:**
Verify debug configuration in `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    }
  ]
}
```

Then:
1. Set breakpoint (click in gutter)
2. Press F5 to start debug
3. Run code that hits breakpoint

### Issue: Linting errors not showing in VSCode

**Symptoms:**
```
No red squiggles for linting errors
MyPy warnings don't appear
```

**Solution:**
Enable linting in `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "pylance.analysis.typeCheckingMode": "strict"
}
```

Or check directly:
```bash
make lint
```

---

## Git & Hooks Issues

### Issue: Pre-commit hook blocks commits

**Symptoms:**
```
❌ Commit blocked. Fix the invariant violations above.
```

**Solution:**
Fix the violations or bypass (only if necessary):

```bash
# View what failed
./scripts/check-invariants.sh

# Fix issues
# Then commit normally

# Or bypass (not recommended)
git commit --no-verify
```

### Issue: Pre-commit hook won't run

**Symptoms:**
```
Hook not executing
Changes committed without checks
```

**Solution:**
Reinstall hooks:

```bash
chmod +x .git/hooks/pre-commit
python scripts/install-hooks.py
```

---

## Dashboard Issues

### Issue: Dashboard shows "Loading..." forever

**Symptoms:**
```
Spinner keeps spinning
No data appears
```

**Solution:**
1. Check backend is running and responding:

```bash
curl http://localhost:8888/api/health
```

2. Check browser console for errors (F12)
3. Check network tab for failed requests
4. Restart backend:

```bash
make dev-backend
```

### Issue: Charts/visualizations don't render

**Symptoms:**
```
Blank white space where chart should be
Three.js errors in console
```

**Solution:**
Check browser compatibility and WebGL support:

```javascript
// In browser console
THREE.WEBGL.isWebGLAvailable()  // Should return true
```

If false, try different browser or enable WebGL in settings.

---

## Performance Issues

### Issue: Dashboard is slow/laggy

**Symptoms:**
```
High CPU usage
Frame drops when interacting
```

**Solution:**
1. Check React DevTools for unnecessary renders
2. Profile with Chrome DevTools Performance tab
3. Check for:
   - Unoptimized images
   - Missing memoization
   - Network requests in tight loops

```bash
# Build for production (faster)
make build
```

### Issue: Tests are very slow

**Symptoms:**
```
Test suite takes minutes to run
Single test is slow
```

**Solution:**
Identify slow tests:

```bash
# Run with timing
pytest tests/ -v --durations=10

# Run only fast tests
make test-fast

# Profile specific test
pytest tests/test_example.py::test_slow -v --profile
```

---

## Database Issues

### Issue: Database is locked

**Symptoms:**
```
sqlite3.OperationalError: database is locked
```

**Solution:**
SQLite can't handle concurrent access:

```bash
# Kill processes using database
lsof tests.db  # macOS/Linux
Handle /c/path/to/tests.db  # Windows

# Or restart services
make clean
make dev
```

### Issue: Missing database tables

**Symptoms:**
```
sqlite3.OperationalError: no such table: heuristics
```

**Solution:**
Initialize or migrate database:

```bash
# Create tables
python scripts/init-db.py

# Or run migrations
python scripts/migrate_db.py
```

---

## Getting Help

If you can't find your issue here:

1. **Check the logs:**
   ```bash
   cat logs/*.log
   tail -f logs/latest.log
   ```

2. **Ask for help in CONTRIBUTING.md**
   - See "Getting Help" section
   - Include error message
   - Include output of `make lint`

3. **Search GitHub issues:**
   - https://github.com/Spacehunterz/Emergent-Learning-Framework_ELF/issues

4. **Check recent changes:**
   ```bash
   git log --oneline -10
   git diff HEAD~5..HEAD
   ```

---

## Quick Diagnostics

Run this to check system health:

```bash
# Print diagnostic info
echo "=== System Info ==="
python --version
npm --version
node --version

echo "=== Virtual Environment ==="
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
which python

echo "=== Dependencies ==="
pip list | grep -E "(pytest|anthropic|fastapi)"

echo "=== Tests ==="
pytest tests/ --collect-only -q | head -10

echo "=== Database ==="
ls -lah *.db

echo "=== Ports ==="
lsof -i :8888  # macOS/Linux
netstat -ano | findstr :8888  # Windows

echo "=== Git Status ==="
git status
git log --oneline -3
```

Good luck debugging!
