@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>&1
if errorlevel 1 (
    echo uv is required. Install uv, then run this launcher again.
    exit /b 1
)
call uv run groundmark %*
exit /b %errorlevel%
