# Global Context CLI wrapper for PowerShell
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script = Join-Path $scriptDir 'globalcontext.py'

# Pick an available Python launcher: py -3, then python, then python3.
if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $script @args
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $script @args
} else {
    & python3 $script @args
}
