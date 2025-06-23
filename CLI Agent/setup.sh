#!/bin/bash

echo ""
echo "========================================"
echo "    DevForge CLI Agent Setup"
echo "========================================"
echo ""

# Check Python
echo "[1/4] Checking Python..."
if command -v python3 &> /dev/null; then
    echo "✅ Python3 is available"
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    echo "✅ Python is available"
    PYTHON_CMD="python"
else
    echo "❌ Python is not installed"
    echo ""
    echo "Please install Python first:"
    echo "  > macOS: brew install python"
    echo "  > Linux: sudo apt install python3 python3-pip"
    echo "  > Or download from: https://python.org/downloads/"
    echo ""
    exit 1
fi

# Check Git
echo "[2/4] Checking Git..."
if command -v git &> /dev/null; then
    echo "✅ Git is available"
else
    echo "❌ Git is not installed"
    echo ""
    echo "Please install Git first:"
    echo "  > macOS: brew install git"
    echo "  > Linux: sudo apt install git"
    echo "  > Or download from: https://git-scm.com/"
    echo ""
    exit 1
fi

# Check UV
echo "[3/4] Checking UV package manager..."
if command -v uv &> /dev/null; then
    echo "✅ UV is available"
else
    echo "❌ UV package manager not found"
    echo ""
    echo "Installing UV..."
    $PYTHON_CMD -m pip install uv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install UV"
        echo "Please run: $PYTHON_CMD -m pip install uv"
        exit 1
    fi
    echo "✅ UV installed successfully"
fi

# Install dependencies
echo "[4/4] Installing dependencies..."
uv sync
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "----------------------------------------"
echo "  Quick Start Commands:"
echo "----------------------------------------"
echo ""
echo "Start the server:"
echo "  uv run python -m mcp_server.mcp_server"
echo ""
echo "Try the CLI:"
echo '  uv run cli-agent run "install docker"'
echo '  uv run cli-agent run "system info"'
echo ""
echo "Set your OpenAI API key:"
echo "  export OPENAI_API_KEY=your-key-here"
echo ""
