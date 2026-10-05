$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -X utf8 server.py --open @args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 -X utf8 server.py --open @args
} else {
    Write-Host 'Python 3.10+ is required. Install Python and run this script again.'
    exit 1
}
