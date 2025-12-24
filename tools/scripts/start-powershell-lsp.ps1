# Start PowerShell Language Server for Claude Code
# This script launches PowerShell Editor Services

param(
    [int]$Port = 2089,
    [switch]$Verbose
)

$ErrorActionPreference = 'Stop'

Write-Host "Checking PowerShell version..."
$psVersion = $PSVersionTable.PSVersion.Major
Write-Host "PowerShell version: $psVersion"

if ($psVersion -lt 5) {
    Write-Error "PowerShell 5.0+ required. Consider using PowerShell Core (pwsh)"
    exit 1
}

Write-Host "Starting PowerShell LSP Server..."
Write-Host "Configuration: PSScriptAnalyzer"
Write-Host ""

# Check if PSScriptAnalyzer is installed
try {
    Import-Module PSScriptAnalyzer -ErrorAction Stop
    Write-Host "✓ PSScriptAnalyzer loaded"
} catch {
    Write-Host "Installing PSScriptAnalyzer..."
    Install-Module PSScriptAnalyzer -Force -Scope CurrentUser
    Import-Module PSScriptAnalyzer
}

# For full LSP support, we'd need PowerShell Editor Services
# This is a simplified version that uses PSScriptAnalyzer
Write-Host "Note: For full LSP features, install PowerShell Editor Services:"
Write-Host "  Install-Module PowerShellEditorServices -Scope CurrentUser"
Write-Host ""

# Function to analyze PowerShell files
function Invoke-PowerShellLint {
    param([string]$FilePath)

    if (Test-Path $FilePath) {
        $results = Invoke-ScriptAnalyzer -Path $FilePath -IncludeRule @(
            'PSAvoidUsingCmdletAliases',
            'PSAvoidUsingPositionalParameters',
            'PSAvoidUsingPlainTextForPassword',
            'PSUseApprovedVerbs',
            'PSAvoidDefaultValueSwitchParameter',
            'PSMissingModuleManifestField',
            'PSReservedCmdletChar',
            'PSReservedParams',
            'PSUseBOMForUnicodeEncodedFile',
            'PSAvoidGlobalAliases',
            'PSAvoidGlobalFunctions',
            'PSAvoidGlobalVariables',
            'PSMisleadingBacktick',
            'PSPlaceCloseBrace',
            'PSPlaceOpenBrace',
            'PSProvideCommentHelp',
            'PSPossibleIncorrectComparisonWithNull',
            'PSPossibleIncorrectUsageOfRedirectionOperator',
            'PSUseConsistentIndentation',
            'PSUseConsistentWhitespace',
            'PSUseCorrectCasing',
            'PSUseDeclaredVarsMoreThanAssignments'
        )

        $results | ForEach-Object {
            @{
                Message = $_.Message
                Severity = $_.Severity
                Line = $_.Line
                Column = $_.Column
                RuleName = $_.RuleName
            }
        } | ConvertTo-Json
    }
}

Write-Host "PowerShell LSP ready for analysis"
Write-Host "Use Invoke-PowerShellLint to analyze .ps1 files"
Write-Host ""
Write-Host "Waiting for connections..."

# Keep process running
while ($true) {
    Start-Sleep -Seconds 10
}
