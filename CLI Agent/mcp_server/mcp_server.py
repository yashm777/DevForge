# --- File: mcpserver.py ---
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import platform
import os
import subprocess
import logging
import time
from datetime import datetime
from collections import deque
from tools.code_generator import generate_code
from tools.installers.mac import install_mac_tool
from tools.installers.windows import install_windows_tool, install_windows_tool_by_id
from tools.installers.linux import install_linux_tool
from tools.uninstallers.mac import uninstall_mac_tool
from tools.uninstallers.windows import uninstall_windows_tool
from tools.uninstallers.linux import uninstall_tool_linux
from tools.version_checkers.mac import check_version_mac_tool as check_version_mac
from tools.version_checkers.windows import check_version as check_version_windows
from tools.version_checkers.linux import check_version as check_version_linux
from tools.upgraders.mac import upgrade_mac_tool as handle_tool_mac, downgrade_mac_tool
from tools.upgraders.windows import handle_tool
from tools.upgraders.linux import handle_tool
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# In-memory log storage
server_logs = deque(maxlen=1000)  # Keep last 1000 log entries

def add_log_entry(level: str, message: str, details: dict = None):
    """Add a log entry to the in-memory log storage"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message,
        "details": details or {}
    }
    server_logs.append(log_entry)
    # Also log to console for debugging
    logger.info(f"[{timestamp}] {level.upper()}: {message}")

app = FastAPI()

# --- Dispatcher Functions ---
def install_tool(tool, version="latest"):
    add_log_entry("INFO", f"Install request for tool: {tool} (version: {version})")
    os_type = platform.system().lower()
    if os_type == "windows":
        result = install_windows_tool(tool, version)
    elif os_type == "darwin":
        result = install_mac_tool(tool, version)
    elif os_type == "linux":
        result = install_linux_tool(tool,version)
    else:
        result = {"status": "error", "message": f"Unsupported OS: {os_type}"}
    
    add_log_entry("INFO", f"Install result for {tool}: {result.get('status', 'unknown')}")
    return result

def install_tool_by_id(package_id, version="latest"):
    """Install a specific package by its ID"""
    add_log_entry("INFO", f"Install by ID request for package: {package_id} (version: {version})")
    os_type = platform.system().lower()
    if os_type == "windows":
        result = install_windows_tool_by_id(package_id, version)
    elif os_type == "darwin":
        result = install_mac_tool(package_id, version)  # Mac doesn't have by_id function yet
    elif os_type == "linux":
        result = install_linux_tool(package_id,version)  # Linux doesn't have by_id function yet
    else:
        result = {"status": "error", "message": f"Unsupported OS: {os_type}"}
    
    add_log_entry("INFO", f"Install by ID result for {package_id}: {result.get('status', 'unknown')}")
    return result

def uninstall_tool(tool):
    add_log_entry("INFO", f"Uninstall request for tool: {tool}")
    os_type = platform.system().lower()
    if os_type == "windows":
        result = uninstall_windows_tool(tool)
    elif os_type == "darwin":
        result = uninstall_mac_tool(tool)
    elif os_type == "linux":
        result = uninstall_tool_linux(tool)
    else:
        result = {"status": "error", "message": f"Unsupported OS: {os_type}"}
    
    add_log_entry("INFO", f"Uninstall result for {tool}: {result.get('status', 'unknown')}")
    return result

def check_version(tool, version="latest"):
    add_log_entry("INFO", f"Version check request for tool: {tool}")
    os_type = platform.system().lower()
    if os_type == "windows":
        result = check_version_windows(tool, version)
    elif os_type == "darwin":
        result = check_version_mac(tool)  # Only pass tool, not version
    elif os_type == "linux":
        result = check_version_linux(tool, version)
    else:
        result = {"status": "error", "message": f"Unsupported OS: {os_type}"}
    
    add_log_entry("INFO", f"Version check result for {tool}: {result.get('status', 'unknown')}")
    return result

def upgrade_tool(tool, version="latest"):
    add_log_entry("INFO", f"Upgrade request for tool: {tool} (version: {version})")
    os_type = platform.system().lower()
    if os_type == "windows":
        result = handle_tool(tool, version)
    elif os_type == "darwin":
        result = handle_tool_mac(tool, version)
    elif os_type == "linux":
        result = handle_tool(tool, version)
    else:
        result = {"status": "error", "message": f"Unsupported OS: {os_type}"}
    
    add_log_entry("INFO", f"Upgrade result for {tool}: {result.get('status', 'unknown')}")
    return result

def downgrade_tool(tool, version="latest"):
    add_log_entry("INFO", f"Downgrade request for tool: {tool} (version: {version})")
    os_type = platform.system().lower()
    if os_type == "darwin":
        # Use Mac-specific downgrade function
        result = downgrade_mac_tool(tool, version)
    elif os_type == "windows":
        # For now, use upgrade function with different messaging
        result = handle_tool(tool, version)
        if result["status"] == "success":
            result["message"] = result["message"].replace("upgraded", "switched to")
    elif os_type == "linux":
        # For now, use upgrade function with different messaging  
        result = handle_tool(tool, version)
        if result["status"] == "success":
            result["message"] = result["message"].replace("upgraded", "switched to")
    else:
        result = {"status": "error", "message": f"Unsupported OS: {os_type}"}
    
    add_log_entry("INFO", f"Downgrade result for {tool}: {result.get('status', 'unknown')}")
    return result

def get_system_info():
    add_log_entry("INFO", "System info request")
    result = {
        "os_type": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "user": os.getenv("USERNAME") or os.getenv("USER") or "unknown"
    }
    add_log_entry("INFO", "System info provided")
    return result

def get_server_logs(lines: int = 50):
    """Get the last N log entries"""
    return list(server_logs)[-lines:]

# Task dispatch dictionary
task_handlers = {
    "install": install_tool,
    "install_by_id": install_tool_by_id,
    "uninstall": uninstall_tool,
    "update": upgrade_tool,
    "upgrade": upgrade_tool,
    "downgrade": downgrade_tool,
    "version": check_version,
}

@app.post("/mcp/")
async def mcp_endpoint(request: Request):
    try:
        req = await request.json()
        add_log_entry("INFO", f"Incoming MCP request: {req.get('method', 'unknown')}", {"request": req})

        method = req.get("method")
        params = req.get("params", {})
        id_ = req.get("id")

        result = None
        if method == "tool_action_wrapper":
            task = params.get("task")
            tool = params.get("tool_name")
            version = params.get("version", "latest")

            handler = task_handlers.get(task)
            if handler:
                # uninstall_tool expects only tool param, others also get version
                if task == "uninstall":
                    result = handler(tool)
                elif method == "generate_code":
                    description = params.get("description")
                    result = generate_code(description)
                else:
                    result = handler(tool, version)
            else:
                result = {"status": "error", "message": f"Unknown task: {task}"}

        elif method == "generate_code":
            description = params.get("description")
            result = generate_code(description)

        elif method == "info://server":
            result = get_system_info()

        elif method == "get_logs":
            lines = params.get("lines", 50)
            result = {"logs": get_server_logs(lines)}

        else:
            result = {"status": "error", "message": f"Unknown method: {method}"}

        add_log_entry("INFO", f"MCP response for {method}: {result.get('status', 'success')}")
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": id_,
                "result": result
            },
            media_type="application/json"
        )
    except Exception as e:
        # Log the full traceback for debugging
        error_msg = f"Exception in mcp_endpoint: {e}"
        add_log_entry("ERROR", error_msg, {"traceback": traceback.format_exc()})
        logger.error(f"Exception in mcp_endpoint: {e}\n{traceback.format_exc()}")

        # Return a JSON error response
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": 500,
                    "message": f"Internal Server Error: {str(e)}"
                }
            },
            media_type="application/json"
        )

def main():
    """Main entry point for the MCP server."""
    import argparse
    parser = argparse.ArgumentParser(description="Start the MCP server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    add_log_entry("INFO", f"Starting MCP server on {args.host}:{args.port}")
    logger.info(f"Starting MCP server on {args.host}:{args.port}")
    uvicorn.run("mcp_server.mcp_server:app", host=args.host, port=args.port, reload=False)

if __name__ == "__main__":
    main()
