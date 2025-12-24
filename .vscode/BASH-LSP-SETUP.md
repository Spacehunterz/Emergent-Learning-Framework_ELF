# Bash Language Server LSP Setup

## Status: ✅ Configured

Shell scripts in the project now have Language Server Protocol (LSP) support for code intelligence and linting.

### Components Installed

- ✅ **bash-language-server** - Bash LSP implementation
- ✅ **ShellCheck** - Bash script analyzer (optional, improves linting)
- ✅ Configuration:
  - `.shellcheckrc` - ShellCheck rules configuration
  - `.vscode/start-bash-lsp-server.sh` - LSP startup script

### Features

Bash Language Server provides:
- **Syntax checking** - Detects syntax errors in real-time
- **Shell variable analysis** - Type and variable tracking
- **Code navigation** - Jump to variable definitions
- **Hover information** - Show variable types and definitions
- **Diagnostics** - Report errors and warnings

### Starting the LSP Server

**Option 1: Bash Script**
```bash
bash .vscode/start-bash-lsp-server.sh
```

**Option 2: Direct Command**
```bash
bash-language-server start
```

**Option 3: With Verbose Output**
```bash
bash-language-server start --debug
```

### Configuration

**ShellCheck Rules** (`.shellcheckrc`):
```ini
SC1090=warning    # Report all errors
SC2015=warning    # Coding conventions
SC2086=warning    # Quote prevention
SC2181=warning    # Return code checks
```

For full ShellCheck documentation, see: https://www.shellcheck.net/

### Type Checking Shell Scripts

Run ShellCheck directly:
```bash
shellcheck src/query/demo.sh
shellcheck tools/scripts/backup.sh
shellcheck -x apps/dashboard/run-dashboard.sh  # Follow sources
```

Or use bash-language-server which integrates ShellCheck:
```bash
bash-language-server --check src/query/demo.sh
```

### Shell Scripts in Project

Found **~30 shell scripts**:
- `install.sh` - Installation script
- `src/query/demo.sh` - Demo script
- `tests/*.sh` - Test suites
- `tools/scripts/*.sh` - Utility scripts
- `apps/dashboard/run-dashboard.sh` - Dashboard startup

### Using in Claude Code

Bash LSP communicates via stdio:

```python
# Bash LSP doesn't support goToDefinition like Python/TypeScript
# Instead, use it for diagnostics and analysis

# For static analysis, run:
# shellcheck -f json src/query/demo.sh
```

### Linting Examples

**Check single file:**
```bash
shellcheck src/query/demo.sh
```

Output:
```
In src/query/demo.sh line 5:
  if [ $? == 0 ]
       ^-- SC2181: Check exit code directly with e.g. 'if mycmd; then ...'

In src/query/demo.sh line 10:
  echo $MYVAR
         ^-- SC2086: Double quote to prevent globbing and word splitting.
```

**Check all shell scripts:**
```bash
find . -name "*.sh" -exec shellcheck {} \;
```

**Check and fix (with -x flag to follow sources):**
```bash
shellcheck -x apps/dashboard/run-dashboard.sh
```

### Common Shell Issues

**SC2086 - Double quote variables:**
```bash
# ❌ Wrong - variables expand and glob
echo $MYVAR
ls $DIR/*.txt

# ✅ Right - quoted
echo "$MYVAR"
ls "$DIR"/*.txt
```

**SC2181 - Check exit codes directly:**
```bash
# ❌ Wrong
some_command
if [ $? -eq 0 ]; then ...

# ✅ Right
if some_command; then ...
```

**SC2046 - Quote command substitution:**
```bash
# ❌ Wrong - splits on spaces
rm $(find . -name "*.tmp")

# ✅ Right - preserves spaces in filenames
rm $(find . -name "*.tmp" -print0) | xargs -0 rm
```

### Project Shell Scripts Analysis

Quick scan of shell scripts:
```bash
# Check all scripts
find . -name "*.sh" -not -path "*/node_modules/*" | xargs shellcheck -q

# Count issues by type
find . -name "*.sh" -not -path "*/node_modules/*" | xargs shellcheck -f json | \
  jq -r '.[].code' | sort | uniq -c | sort -rn
```

### Troubleshooting

**Server not starting:**
```bash
# Verify bash-language-server is installed
bash-language-server --version

# Reinstall if needed
npm install -g bash-language-server

# Verify it works
bash-language-server start
# (Should show: Server started on stdin/stdout)
```

**ShellCheck not found:**
```bash
# Check if installed
which shellcheck
shellcheck --version

# Install via package manager (if available):
# Ubuntu/Debian: sudo apt install shellcheck
# macOS: brew install shellcheck
# Or use npm: npm install -g shellcheck-cli (if available)
```

**Scripts have CRLF line endings:**
This is a common issue on Windows. Convert to LF:
```bash
# Using dos2unix
dos2unix script.sh

# Or using sed (if dos2unix unavailable)
sed -i 's/\r$//' script.sh
```

### Configuration Files

**`.shellcheckrc` example:**
```ini
# Global configuration
SC1090=warning     # Ignore sourced files error
SC1091=warning     # Ignore not-followed source
SC2086=warning     # Quote variables
SC2015=warning     # Condition precedence
```

### Next Steps

1. **Run analysis on all scripts:**
   ```bash
   find . -name "*.sh" -not -path "*/node_modules/*" -exec shellcheck {} \;
   ```

2. **Fix high-priority issues:**
   - SC2086 (quote variables)
   - SC2181 (check exit codes)
   - SC2046 (quote command substitution)

3. **Integrate into CI:**
   - Add ShellCheck to test pipeline
   - Fail on errors: `shellcheck -e SC1091 **/*.sh`

### References

- [ShellCheck Wiki](https://www.shellcheck.net/wiki/)
- [Bash Language Server](https://github.com/bash-lsp/bash-language-server)
- [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html)
