import shutil
import subprocess
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_executable(tool_name: str) -> str:
    """
    Find the full path of an executable, checking aliases and common locations.
    """
    tool_aliases = {
        "python": ["python3", "python"],
        "pip": ["pip3", "pip"],
        "node": ["node", "nodejs"],
        "java": ["java", "jdk"],
    }
    
    possible_names = tool_aliases.get(tool_name, [tool_name])
    
    for name in possible_names:
        executable_path = shutil.which(name)
        if executable_path:
            return executable_path
            
    common_paths = [
        "/usr/local/bin",
        "/opt/homebrew/bin",
        os.path.expanduser("~/.local/bin")
    ]
    
    for path in common_paths:
        for name in possible_names:
            full_path = os.path.join(path, name)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                return full_path
                
    return None

import shutil
import subprocess
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_executable(tool_name: str) -> str:
    """
    Find the full path of an executable, checking aliases and common locations.
    """
    tool_aliases = {
        "python": ["python3", "python"],
        "pip": ["pip3", "pip"],
        "node": ["node", "nodejs"],
        "java": ["java", "jdk"],
    }
    
    possible_names = tool_aliases.get(tool_name, [tool_name])
    
    for name in possible_names:
        executable_path = shutil.which(name)
        if executable_path:
            return executable_path
            
    common_paths = [
        "/usr/local/bin",
        "/opt/homebrew/bin",
        os.path.expanduser("~/.local/bin")
    ]
    
    for path in common_paths:
        for name in possible_names:
            full_path = os.path.join(path, name)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                return full_path
                
    return None

def check_version(tool_name: str, version: str = "latest") -> dict:
    """
    Check the version of a tool on macOS, with dynamic fallback for Python modules.
    """
    # First, try to find the tool as a standard executable
    executable_path = find_executable(tool_name)
    if executable_path:
        try:
            version_commands = [
                [executable_path, "--version"],
                [executable_path, "-v"],
                [executable_path, "-V"],
                [executable_path, "version"]
            ]
            for cmd in version_commands:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
                if result.stdout.strip():
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name}",
                        "version": result.stdout.strip(),
                        "command": " ".join(cmd)
                    }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            # If executable found but version commands fail, proceed to other methods
            pass

    # If not found or version check failed, try running as a Python module
    for py_exec in ["python3", "python"]:
        if shutil.which(py_exec):
            try:
                # Use the tool name directly as the module name
                cmd = [py_exec, "-m", tool_name, "--version"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
                if result.stdout.strip():
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name} (via Python module)",
                        "version": result.stdout.strip(),
                        "command": " ".join(cmd),
                    }
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                # For 'idle', the module is 'idlelib'
                if tool_name == "idle":
                    try:
                        cmd = [py_exec, "-m", "idlelib", "--version"]
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
                        if result.stdout.strip():
                           return {
                               "status": "success",
                               "message": f"Version information for {tool_name} (via Python module)",
                               "version": result.stdout.strip(),
                               "command": " ".join(cmd),
                           }
                    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                        continue
                else:
                    continue

    # If still not found, try Homebrew
    if shutil.which("brew"):
        try:
            brew_cmd = ["brew", "list", "--versions", tool_name]
            result = subprocess.run(brew_cmd, capture_output=True, text=True, timeout=10, check=True)
            if result.stdout.strip():
                return {
                    "status": "success",
                    "message": f"Version information for {tool_name} (Homebrew)",
                    "version": result.stdout.strip(),
                    "source": "homebrew"
                }
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pass

    return {
        "status": "error",
        "message": f"{tool_name} is not installed, not in PATH, or its version could not be determined."
    }

# Legacy function for backward compatibility
def version_tool_mac(tool_name: str, version: str = "latest") -> dict:
    return check_version(tool_name, version)

# Legacy function for backward compatibility
def version_tool_mac(tool_name: str, version: str = "latest") -> dict:
    return check_version(tool_name, version) 