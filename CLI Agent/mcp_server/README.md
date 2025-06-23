# MCP Server

Model Context Protocol server for development tool management.

## Quick Setup (Recommended)

**Run the setup script first from the project root:**

**Windows**: Run `setup.bat`  
**macOS/Linux**: Run `bash setup.sh`

These scripts will automatically:
- ✅ Check if Python, Git, and UV are installed
- ✅ Install UV package manager if missing
- ✅ Install all project dependencies
- ✅ Provide instructions to start the server

## Manual Setup

If you prefer manual setup, ensure you have:

1. **Python 3.8+** - Download from [python.org](https://python.org/downloads/)
2. **UV Package Manager** - Install with: `pip install uv`
3. **Project Dependencies** - Install with: `uv sync` (from project root)

## How to Run

From the project root directory:

```bash
uv run python -m mcp_server.mcp_server --host localhost --port 8000
```

The server will start and display:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8000 (Press CTRL+C to quit)
```

**Note**: If you haven't run the setup script yet, go back to the project root and run:
- **Windows**: `setup.bat`
- **macOS/Linux**: `bash setup.sh`
