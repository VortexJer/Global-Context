# Global Context CLI wrapper for PowerShell
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& python3 "$scriptDir\globalcontext.py" @args
