import subprocess
import sys
import os

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

    # 2. Check common locations for Linux (Ubuntu and other distributions)
    elif sys.platform.startswith("linux"):
        user_home = os.path.expanduser("~")
        common_paths = [
            "/usr/bin/code",  # System-wide installation via apt
            "/snap/bin/code",  # Snap installation
            "/usr/local/bin/code",  # Manual system installation
            os.path.join(user_home, ".local", "bin", "code"),  # User-local installation
            "/opt/code/bin/code",  # Alternative installation location
            "/opt/visual-studio-code/bin/code",  # Alternative installation location
            "/usr/share/code/bin/code",  # Another possible location
        ]
        for path in common_paths:
            if os.path.exists(path):
                try:
                    subprocess.run([path, "--version"], check=True, capture_output=True, text=True)
                    return path
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue

    # 3. Check common locations for macOS
    elif sys.platform == "darwin":
        common_paths = [
            "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
            "/usr/local/bin/code"
        ]
        for path in common_paths:
            if os.path.exists(path):
                try:
                    subprocess.run([path, "--version"], check=True, capture_output=True, text=True)
                    return path
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue

    # 4. Fallback to checking if 'code' is in the PATH
    try:
        # On Windows, we need shell=True for the PATH lookup
        use_shell = sys.platform == "win32"
        subprocess.run(["code", "--version"], check=True, shell=use_shell, capture_output=True, text=True)
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
        # Only use shell=True on Windows
        use_shell = sys.platform == "win32"
        result = subprocess.run(command, check=True, shell=use_shell, capture_output=True, text=True)
        extensions = result.stdout.strip()
        if extensions:
            return set(extensions.split('\n'))
        return set()
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
        # Only use shell=True on Windows
        use_shell = sys.platform == "win32"
        subprocess.run(install_command, check=True, shell=use_shell, capture_output=True, text=True)
        
        extensions_after = get_installed_extensions()

        newly_installed_extensions = extensions_after - extensions_before

        if any(extension_id.lower() == ext.lower() for ext in newly_installed_extensions):
            return {"status": "Success", "message": f"Extension '{extension_id}' installed and verified successfully."}
        
        if any(extension_id.lower() == ext.lower() for ext in extensions_after):
            return {"status": "Success", "message": f"Extension '{extension_id}' is present after installation attempt."}

        return {"status": "Error", "message": f"Installation of '{extension_id}' failed verification."}

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        return {"status": "Error", "message": f"Failed to install extension '{extension_id}'. Error: {error_msg}"}
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
        # Only use shell=True on Windows
        use_shell = sys.platform == "win32"
        subprocess.run(uninstall_command, check=True, shell=use_shell, capture_output=True, text=True)
        
        extensions_after = get_installed_extensions()

        if not any(extension_id.lower() == ext.lower() for ext in extensions_after):
            return {"status": "Success", "message": f"Extension '{extension_id}' uninstalled and verified successfully."}
        
        return {"status": "Error", "message": f"Uninstallation of '{extension_id}' failed verification."}

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        return {"status": "Error", "message": f"Failed to uninstall extension '{extension_id}'. Error: {error_msg}"}
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