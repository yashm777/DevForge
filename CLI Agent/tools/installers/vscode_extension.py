import subprocess
import sys
import os
import shutil

def find_vscode_executable():
    """Find the path to the VSCode executable, prioritizing official locations over PATH."""
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

    # 2. Fallback to checking if 'code' is in the PATH
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
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        return set(result.stdout.strip().split('\n'))
    except (FileNotFoundError, subprocess.CalledProcessError):
        return set()

def install_extension(extension_id):
    """
    Install a VSCode extension, with a curl fallback for stubborn Linux environments.
    """
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode is not installed or could not be found."}

    if any(extension_id.lower() == ext.lower() for ext in get_installed_extensions()):
        return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}

    print(f"Attempting standard installation for '{extension_id}'...")
    
    try:
        # --- PRIMARY METHOD: Standard VS Code command ---
        install_command = [vscode_executable, "--install-extension", extension_id]
        subprocess.run(install_command, check=True, capture_output=True, text=True)
        print(f"Standard installation successful for '{extension_id}'.")
        return {"status": "Success", "message": f"Extension '{extension_id}' installed successfully."}
        
    except subprocess.CalledProcessError as e:
        print(f"Standard installation failed: {e.stderr.strip()}. Attempting fallback method...")

        # --- FALLBACK METHOD: Use curl to download and then install from VSIX file ---
        # This part will only run on non-Windows systems if the primary method fails.
        if sys.platform == "win32":
             return {"status": "Error", "message": f"Failed to install '{extension_id}'. Fallback not available for Windows."}

        if not shutil.which("curl"):
            return {"status": "Error", "message": "Fallback failed: 'curl' command not found."}

        publisher, ext_name = extension_id.split('.')
        vsix_url = f"https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{ext_name}/latest/vspackage"
        vsix_path = f"/tmp/{extension_id}.vsix"

        try:
            print(f"Fallback: Downloading from {vsix_url}...")
            curl_command = ["curl", "-vL", vsix_url, "-o", vsix_path]
            subprocess.run(curl_command, check=True, capture_output=True, text=True)

            print(f"Fallback: Installing from downloaded file '{vsix_path}'...")
            install_from_file_command = [vscode_executable, "--install-extension", vsix_path, "--force"]
            subprocess.run(install_from_file_command, check=True, capture_output=True, text=True)
            
            os.remove(vsix_path) # Clean up the downloaded file

            if any(extension_id.lower() == ext.lower() for ext in get_installed_extensions()):
                 print("Fallback installation successful and verified.")
                 return {"status": "Success", "message": f"Extension '{extension_id}' installed successfully using fallback method."}
            else:
                 return {"status": "Error", "message": "Fallback installation failed during final verification."}

        except Exception as fallback_error:
            return {"status": "Error", "message": f"The fallback installation method also failed. Error: {fallback_error}"}

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