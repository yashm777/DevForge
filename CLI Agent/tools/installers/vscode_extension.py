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
    cli_env = os.environ.copy()
    cli_env["VSCODE_CLI"] = "1"
    
    # We will not use check=True by default so we can inspect the output of failed commands.
    return subprocess.run(
        command,
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
                    result = _run_vscode_command([path, "--version"])
                    if result.returncode == 0:
                        return path
                except FileNotFoundError:
                    continue
    elif sys.platform.startswith("linux"):
        # Check standard path first
        if shutil.which("code"):
            try:
                result = _run_vscode_command(["code", "--version"])
                if result.returncode == 0:
                    return "code"
            except FileNotFoundError:
                pass
        # Check for snap path as a fallback
        snap_path = "/snap/bin/code"
        if os.path.exists(snap_path):
             try:
                result = _run_vscode_command([snap_path, "--version"])
                if result.returncode == 0:
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
        if result.returncode == 0:
            extensions = result.stdout.strip().split('\n')
            return set(ext.lower() for ext in extensions if ext)
    except FileNotFoundError:
        pass
    return set()

def install_extension(extension_id):
    """Install a VSCode extension and verify its installation."""
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode is not installed or could not be found."}

    normalized_extension_id = extension_id.lower()
    if normalized_extension_id in get_installed_extensions():
        return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}

    print(f"Attempting to install '{extension_id}'...")

    try:
        install_command = [vscode_executable, "--install-extension", extension_id]
        result = _run_vscode_command(install_command)

        # Primary Verification: Check the command's output for success message.
        if result.returncode == 0 and "was successfully installed" in result.stdout:
            return {"status": "Success", "message": f"Extension '{extension_id}' installed successfully."}

        # Secondary Verification: If stdout is not conclusive, check the extension list.
        for _ in range(3):
            time.sleep(2)
            if normalized_extension_id in get_installed_extensions():
                return {"status": "Success", "message": f"Extension '{extension_id}' installed and verified."}

        # If both checks fail, report a detailed error.
        error_details = result.stderr.strip() or result.stdout.strip()
        return {"status": "Error", "message": f"Installation of '{extension_id}' failed verification. Details: {error_details}"}

    except Exception as e:
        return {"status": "Error", "message": f"An unexpected error occurred: {str(e)}"}


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
        result = _run_vscode_command(uninstall_command)

        if result.returncode == 0 and "was successfully uninstalled" in result.stdout:
             return {"status": "Success", "message": f"Extension '{extension_id}' uninstalled successfully."}

        for _ in range(3):
            time.sleep(2)
            if normalized_extension_id not in get_installed_extensions():
                return {"status": "Success", "message": f"Extension '{extension_id}' uninstalled and verified."}
        
        error_details = result.stderr.strip() or result.stdout.strip()
        return {"status": "Error", "message": f"Uninstallation of '{extension_id}' failed verification. Details: {error_details}"}

    except Exception as e:
        return {"status": "Error", "message": f"An unexpected error occurred: {str(e)}"}

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