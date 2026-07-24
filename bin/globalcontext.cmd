@echo off
rem Global Context CLI wrapper for Windows Command Prompt
setlocal
set "SCRIPT_DIR=%~dp0"

rem Pick an available Python launcher: py -3, then python, then python3.
set "GC_PY="
where py >nul 2>nul && set "GC_PY=py -3"
if not defined GC_PY (where python >nul 2>nul && set "GC_PY=python")
if not defined GC_PY set "GC_PY=python3"

%GC_PY% "%SCRIPT_DIR%globalcontext.py" %*
