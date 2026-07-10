@echo off
rem Global Context CLI wrapper for Windows Command Prompt
setlocal
set "SCRIPT_DIR=%~dp0"
python3 "%SCRIPT_DIR%globalcontext.py" %*
