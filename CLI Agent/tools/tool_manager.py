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

    os_type = get_os_type()
    
    # Map OS types to module names
    os_module_map = {
        "darwin": "mac",      # macOS detection maps to mac.py module
        "linux": "linux"     
    }
    
    module_os = os_module_map.get(os_type, os_type)

    try:
        # Dynamically build the module path (OS mapping handled elsewhere)
        module_path = f"tools.{task_folder}.{module_os}"
        # Import the correct tool module (e.g., tools.installers.mac)
        tool_module = __import__(module_path, fromlist=["handle_tool"])

        # Prefer standard handle_tool() if it exists (recommended for all new code)
        if hasattr(tool_module, "handle_tool"):
            result = tool_module.handle_tool(tool, version)
        # If not, check for a specific function like install_tool_mac(), uninstall_tool_linux(), etc.
        elif hasattr(tool_module, f"{task}_tool_{module_os}"):
            func = getattr(tool_module, f"{task}_tool_{module_os}")
            result = func(tool, version)
        else:
            # If neither function exists, return a clear error for debugging
            return {"status": "error", "message": f"No handler function found in {module_path}"}

        # Standardize return value: 
        # If already a dict (modern format), return as is
        if isinstance(result, dict):
            return result
        else:
            # If not (e.g., True/False), convert to dict for consistency
            return {
                "status": "success" if result else "error",
                "message": f"{task.capitalize()} {'completed' if result else 'failed'} for {tool}"
            }

    # Handle cases where the correct installer module doesn't exist
    except ImportError:
        return {"status": "error", "message": f"No handler for {task} on {os_type}."}
    # Handle all other unexpected errors gracefully
    except Exception as e:
        return {"status": "error", "message": str(e)}
