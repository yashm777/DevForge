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
    Install a VSCode extension with platform-specific logic and verbose logging for diagnostics.
    
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

    print(f"Attempting to install '{extension_id}' with verbose logging for diagnostics...")

    try:
        # --- Platform-Specific Command ---
        if sys.platform == "win32":
            # WINDOWS: Keep the original working command
            install_command = [vscode_executable, "--install-extension", extension_id, "--force"]
            subprocess.run(install_command, check=True, shell=True, capture_output=True, text=True)
        else:
            # LINUX/MACOS: Add --verbose for detailed error logging
            install_command = [vscode_executable, "--install-extension", extension_id, "--force", "--verbose"]
            env = os.environ.copy()
            env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
            # We will now intentionally capture and print the output for diagnosis
            result = subprocess.run(install_command, check=True, capture_output=True, text=True, env=env)
            print("--- VSCode Verbose Output ---")
            print(result.stdout)
            print(result.stderr)
            print("-----------------------------")
        
        # --- Verification Logic ---
        extensions_after = get_installed_extensions()
        if any(extension_id.lower() == ext.lower() for ext in extensions_after):
            return {"status": "Success", "message": f"Extension '{extension_id}' installed and verified successfully."}

        return {"status": "Error", "message": f"Installation of '{extension_id}' failed verification. See console for verbose logs."}

    except subprocess.CalledProcessError as e:
        # The verbose output will be in stderr, which is crucial for debugging
        error_message = e.stderr.strip() if e.stderr else "No error output from VSCode."
        return {"status": "Error", "message": f"Failed to install extension '{extension_id}'. Verbose Error Log:\n---\n{error_message}\n---"}
    except FileNotFoundError:
        return {"status": "Error", "message": "The 'code' command is not available."}

    except subprocess.CalledProcessError as e:
        # Provide a more detailed error message
        error_message = e.stderr.strip() if e.stderr else "No error output."
        if "CERT_HAS_EXPIRED" in error_message or "unable to verify the first certificate" in error_message:
            error_message += "\nThis might be an SSL/TLS certificate issue. Ensure your system's certificates are up to date."
        return {"status": "Error", "message": f"Failed to install extension '{extension_id}'. Error: {error_message}"}
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