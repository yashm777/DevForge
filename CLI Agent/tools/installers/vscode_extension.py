import subprocess
import sys
import os
import time
import shutil

def _run_vscode_command(command):
    """
    Runs a VSCode command with the necessary environment to force CLI mode.
    This prevents the GUI from opening unexpectedly.
    """
    # Create a copy of the current environment and add VSCODE_CLI=1
    # This is the official way to force the 'code' executable into CLI mode.
    cli_env = os.environ.copy()
    cli_env["VSCODE_CLI"] = "1"

    # On non-Windows systems, we pass the modified environment.
    # On Windows, this is not typically necessary, but it doesn't hurt.
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        env=cli_env
    )

def find_vscode_executable():
    """Find the path to the VSCode executable, prioritizing official locations over PATH."""
    if sys.platform == "win32":
        user_profile = os.path.expanduser("~")
        common_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft VS Code", "bin", "code.cmd"),
            os.path.join(user_profile, "AppData", "Local", "Programs", "Microsoft VS Code", "bin", "code.cmd")
        ]
        for path in common_paths:
            if os.path.exists(path):
                try:
                    _run_vscode_command([path, "--version"])
                    return path
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
    elif sys.platform.startswith("linux"):
        # Check standard path first
        if shutil.which("code"):
            try:
                _run_vscode_command(["code", "--version"])
                return "code"
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass
        # Check for snap path as a fallback
        snap_path = "/snap/bin/code"
        if os.path.exists(snap_path):
             try:
                _run_vscode_command([snap_path, "--version"])
                return snap_path
             except (FileNotFoundError, subprocess.CalledProcessError):
                pass
    
    # General fallback for any system (e.g., macOS or other Linux setups)
    if shutil.which("code"):
        return "code"

    return None

def is_vscode_installed():
    """Check if VSCode is installed."""
    return find_vscode_executable() is not None

def get_installed_extensions():
    """Get a list of installed VSCode extensions."""
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return set()
    
    try:
        command = [vscode_executable, "--list-extensions"]
        result = _run_vscode_command(command)
        extensions = result.stdout.strip().split('\n')
        return set(ext.lower() for ext in extensions if ext) # Use lowercase for consistent matching
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()

def install_extension(extension_id):
    """Install a VSCode extension and verify its installation."""
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode is not installed or could not be found."}

    # Normalize extension ID to lowercase for comparison
    normalized_extension_id = extension_id.lower()

    if normalized_extension_id in get_installed_extensions():
        return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}

    print(f"Attempting to install '{extension_id}'...")

    try:
        install_command = [vscode_executable, "--install-extension", extension_id]
        _run_vscode_command(install_command)
        
        # Retry mechanism for verification
        for _ in range(3):
            time.sleep(2)  # A short delay is still helpful
            if normalized_extension_id in get_installed_extensions():
                return {"status": "Success", "message": f"Extension '{extension_id}' installed and verified successfully."}

        return {"status": "Error", "message": f"Installation of '{extension_id}' failed verification."}

    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip() if e.stderr else e.stdout.strip()
        return {"status": "Error", "message": f"Failed to install extension '{extension_id}'. Error: {error_message}"}
    except FileNotFoundError:
        return {"status": "Error", "message": "The 'code' command is not available."}

def uninstall_extension(extension_id):
    """Uninstall a VSCode extension and verify its removal."""
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode is not installed or could not be found."}

    normalized_extension_id = extension_id.lower()

    if normalized_extension_id not in get_installed_extensions():
        return {"status": "Success", "message": f"Extension '{extension_id}' is not installed."}

    print(f"Attempting to uninstall '{extension_id}'...")

    try:
        uninstall_command = [vscode_executable, "--uninstall-extension", extension_id]
        _run_vscode_command(uninstall_command)
        
        # Retry mechanism for verification
        for _ in range(3):
            time.sleep(2)
            if normalized_extension_id not in get_installed_extensions():
                return {"status": "Success", "message": f"Extension '{extension_id}' uninstalled and verified successfully."}

        return {"status": "Error", "message": f"Uninstallation of '{extension_id}' failed verification."}

    except subprocess.CalledProcessError as e:
        error_message = e.stderr.strip() if e.stderr else e.stdout.strip()
        return {"status": "Error", "message": f"Failed to uninstall extension '{extension_id}'. Error: {error_message}"}
    except FileNotFoundError:
        return {"status": "Error", "message": "The 'code' command is not available."}

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
        
    print(result["message"])
    if result["status"] == "Error":
        sys.exit(1)