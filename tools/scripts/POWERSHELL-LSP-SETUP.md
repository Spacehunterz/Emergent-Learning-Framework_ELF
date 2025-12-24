# PowerShell Language Server LSP Setup

## Status: ✅ Ready (Basic Mode)

PowerShell scripts in the project can be analyzed with PSScriptAnalyzer for code quality and compliance.

### Components Configured

- ✅ **PSScriptAnalyzer** - PowerShell code analysis
- ✅ **PowerShell 5.0+** - Required
- ✅ Script:
  - `tools/scripts/start-powershell-lsp.ps1` - Analysis script

### Features (Current)

PSScriptAnalyzer provides:
- **Best practices checking** - Detects unsafe patterns
- **Naming conventions** - Verifies cmdlet naming standards
- **Code style** - Enforces indentation and formatting
- **Security issues** - Flags hardcoded passwords, etc.
- **Performance** - Identifies inefficient patterns

### Features (Optional - Full LSP)

For full Language Server Protocol support, upgrade to:

**PowerShell Editor Services:**
```powershell
Install-Module PowerShellEditorServices -Scope CurrentUser -Force
```

This adds:
- Real-time diagnostics
- IntelliSense and auto-complete
- Go to definition
- Hover information
- Rename refactoring

### Starting Analysis

**Option 1: PowerShell Script**
```powershell
cd C:\Users\Evede\.gemini\antigravity\scratch\emergent-learning
.\tools\scripts\start-powershell-lsp.ps1
```

**Option 2: Direct PSScriptAnalyzer**
```powershell
Import-Module PSScriptAnalyzer
Invoke-ScriptAnalyzer -Path .\install.ps1
```

**Option 3: Analyze All Scripts**
```powershell
$scripts = Get-ChildItem -Recurse -Filter "*.ps1"
foreach ($script in $scripts) {
    Invoke-ScriptAnalyzer -Path $script.FullName
}
```

### Configuration

**Installed Analyzer Rules:**
```
✓ PSAvoidUsingCmdletAliases
✓ PSAvoidUsingPositionalParameters
✓ PSAvoidUsingPlainTextForPassword
✓ PSUseApprovedVerbs
✓ PSAvoidDefaultValueSwitchParameter
✓ PSMissingModuleManifestField
✓ PSReservedCmdletChar
✓ PSReservedParams
✓ PSUseBOMForUnicodeEncodedFile
✓ PSAvoidGlobalAliases
✓ PSAvoidGlobalFunctions
✓ PSAvoidGlobalVariables
✓ PSMisleadingBacktick
✓ PSPlaceCloseBrace
✓ PSPlaceOpenBrace
✓ PSProvideCommentHelp
✓ PSPossibleIncorrectComparisonWithNull
✓ PSPossibleIncorrectUsageOfRedirectionOperator
✓ PSUseConsistentIndentation
✓ PSUseConsistentWhitespace
✓ PSUseCorrectCasing
✓ PSUseDeclaredVarsMoreThanAssignments
```

### PowerShell Scripts in Project

Found **~10 PowerShell scripts**:
- `install.ps1` - Installation
- `apps/dashboard/run-dashboard.ps1` - Dashboard startup
- `apps/dashboard/start.ps1` - Dashboard start
- `tools/scripts/*.ps1` - Utility scripts
- `.venv/Scripts/Activate.ps1` - Virtual environment (auto-generated)

### Analyzing Scripts

**Single file:**
```powershell
Invoke-ScriptAnalyzer -Path .\install.ps1
```

Output example:
```
RuleName               : PSAvoidUsingPositionalParameters
Severity              : Warning
ScriptName            : install.ps1
Line                  : 15
Column                : 5
Message               : Position parameter should not be used
```

**All scripts (exclude .venv):**
```powershell
Get-ChildItem -Recurse -Filter "*.ps1" `
  -Exclude "Activate.ps1" |
  ForEach-Object { Invoke-ScriptAnalyzer -Path $_.FullName }
```

**Get count of issues:**
```powershell
Get-ChildItem -Recurse -Filter "*.ps1" |
  ForEach-Object {
    Invoke-ScriptAnalyzer -Path $_.FullName |
    Measure-Object | Select-Object -ExpandProperty Count
  }
```

### Common PowerShell Issues

**Avoid aliases:**
```powershell
# ❌ Wrong - uses alias
ls
pwd
cat file.txt

# ✅ Right - uses full names
Get-ChildItem
Get-Location
Get-Content file.txt
```

**Use approved verbs:**
```powershell
# ❌ Wrong
function Remove-All { ... }  # "All" is not approved

# ✅ Right
function Clear-All { ... }  # "Clear" is approved
```

**Avoid positional parameters:**
```powershell
# ❌ Wrong - uses position
Get-ChildItem -Recurse $true

# ✅ Right - uses name
Get-ChildItem -Recurse
```

**Avoid hardcoded passwords:**
```powershell
# ❌ Wrong - hardcoded
$password = "MySecretPassword123"
$cred = New-Object PSCredential -Args "user", (ConvertTo-SecureString $password -AsPlainText -Force)

# ✅ Right - read from secure store
$password = Read-Host -AsSecureString
$cred = New-Object PSCredential -Args "user", $password
```

### Using in Claude Code

For direct integration with Claude Code, use the script:

```powershell
# In PowerShell
.\tools\scripts\start-powershell-lsp.ps1

# This starts analysis mode for power commands
```

### Upgrading to Full LSP

For complete Language Server Protocol support:

**1. Install PowerShell Editor Services:**
```powershell
Install-Module PowerShellEditorServices -Scope CurrentUser -Force
```

**2. Update startup script:**
```powershell
$lsPath = Get-Module PowerShellEditorServices -ListAvailable |
  Select-Object -ExpandProperty ModuleBase

# Start LSP server on port 2089
& "$lsPath/PowerShellEditorServices.exe" `
  -ListenPort 2089 `
  -LogLevel Diagnostic
```

**3. Connect from Claude Code:**
- Configure to use `127.0.0.1:2089`
- Enjoy full PowerShell code intelligence

### Prerequisites for Full LSP

- PowerShell 5.0+ or PowerShell Core (pwsh)
- .NET Runtime
- Administrator access (for some features)

Check your version:
```powershell
$PSVersionTable.PSVersion
```

### Troubleshooting

**PSScriptAnalyzer not installed:**
```powershell
# Install
Install-Module PSScriptAnalyzer -Scope CurrentUser -Force

# Verify
Get-Module PSScriptAnalyzer -ListAvailable
```

**PowerShell version too old:**
```powershell
# Check version
$PSVersionTable.PSVersion

# If less than 5.0, upgrade:
# Windows: Install Windows Management Framework (WMF) 5.1
# Or: Download PowerShell Core from GitHub
```

**Module import fails:**
```powershell
# Set execution policy if needed
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# Then try import again
Import-Module PSScriptAnalyzer
```

### Next Steps

1. **Run analysis on all scripts:**
   ```powershell
   Get-ChildItem -Recurse -Filter "*.ps1" -Exclude "Activate.ps1" |
     ForEach-Object { Invoke-ScriptAnalyzer -Path $_.FullName }
   ```

2. **Fix critical issues:**
   - Remove hardcoded passwords
   - Use full cmdlet names (no aliases)
   - Use approved verbs
   - Fix parameter usage

3. **(Optional) Upgrade to full LSP:**
   - Install PowerShellEditorServices
   - Update .vscode settings
   - Configure port and startup

### References

- [PSScriptAnalyzer GitHub](https://github.com/PowerShell/PSScriptAnalyzer)
- [PowerShell Best Practices](https://docs.microsoft.com/en-us/powershell/scripting/developer/cmdlet/strongly-encouraged-development-guidelines)
- [PowerShell Approved Verbs](https://docs.microsoft.com/en-us/powershell/scripting/developer/cmdlet/approved-verbs-for-powershell-commands)
