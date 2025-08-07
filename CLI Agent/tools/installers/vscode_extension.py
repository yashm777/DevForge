import subprocess
import sys
import os
import time
import shutil

def _run_vscode_command(command):
    """
    Runs a VSCode command with the necessary environment to force CLI mode
    and handles command execution.
    """
    cli_env = os.environ.copy()
    cli_env["VSCODE_CLI"] = "1"
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            env=cli_env,
            timeout=120  # Add a timeout for safety
        )
        return result
    except FileNotFoundError:
        return None
    except Exception as e:
        # Catch other potential exceptions like timeout
        return subprocess.CompletedProcess(command, 1, stdout="", stderr=str(e))


def find_vscode_executable():
    """Find the path to the VSCode executable in a more robust way."""
    for name in ["code", "code-insiders"]:
        if sys.platform == "win32":
            # In Windows, `code.cmd` is usually in the PATH
            if shutil.which(name):
                return name
        else:
            # In Linux/macOS, check common paths
            for path in ["/usr/bin", "/usr/local/bin", "/snap/bin"]:
                if os.path.exists(os.path.join(path, name)):
                    return os.path.join(path, name)
            # Fallback to PATH
            if shutil.which(name):
                return name
    return None

def is_vscode_installed():
    """Check if VSCode is installed."""
    return find_vscode_executable() is not None

def get_installed_extensions(vscode_executable):
    """Get a set of installed VSCode extensions."""
    if not vscode_executable:
        return set()
    
    command = [vscode_executable, "--list-extensions"]
    result = _run_vscode_command(command)
    
    if result and result.returncode == 0:
        extensions = result.stdout.strip().lower().split('\n')
        return set(ext for ext in extensions if ext)
    return set()

def install_extension(extension_id):
    """Install a VSCode extension with robust verification."""
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode executable not found."}

    normalized_id = extension_id.lower()
    
    # Initial check to see if it's already installed
    installed_extensions = get_installed_extensions(vscode_executable)
    if normalized_id in installed_extensions:
        return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}

    print(f"Attempting to install '{extension_id}'...")
    
    command = [vscode_executable, "--install-extension", extension_id]
    result = _run_vscode_command(command)

    # Primary verification: Check the command output. This is the most reliable method.
    if result and result.returncode == 0:
        stdout_lower = result.stdout.lower()
        if "successfully installed" in stdout_lower:
            return {"status": "Success", "message": f"Extension '{extension_id}' installed successfully."}
        # Handle cases where it might already be installed but our initial check missed it
        if "is already installed" in stdout_lower:
            return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}

    # Secondary verification: If primary failed, check the list again.
    time.sleep(3) # Give VS Code a moment to update its list
    installed_extensions_after = get_installed_extensions(vscode_executable)
    if normalized_id in installed_extensions_after:
        return {"status": "Success", "message": f"Extension '{extension_id}' installed and verified."}

    # If all checks fail, provide a detailed error.
    error_details = result.stderr.strip() if result and result.stderr else "No error output."
    return {"status": "Error", "message": f"Installation of '{extension_id}' failed. Details: {error_details}"}


def uninstall_extension(extension_id):
    """Uninstall a VSCode extension with robust verification."""
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode executable not found."}
        
    normalized_id = extension_id.lower()
    
    if normalized_id not in get_installed_extensions(vscode_executable):
        return {"status": "Success", "message": f"Extension '{extension_id}' is not installed."}

    print(f"Attempting to uninstall '{extension_id}'...")
    
    command = [vscode_executable, "--uninstall-extension", extension_id]
    result = _run_vscode_command(command)

    if result and result.returncode == 0 and "successfully uninstalled" in result.stdout.lower():
        return {"status": "Success", "message": f"Extension '{extension_id}' uninstalled successfully."}

    time.sleep(3)
    if normalized_id not in get_installed_extensions(vscode_executable):
        return {"status": "Success", "message": f"Extension '{extension_id}' uninstalled and verified."}

    error_details = result.stderr.strip() if result and result.stderr else "No error output."
    return {"status": "Error", "message": f"Uninstallation of '{extension_id}' failed. Details: {error_details}"}


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python vscode_extension.py <install|uninstall> <extension_id>")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    extension_id = sys.argv[2]
    
    if action == "install":
        result = install_extension(extension_id)
    elif action == "uninstall":
        result = uninstall_extension(extension_id)
    else:
        print("Invalid action. Use 'install' or 'uninstall'.")
        sys.exit(1)
        
    print(f"Status: {result['status']}\nMessage: {result['message']}")
    if result["status"] == "Error":
        sys.exit(1)