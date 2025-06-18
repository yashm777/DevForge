from tools.os_utils import get_os_type

# Map task to folder
TASK_MODULE_MAP = {
    "install": "installers",
    "uninstall": "uninstallers",
    "update": "upgraders",
    "version": "version_checkers"
}

def handle_request(request: dict) -> dict:
    task = request.get("task")
    tool = request.get("tool")
    version = request.get("version", "latest")

    if not task or not tool:
        return {"status": "error", "message": "Missing task or tool in request."}

    task_folder = TASK_MODULE_MAP.get(task)
    if not task_folder:
        return {"status": "error", "message": f"Unsupported task: {task}"}

    os_type = get_os_type()  # "linux", "mac", "windows"

    try:
        # Dynamically import the correct function based on task + OS
        module_path = f"tools.{task_folder}.{os_type}"
        tool_module = __import__(module_path, fromlist=["handle_tool"])
        result = tool_module.handle_tool(tool, version)

        return {
            "status": "success" if result else "error",
            "message": f"{task.capitalize()} {'completed' if result else 'failed'} for {tool}"
        }

    except ImportError:
        return {"status": "error", "message": f"No handler for {task} on {os_type}."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
