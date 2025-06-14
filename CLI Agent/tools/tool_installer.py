import subprocess
import platform
import shutil

def run_command(command_list, shell=False):
    """Run a shell command and return True if successful, False otherwise."""
    try:
        subprocess.run(command_list, check=True, shell=shell)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False

def install_tool(tool_name):
    os_type = platform.system().lower()

    if os_type == "linux":
        if shutil.which("apt") is None:
            print("APT package manager not found. Unsupported Linux distribution.")
            return False
        if tool_name == "docker":
            return (
                run_command(["sudo", "apt", "update"]) and
                run_command(["sudo", "apt", "install", "-y", "docker.io"])
            )
        elif tool_name == "nodejs":
            return run_command(["sudo", "apt", "install", "-y", "nodejs"])
        else:
            print(f"Tool '{tool_name}' not supported on Linux.")
            return False

    elif os_type == "darwin":  # macOS
        if shutil.which("brew") is None:
            print("Homebrew not found. Please install Homebrew first.")
            return False
        if tool_name == "docker":
            return run_command(["brew", "install", "--cask", "docker"])
        elif tool_name == "nodejs":
            return run_command(["brew", "install", "node"])
        else:
            print(f"Tool '{tool_name}' not supported on macOS.")
            return False

    elif os_type == "windows":
        if tool_name == "docker":
            print("Please install Docker Desktop manually on Windows.")
            return False
        elif tool_name == "nodejs":
            # Try using Chocolatey to install Node.js
            if shutil.which("choco") is None:
                print("Chocolatey not found. Please install Chocolatey first.")
                return False
            return run_command(["choco", "install", "-y", "nodejs"], shell=True)
        else:
            print(f"Tool '{tool_name}' not supported on Windows.")
            return False

    else:
        print("Unsupported OS.")
        return False

def handle_request(request):
    if request["task"] == "install_tool":
        tool = request.get("tool")
        if tool:
            success = install_tool(tool)
            return {"status": "success" if success else "error", "tool": tool}
        else:
            return {"status": "error", "message": "Missing 'tool' in request."}
    else:
        return {"status": "error", "message": f"Unknown task: {request['task']}"}
