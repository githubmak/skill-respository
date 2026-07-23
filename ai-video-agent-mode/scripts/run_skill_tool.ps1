<#
.SYNOPSIS
Runs one AI Video Agent Mode Python tool without PowerShell command-string parsing.

.DESCRIPTION
Only a script path and already-tokenized arguments are accepted.  Do not pass
JSON, Markdown, prompts, or here-strings: write those to files and pass paths.
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
