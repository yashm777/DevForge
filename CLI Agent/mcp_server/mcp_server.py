from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import platform
import traceback
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

# Dummy functions and variables to make the example self-contained
def add_log_entry(level, message, extra=None):
    logger.log(level, message, extra=extra)

def perform_git_setup_mac(action, repo_url, branch, username, email, dest_dir):
    return {"status": "success", "action": action}

def perform_git_setup_linux(action, repo_url, branch, username, email, dest_dir):
    return {"status": "success", "action": action}

task_handlers = {
    # Dummy handlers for illustration
    "system_config": lambda tool, action, value: {"status": "success"},
    "uninstall": lambda tool: {"status": "success"},
    "install_by_id": lambda package_id, version: {"status": "success"}
}

def generate_code(description):
    return {"status": "success", "code": "print('Hello, world!')"}

def get_system_info():
    return {"status": "success", "info": "System information"}

def get_server_logs(lines):
    return ["Log line 1", "Log line 2"]

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

            if task == "git_setup":
                action = params.get("action")
                repo_url = params.get("repo_url", "")
                branch = params.get("branch", "")
                username = params.get("username", "")
                email = params.get("email", "")
                dest_dir = params.get("dest_dir", "")
                os_type = platform.system().lower()

                # Minimal input validation
                missing_fields = []
                if not action:
                    missing_fields.append("action")
                if action == "clone" and not repo_url:
                    missing_fields.append("repo_url")
                if action == "switch_branch" and (not dest_dir or not branch):
                    if not dest_dir:
                        missing_fields.append("dest_dir")
                    if not branch:
                        missing_fields.append("branch")
                if action == "generate_ssh_key" and not email:
                    missing_fields.append("email")

                if missing_fields:
                    result = {
                        "status": "error",
                        "action": action,
                        "message": f"Missing required fields: {', '.join(missing_fields)}"
                    }
                else:
                    try:
                        if os_type == "darwin":
                            git_result = perform_git_setup_mac(
                                action=action,
                                repo_url=repo_url,
                                branch=branch,
                                username=username,
                                email=email,
                                dest_dir=dest_dir
                            )
                        elif os_type == "linux":
                            git_result = perform_git_setup_linux(
                                action=action,
                                repo_url=repo_url,
                                branch=branch,
                                username=username,
                                email=email,
                                dest_dir=dest_dir
                            )
                        else:
                            git_result = {"status": "error", "message": f"Git setup is not supported on OS: {os_type}"}

                        result = {
                            "status": "error" if git_result.get("status") == "error" else "success",
                            "action": action,
                            "details": git_result
                        }
                        add_log_entry("INFO", f"Git setup action '{action}' result: {result['status']}", {"action": action, "details": git_result})
                    except Exception as e:
                        result = {
                            "status": "error",
                            "action": action,
                            "message": str(e)
                        }
                        add_log_entry("ERROR", f"Git setup action '{action}' failed: {str(e)}", {"action": action})

            else:
                tool = params.get("tool_name")
                version = params.get("version", "latest")
                handler = task_handlers.get(task)

                if handler:
                    if task == "system_config":
                        action = params.get("action", "check")
                        value = params.get("value", None)
                        result = handler(tool, action, value)
                    elif task == "uninstall":
                        result = handler(tool)
                    elif task == "install_by_id":
                        package_id = params.get("package_id")
                        result = handler(package_id, version)
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
        error_msg = f"Exception in mcp_endpoint: {e}"
        add_log_entry("ERROR", error_msg, {"traceback": traceback.format_exc()})
        logger.error(f"Exception in mcp_endpoint: {e}\n{traceback.format_exc()}")

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
