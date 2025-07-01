# --- File: mcpserver.py ---
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import platform
import os
import subprocess
import logging
from tools.code_generator import generate_code
from tools.installers.mac import install_mac_tool
from tools.installers.windows import install_windows_tool
from tools.installers.linux import install_linux_tool
from tools.uninstallers.mac import uninstall_mac_tool
from tools.uninstallers.windows import uninstall_windows_tool
from tools.uninstallers.linux import uninstall_linux_tool
from tools.version_checkers.mac import check_version as check_version_mac
from tools.version_checkers.windows import check_version as check_version_windows
from tools.version_checkers.linux import check_version as check_version_linux
from tools.upgraders.mac import handle_tool
from tools.upgraders.windows import handle_tool
from tools.upgraders.linux import handle_tool
import traceback



# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# --- Dispatcher Functions ---
def install_tool(tool, version="latest"):
    os_type = platform.system().lower()
    if os_type == "windows":
        return install_windows_tool(tool, version)
    elif os_type == "darwin":
        return install_mac_tool(tool, version)
    elif os_type == "linux":
        return install_linux_tool(tool)
    else:
        return {"status": "error", "message": f"Unsupported OS: {os_type}"}

def uninstall_tool(tool):
    os_type = platform.system().lower()
    if os_type == "windows":
        return uninstall_windows_tool(tool)
    elif os_type == "darwin":
        return uninstall_mac_tool(tool)
    elif os_type == "linux":
        return uninstall_linux_tool(tool)
    else:
        return {"status": "error", "message": f"Unsupported OS: {os_type}"}

def check_version(tool):
    os_type = platform.system().lower()
    if os_type == "windows":
        return check_version_windows(tool)
    elif os_type == "darwin":
        return check_version_mac(tool)
    elif os_type == "linux":
        return check_version_linux(tool)
    else:
        return {"status": "error", "message": f"Unsupported OS: {os_type}"}

def upgrade_tool(tool, version="latest"):
    os_type = platform.system().lower()
    if os_type == "windows":
        return handle_tool(tool, version)
    elif os_type == "darwin":
        return handle_tool(tool, version)
    elif os_type == "linux":
        return handle_tool(tool, version)
    else:
        return {"status": "error", "message": f"Unsupported OS: {os_type}"}

def get_system_info():
    return {
        "os_type": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "user": os.getenv("USERNAME") or os.getenv("USER") or "unknown"
    }


# Task dispatch dictionary
task_handlers = {
    "install": install_tool,
    "uninstall": uninstall_tool,
    "update": upgrade_tool,
    "upgrade": upgrade_tool,
    "version": check_version,
}


@app.post("/mcp/")
async def mcp_endpoint(request: Request):
    try:
        req = await request.json()
        logger.info(f"Incoming MCP request: {req}")

        method = req.get("method")
        params = req.get("params", {})
        id_ = req.get("id")

        logger.info(f"Method: {method}, Params: {params}")

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

        else:
            result = {"status": "error", "message": f"Unknown method: {method}"}

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

    logger.info(f"Starting MCP server on {args.host}:{args.port}")
    uvicorn.run("mcp_server.mcp_server:app", host=args.host, port=args.port, reload=False)


if __name__ == "__main__":
    main()
