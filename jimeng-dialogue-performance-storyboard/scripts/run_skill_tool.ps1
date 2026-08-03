<#
.SYNOPSIS
Runs one Jimeng storyboard Python tool without PowerShell command-string parsing.

.DESCRIPTION
Only a script path and already-tokenized arguments are accepted. Write JSON,
Markdown, prompts, and multiline text to files, then pass their paths.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$ScriptPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ToolArguments
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ScriptPath -PathType Leaf)) {
    throw "Python tool not found: $ScriptPath"
}

$py = Get-Command py -ErrorAction SilentlyContinue
if ($null -ne $py) {
    & $py.Source '-3' $ScriptPath @ToolArguments
} else {
    $python = Get-Command python3 -ErrorAction SilentlyContinue
    if ($null -eq $python) {
        $python = Get-Command python -ErrorAction SilentlyContinue
    }
    if ($null -eq $python) {
        throw 'Python 3 was not found. Install Python 3 or make the py launcher available.'
    }
    & $python.Source $ScriptPath @ToolArguments
}

exit $LASTEXITCODE
