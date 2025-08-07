import subprocess
import sys
import os
import time
import shutil

def find_vscode_executable():
    """Find the path to the VSCode executable, prioritizing official locations over PATH.
    This function is now compatible with Windows and Linux."""
    # 1. Check common locations for Windows first to prioritize official VSCode
    if sys.platform == "win32":
        user_profile = os.path.expanduser("~")
        common_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft VS Code", "bin", "code.cmd"),
            os.path.join(user_profile, "AppData", "Local", "Programs", "Microsoft VS Code", "bin", "code.cmd")
        ]
        for path in common_paths:
            if os.path.exists(path):
                try:
                    subprocess.run([path, "--version"], check=True, capture_output=True, text=True)
                    return path
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
    # 2. Check for linux
    elif sys.platform == "linux":
        # Check if 'code' is in the PATH
        if shutil.which("code"):
            return "code"
        # Check for snap installation
        snap_path = "/snap/bin/code"
        if os.path.exists(snap_path):
            return snap_path

    # 3. Fallback to checking if 'code' is in the PATH for any OS
    try:
        subprocess.run(["code", "--version"], check=True, shell=True, capture_output=True, text=True)
        return "code"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass  # Not in PATH

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
        result = subprocess.run(command, check=True, shell=True, capture_output=True, text=True)
        return set(result.stdout.strip().split('\n'))
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()

def install_extension(extension_id):
    """
    Install a VSCode extension and verify its installation by comparing extension lists.
    
    Args:
        extension_id (str): The ID of the extension to install (e.g., 'ms-python.python').
        
    Returns:
        dict: A dictionary with a status message.
    """
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode is not installed or could not be found."}

    extensions_before = get_installed_extensions()
    
    if any(extension_id.lower() == ext.lower() for ext in extensions_before):
        return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}

    print(f"Attempting to install '{extension_id}'...")

    try:
        install_command = [vscode_executable, "--install-extension", extension_id, "--force"]
        subprocess.run(install_command, check=True, shell=True, capture_output=True, text=True)
        
        # Retry mechanism for verification
        for _ in range(5):  # Retry up to 5 times
            time.sleep(3)  # Wait 3 seconds between retries
            extensions_after = get_installed_extensions()
            newly_installed = extensions_after - extensions_before

            if any(extension_id.lower() == ext.lower() for ext in newly_installed):
                return {"status": "Success", "message": f"Extension '{extension_id}' installed and verified successfully."}
            
            # Also check if it's in the full list, in case it was installed before but not detected
            if any(extension_id.lower() == ext.lower() for ext in extensions_after):
                return {"status": "Success", "message": f"Extension '{extension_id}' is present after installation attempt."}

        return {"status": "Error", "message": f"Installation of '{extension_id}' failed verification."}

    except subprocess.CalledProcessError as e:
        return {"status": "Error", "message": f"Failed to install extension '{extension_id}'. Error: {e.stderr.strip()}"}
    except FileNotFoundError:
        return {"status": "Error", "message": "The 'code' command is not available."}

def uninstall_extension(extension_id):
    """
    Uninstall a VSCode extension and verify its removal by comparing extension lists.
    
    Args:
        extension_id (str): The ID of the extension to uninstall (e.g., 'ms-python.python').
        
    Returns:
        dict: A dictionary with a status message.
    """
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode is not installed or could not be found."}

    extensions_before = get_installed_extensions()
    
    if not any(extension_id.lower() == ext.lower() for ext in extensions_before):
        return {"status": "Success", "message": f"Extension '{extension_id}' is not installed."}

    print(f"Attempting to uninstall '{extension_id}'...")

    try:
        uninstall_command = [vscode_executable, "--uninstall-extension", extension_id]
        subprocess.run(uninstall_command, check=True, shell=True, capture_output=True, text=True)
        
        # Retry mechanism for verification
        for _ in range(5): # Retry up to 5 times
            time.sleep(3) # Wait 3 seconds
            extensions_after = get_installed_extensions()
            if not any(extension_id.lower() == ext.lower() for ext in extensions_after):
                return {"status": "Success", "message": f"Extension '{extension_id}' uninstalled and verified successfully."}

        return {"status": "Error", "message": f"Uninstallation of '{extension_id}' failed verification."}

    except subprocess.CalledProcessError as e:
        return {"status": "Error", "message": f"Failed to uninstall extension '{extension_id}'. Error: {e.stderr.strip()}"}
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