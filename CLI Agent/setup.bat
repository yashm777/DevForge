@echo off
title DevForge CLI Agent Setup
echo.
echo ========================================
echo    DevForge CLI Agent Setup
echo ========================================
echo.

REM Check Python
echo [1/4] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo ❌ Python is not installed
        echo.
        echo Please install Python first:
        echo   ^> Download from: https://python.org/downloads/
        echo   ^> Make sure to check "Add Python to PATH"
        echo.
        pause
        exit /b 1
    ) else (
        echo ✅ Python is available
        set PYTHON_CMD=py
    )
) else (
    echo ✅ Python is available
    set PYTHON_CMD=python
)

REM Check Git
echo [2/4] Checking Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git is not installed
    echo.
    echo Please install Git first:
    echo   ^> Download from: https://git-scm.com/
    echo.
    pause
    exit /b 1
) else (
    echo ✅ Git is available
)

REM Check UV
echo [3/4] Checking UV package manager...
uv --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ UV package manager not found
    echo.
    echo Installing UV...
    %PYTHON_CMD% -m pip install uv
    if %errorlevel% neq 0 (
        echo ❌ Failed to install UV
        echo Please run: %PYTHON_CMD% -m pip install uv
        pause
        exit /b 1
    )
    echo ✅ UV installed successfully
) else (
    echo ✅ UV is available
)

REM Install dependencies
echo [4/4] Installing dependencies...
uv sync
if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo 🎉 Setup complete!
echo.
echo ----------------------------------------
echo  Quick Start Commands:
echo ----------------------------------------
echo.
echo Start the server:
echo   uv run python -m mcp_server.mcp_server
echo.
echo Try the CLI:
echo   uv run cli-agent run "install docker"
echo   uv run cli-agent run "system info"
echo.
echo Set your OpenAI API key:
echo   set OPENAI_API_KEY=your-key-here
echo.
pause
