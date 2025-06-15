# tool_installer.py - Handles installing, uninstalling, updating, and checking version of tools.

import subprocess
import shutil
from .os_utils import is_linux, is_mac, is_windows
from .constants import ToolMessages

def run_command(command_list, shell=False):
    try:
        subprocess.run(command_list, check=True, shell=shell)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False

# INSTALL TOOL
def install_tool(tool_name, version="latest"):
    if is_linux():
        if shutil.which("apt") is None:
            return ToolMessages.UNSUPPORTED_OS
        if tool_name == "docker":
            success = (
                run_command(["sudo", "apt", "update"]) and
                run_command(["sudo", "apt", "install", "-y", "docker.io"])
            )
        elif tool_name == "nodejs":
            success = run_command(["sudo", "apt", "install", "-y", "nodejs"])
        else:
            return f"{tool_name} is not supported on Linux."
    
    elif is_mac():
        if shutil.which("brew") is None:
            return "Homebrew not found. Please install Homebrew first."
        if tool_name == "docker":
            success = run_command(["brew", "install", "--cask", "docker"])
        elif tool_name == "nodejs":
            success = run_command(["brew", "install", "node"])
        else:
            return f"{tool_name} is not supported on macOS."
    
    elif is_windows():
        if tool_name == "docker":
            return "Please install Docker Desktop manually on Windows."
        elif tool_name == "nodejs":
            if shutil.which("choco") is None:
                return "Chocolatey not found. Please install Chocolatey first."
            success = run_command(["choco", "install", "-y", "nodejs"], shell=True)
        else:
            return f"{tool_name} is not supported on Windows."
    
    else:
        return ToolMessages.UNSUPPORTED_OS

    return (
        ToolMessages.INSTALL_SUCCESS.format(tool=tool_name)
        if success else ToolMessages.INSTALL_FAILED.format(tool=tool_name)
    )

# Placeholder for other tasks
def uninstall_tool(tool_name):
    return f"Uninstall logic for {tool_name} not implemented yet."

def update_tool(tool_name):
    return f"Update logic for {tool_name} not implemented yet."

def tool_version(tool_name):
    return f"Version check logic for {tool_name} not implemented yet."

# Task Dispatcher
def handle_request(request):
    task = request.get("task")
    tool = request.get("tool")

    if not tool:
        return {"status": "error", "message": ToolMessages.MISSING_TOOL}
    
    if task == "install":
        result = install_tool(tool)
    elif task == "uninstall":
        result = uninstall_tool(tool)
    elif task == "update":
        result = update_tool(tool)
    elif task == "version":
        result = tool_version(tool)
    else:
        return {"status": "error", "message": ToolMessages.UNSUPPORTED_TASK.format(task=task)}

    status = "success" if "successfully" in result.lower() else "error"
    return {"status": status, "message": result}
