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
    Installs a VSCode extension with a robust, platform-aware fallback mechanism.
    It first tries the standard installation. If that fails, it uses curl with a
    browser User-Agent to download the VSIX file and then installs it locally.
    
    Args:
        extension_id (str): The ID of the extension to install (e.g., 'ms-python.python').
    """
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        print("Error: VSCode is not installed or could not be found.")
        return

    # Check if the extension is already installed
    if any(extension_id.lower() == ext.lower() for ext in get_installed_extensions()):
        print(f"Info: Extension '{extension_id}' is already installed.")
        return

    print(f"Attempting standard installation for '{extension_id}'...")
    
    try:
        # --- PRIMARY METHOD: Standard VS Code command ---
        primary_command = [vscode_executable, "--install-extension", extension_id]
        subprocess.run(primary_command, check=True, capture_output=True, text=True)
        
        print(f"Success: Extension '{extension_id}' installed successfully via the standard method.")
        return
        
    except subprocess.CalledProcessError as e:
        # --- FALLBACK TRIGGERED ---
        print(f"Standard installation failed. Triggering fallback method...")
        
        # The fallback is only for non-windows systems
        if sys.platform == "win32":
             print("Error: Fallback method is not available for Windows.")
             return

        # Check if curl is installed
        if not shutil.which("curl"):
            print("Error: Fallback failed because 'curl' command is not installed.")
            return

        # Construct the download URL and local file path
        try:
            publisher, ext_name = extension_id.split('.')
        except ValueError:
            print(f"Error: Invalid extension ID format '{extension_id}'.")
            return
            
        vsix_url = f"https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{ext_name}/latest/vspackage"
        vsix_path = f"/tmp/{extension_id}.vsix"
        
        # Define a standard browser User-Agent to avoid being blocked
        browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36"

        try:
            print(f"Fallback: Downloading from '{vsix_url}'...")
            curl_command = [
                "curl",
                "--location", # Follow redirects
                "--user-agent", browser_user_agent, # Pretend to be a browser
                "--output", vsix_path, # Save to file
                vsix_url
            ]
            subprocess.run(curl_command, check=True, capture_output=True, text=True)

            print(f"Fallback: Installing from downloaded file '{vsix_path}'...")
            install_from_file_command = [vscode_executable, "--install-extension", vsix_path, "--force"]
            subprocess.run(install_from_file_command, check=True, capture_output=True, text=True)
            
            os.remove(vsix_path) # Clean up the downloaded file

            print(f"Success: Extension '{extension_id}' installed successfully using the fallback method.")

        except Exception as fallback_error:
            print(f"Error: The fallback installation method also failed. Reason: {fallback_error}")

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