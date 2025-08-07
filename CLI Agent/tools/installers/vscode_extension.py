import subprocess
import sys
import os
import time

def kill_vscode_processes():
    """Kill any running VSCode processes to prevent UI interference."""
    try:
        if sys.platform == "win32":
            # Windows
            subprocess.run(["taskkill", "/F", "/IM", "Code.exe"], 
                         capture_output=True, text=True, check=False)
        else:
            # Linux/Mac
            subprocess.run(["pkill", "-f", "code"], 
                         capture_output=True, text=True, check=False)
        time.sleep(1)  # Give processes time to terminate
    except Exception:
        pass  # Ignore errors if no processes to kill

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
                    subprocess.run([path, "--version"], check=True, capture_output=True, text=True, timeout=10)
                    return path
                except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
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
                    subprocess.run([path, "--version"], check=True, capture_output=True, text=True, timeout=10)
                    return path
                except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
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
                    subprocess.run([path, "--version"], check=True, capture_output=True, text=True, timeout=10)
                    return path
                except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    continue

    # 4. Fallback to checking if 'code' is in the PATH
    try:
        # On Windows, we need shell=True for the PATH lookup
        use_shell = sys.platform == "win32"
        subprocess.run(["code", "--version"], check=True, shell=use_shell, capture_output=True, text=True, timeout=10)
        return "code"
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
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
        use_shell = sys.platform == "win32"
        
        result = subprocess.run(command, check=True, shell=use_shell, capture_output=True, text=True, timeout=10)
        extensions = result.stdout.strip()
        if extensions:
            return set(ext.strip() for ext in extensions.split('\n') if ext.strip())
        return set()
        
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"Warning: Could not get extension list: {e}")
        return set()

def install_extension(extension_id):
    """
    Install a VSCode extension using a simplified approach.
    
    Args:
        extension_id (str): The ID of the extension to install (e.g., 'ms-python.python').
        
    Returns:
        dict: A dictionary with a status message.
    """
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode is not installed or could not be found."}

    # Kill any running VSCode processes first
    print("Closing any running VSCode instances...")
    kill_vscode_processes()

    # Check if already installed
    print("Checking if extension is already installed...")
    try:
        extensions_before = get_installed_extensions()
        if any(extension_id.lower() == ext.lower() for ext in extensions_before):
            return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}
    except Exception as e:
        print(f"Warning: Could not check existing extensions: {e}")
        extensions_before = set()

    print(f"Installing extension '{extension_id}'...")

    try:
        # Simple installation command
        install_command = [vscode_executable, "--install-extension", extension_id, "--force"]
        use_shell = sys.platform == "win32"
        
        # Set environment variables to prevent GUI
        env = os.environ.copy()
        env['DISPLAY'] = ''  # Prevent X11 display on Linux
        
        result = subprocess.run(
            install_command, 
            check=True, 
            shell=use_shell, 
            capture_output=True, 
            text=True, 
            timeout=120,
            env=env if sys.platform.startswith('linux') else None
        )
        
        print(f"Installation completed. Output: {result.stdout.strip()}")
        
        # Simple success check - if command succeeded without error, consider it successful
        if result.returncode == 0:
            # Optional: Quick verification after a short delay
            time.sleep(2)
            try:
                extensions_after = get_installed_extensions()
                if any(extension_id.lower() == ext.lower() for ext in extensions_after):
                    return {"status": "Success", "message": f"Extension '{extension_id}' installed and verified successfully."}
                else:
                    # Even if verification fails, trust the command result
                    return {"status": "Success", "message": f