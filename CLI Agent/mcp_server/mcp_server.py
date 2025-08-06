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
from tools.uninstallers.linux import uninstall_linux_tool
from tools.version_checkers.mac import check_version_mac_tool
from tools.uninstallers.linux import uninstall_linux_tool
from tools.version_checkers.windows import check_version as check_version_windows
from tools.version_checkers.linux import check_version as check_version_linux
from tools.upgraders.mac import upgrade_mac_tool
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
        result = uninstall_linux_tool(tool)
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
        result = check_version_mac_tool(tool, version)
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
        result = upgrade_mac_tool(tool, version)
    elif os_type == "linux":
        result = handle_tool(tool, version)
    else:
        result = {"status": "error", "message": f"Unsupported OS: {os_type}"}
    
    add_log_entry("INFO", f"Upgrade result for {tool}: {result.get('status', 'unknown')}")
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

def handle_system_config(tool, action="check", value=None):
    os_type = platform.system().lower()
    if os_type == "windows":
        from tools.system_config import windows as sys_tool
    elif os_type == "linux":
        from tools.system_config import linux as sys_tool
    else:
        return {"status": "error", "message": f"System config tools not implemented for {os_type}"}

    if action == "check":
        return sys_tool.check_env_variable(tool)
    elif action == "set":
        return sys_tool.set_env_variable(tool, value)
    elif action == "append_to_path":
        return sys_tool.append_to_path(tool)
    elif action == "remove_from_path":
        return sys_tool.remove_from_path(tool)
    elif action == "is_port_open":
        try:
            return sys_tool.is_port_open(int(tool))
        except ValueError:
            return {"status": "error", "message": "Port must be an integer"}
    elif action == "is_service_running":
        return sys_tool.is_service_running(tool)
    elif action == "remove_env":
        return sys_tool.remove_env_variable(tool)
    elif action == "list_env":
        return sys_tool.list_env_variables()
    else:
        return {"status": "error", "message": f"Unknown system_config action: {action}"}


# Add this function to handle git_setup
def handle_git_setup(action, repo_url="", branch="", username="", email="", dest_dir=""):
    os_type = platform.system().lower()
    if os_type == "linux":
        try:
            from tools.git_configurator.linux import perform_git_setup
            return perform_git_setup(
                action=action,
                repo_url=repo_url,
                branch=branch,
                username=username,
                email=email,
                dest_dir=dest_dir
            )
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        return {"status": "error", "message": f"Git setup is not supported on OS: {os_type}"}

# Task dispatch dictionary
task_handlers = {
    "install": install_tool,
    "install_by_id": install_tool_by_id,
    "uninstall": uninstall_tool,
    "update": upgrade_tool,
    "upgrade": upgrade_tool,
    "version": check_version,
    "system_config": handle_system_config,
    "git_setup": handle_git_setup,
}

@app.post("/mcp/")
async def mcp_endpoint(request: Request):
    try:
        req = await request.json()
        add_log_entry("INFO", f"Incoming MCP request: {req.get('method', 'unknown')}", {"request": req})

        method = req.get("method")
        params = req.get("params", {})
        id_ = req.get("id")

        logger.info(f"Method: {method}, Params: {params}")

        result = None
        if method == "tool_action_wrapper":
            task = params.get("task")
            version = params.get("version", "latest")
            handler = task_handlers.get(task)
            
            if handler:
                if task == "git_setup":
                    action = params.get("action")
                    repo_url = params.get("repo_url", "")
                    branch = params.get("branch", "")
                    username = params.get("username", "")
                    email = params.get("email", "")
                    dest_dir = params.get("dest_dir", "")
                    result = handler(action, repo_url, branch, username, email, dest_dir)
                elif task == "system_config":
                    tool = params.get("tool_name")
                    action = params.get("action", "check")
                    value = params.get("value", None)
                    result = handler(tool, action, value)
                elif task == "uninstall":
                    result = handler(tool)
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