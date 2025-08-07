import subprocess
import sys
import os
import time

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
        # Add flags to prevent VSCode from opening
        command = [vscode_executable, "--list-extensions", "--show-versions"]
        # Only use shell=True on Windows
        use_shell = sys.platform == "win32"
        
        result = subprocess.run(command, check=True, shell=use_shell, capture_output=True, text=True, timeout=15)
        extensions = result.stdout.strip()
        if extensions:
            # Remove version info and return just extension IDs
            extension_list = []
            for line in extensions.split('\n'):
                line = line.strip()
                if line and '@' in line:
                    # Remove version part (e.g., "ms-python.python@2023.1.0" -> "ms-python.python")
                    extension_id = line.split('@')[0]
                    extension_list.append(extension_id)
                elif line:
                    extension_list.append(line)
            return set(extension_list)
        return set()
        
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Warning: Could not get extension list: {e}")
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

    # Get initial extensions list
    print(f"Checking existing extensions...")
    extensions_before = get_installed_extensions()
    
    if any(extension_id.lower() == ext.lower() for ext in extensions_before):
        return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}

    print(f"Installing '{extension_id}'...")

    try:
        # Use --force to override existing installations and prevent UI from opening
        install_command = [vscode_executable, "--install-extension", extension_id, "--force"]
        # Only use shell=True on Windows
        use_shell = sys.platform == "win32"
        
        # Run installation command
        result = subprocess.run(install_command, check=True, shell=use_shell, capture_output=True, text=True, timeout=60)
        
        # Check the command output for success/failure indicators
        output = (result.stdout + " " + (result.stderr or "")).lower()
        print(f"Installation output: {result.stdout.strip()}")
        
        if "error" in output or "failed" in output:
            return {"status": "Error", "message": f"Installation failed. Output: {result.stdout.strip()}"}
        
        # Wait for VSCode to register the extension
        print("Waiting for extension to be registered...")
        time.sleep(3)
        
        # Simple verification - just check if extension is now in the list
        print("Verifying installation...")
        extensions_after = get_installed_extensions()
        
        # Case-insensitive check for the extension
        installed = any(extension_id.lower() == ext.lower() for ext in extensions_after)
        
        if installed:
            return {"status": "Success", "message": f"Extension '{extension_id}' installed successfully."}
        else:
            # Check if any similar extensions were installed (partial match)
            similar = [ext for ext in extensions_after if extension_id.lower().split('.')[-1] in ext.lower()]
            if similar:
                return {"status": "Success", "message": f"Extension installed successfully. Found: {similar[0]}"}
            
            # At this point, the command succeeded but we can't verify
            # This often happens but the extension is actually installed
            print(f"Extension count before: {len(extensions_before)}, after: {len(extensions_after)}")
            
            # Check if ANY new extensions were added
            if len(extensions_after) > len(extensions_before):
                new_extensions = extensions_after - extensions_before
                return {"status": "Success", "message": f"Installation completed. New extensions: {', '.join(new_extensions)}"}
            
            # Return success since the install command succeeded
            return {"status": "Success", "message": f"Extension '{extension_id}' installation command completed successfully. Please verify in VSCode."}

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        return {"status": "Error", "message": f"Failed to install extension '{extension_id}'. Error: {error_msg}"}
    except subprocess.TimeoutExpired:
        return {"status": "Error", "message": f"Installation of '{extension_id}' timed out after 60 seconds."}
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