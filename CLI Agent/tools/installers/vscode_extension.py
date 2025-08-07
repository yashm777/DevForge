import subprocess
import sys
import os
import json
import requests
import zipfile
import tempfile
import shutil
from pathlib import Path

def get_vscode_extensions_dir():
    """Get the VSCode extensions directory path."""
    if sys.platform == "win32":
        return os.path.expanduser("~/.vscode/extensions")
    elif sys.platform == "darwin":
        return os.path.expanduser("~/.vscode/extensions")
    else:  # Linux
        return os.path.expanduser("~/.vscode/extensions")

def get_installed_extensions():
    """Get a list of installed VSCode extensions by reading the extensions directory."""
    extensions_dir = get_vscode_extensions_dir()
    if not os.path.exists(extensions_dir):
        return set()
    
    extensions = set()
    try:
        for item in os.listdir(extensions_dir):
            item_path = os.path.join(extensions_dir, item)
            if os.path.isdir(item_path):
                # Extension directories are named like "publisher.extension-version"
                # We want just "publisher.extension"
                if '-' in item:
                    # Remove version part
                    extension_id = '-'.join(item.split('-')[:-1])
                    extensions.add(extension_id)
                else:
                    extensions.add(item)
    except Exception as e:
        print(f"Warning: Could not read extensions directory: {e}")
    
    return extensions

def download_extension(extension_id):
    """Download extension from VSCode marketplace."""
    print(f"Downloading extension '{extension_id}' from marketplace...")
    
    try:
        # Parse extension ID
        if '.' not in extension_id:
            return None, "Invalid extension ID format. Expected 'publisher.extension'"
        
        publisher, name = extension_id.split('.', 1)
        
        # VSCode Marketplace API URL
        url = f"https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{name}/latest/vspackage"
        
        # Download the extension
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return None, f"Failed to download extension. HTTP {response.status_code}"
        
        # Save to temporary file
        temp_file = tempfile.mktemp(suffix='.vsix')
        with open(temp_file, 'wb') as f:
            f.write(response.content)
        
        return temp_file, None
        
    except Exception as e:
        return None, f"Download failed: {str(e)}"

def extract_extension(vsix_path, extension_id):
    """Extract VSIX file to extensions directory."""
    extensions_dir = get_vscode_extensions_dir()
    
    try:
        # Create extensions directory if it doesn't exist
        os.makedirs(extensions_dir, exist_ok=True)
        
        # Create temporary extraction directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract VSIX (it's a ZIP file)
            with zipfile.ZipFile(vsix_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Find package.json to get version info
            package_json_path = os.path.join(temp_dir, 'extension', 'package.json')
            if not os.path.exists(package_json_path):
                return False, "Invalid extension package - missing package.json"
            
            # Read package.json to get version
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            version = package_data.get('version', '1.0.0')
            
            # Create final extension directory name
            extension_dir_name = f"{extension_id}-{version}"
            final_path = os.path.join(extensions_dir, extension_dir_name)
            
            # Remove existing version if it exists
            if os.path.exists(final_path):
                shutil.rmtree(final_path)
            
            # Copy extension files
            extension_source = os.path.join(temp_dir, 'extension')
            shutil.copytree(extension_source, final_path)
            
            return True, f"Extension extracted to {final_path}"
            
    except Exception as e:
        return False, f"Extraction failed: {str(e)}"
    finally:
        # Clean up VSIX file
        try:
            os.remove(vsix_path)
        except:
            pass

def install_extension(extension_id):
    """
    Install a VSCode extension by downloading from marketplace.
    
    Args:
        extension_id (str): The ID of the extension to install (e.g., 'ms-python.python').
        
    Returns:
        dict: A dictionary with a status message.
    """
    # Check if already installed
    installed_extensions = get_installed_extensions()
    if any(extension_id.lower() == ext.lower() for ext in installed_extensions):
        return {"status": "Success", "message": f"Extension '{extension_id}' is already installed."}
    
    print(f"Installing extension '{extension_id}' via direct download...")
    
    # Download extension
    vsix_path, download_error = download_extension(extension_id)
    if download_error:
        return {"status": "Error", "message": download_error}
    
    # Extract extension
    success, extract_message = extract_extension(vsix_path, extension_id)
    if not success:
        return {"status": "Error", "message": extract_message}
    
    # Verify installation
    installed_extensions_after = get_installed_extensions()
    if any(extension_id.lower() == ext.lower() for ext in installed_extensions_after):
        return {"status": "Success", "message": f"Extension '{extension_id}' installed successfully via direct download."}
    else:
        return {"status": "Success", "message": f"Extension '{extension_id}' installation completed. {extract_message}"}

def uninstall_extension(extension_id):
    """
    Uninstall a VSCode extension by removing its directory.
    
    Args:
        extension_id (str): The ID of the extension to uninstall (e.g., 'ms-python.python').
        
    Returns:
        dict: A dictionary with a status message.
    """
    extensions_dir = get_vscode_extensions_dir()
    if not os.path.exists(extensions_dir):
        return {"status": "Success", "message": f"Extension '{extension_id}' is not installed."}
    
    # Find extension directories that match
    removed_count = 0
    try:
        for item in os.listdir(extensions_dir):
            if item.lower().startswith(extension_id.lower() + '-'):
                item_path = os.path.join(extensions_dir, item)
                if os.path.isdir(item_path):
                    print(f"Removing extension directory: {item}")
                    shutil.rmtree(item_path)
                    removed_count += 1
    except Exception as e:
        return {"status": "Error", "message": f"Failed to uninstall extension '{extension_id}'. Error: {str(e)}"}
    
    if removed_count > 0:
        return {"status": "Success", "message": f"Extension '{extension_id}' uninstalled successfully. Removed {removed_count} version(s)."}
    else:
        return {"status": "Success", "message": f"Extension '{extension_id}' is not installed."}

# Fallback functions for when direct installation fails
def find_vscode_executable():
    """Find the path to the VSCode executable (fallback only)."""
    if sys.platform == "win32":
        user_profile = os.path.expanduser("~")
        common_paths = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft VS Code", "bin", "code.cmd"),
            os.path.join(user_profile, "AppData", "Local", "Programs", "Microsoft VS Code", "bin", "code.cmd")
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    elif sys.platform.startswith("linux"):
        user_home = os.path.expanduser("~")
        common_paths = [
            "/usr/bin/code",
            "/snap/bin/code",
            "/usr/local/bin/code",
            os.path.join(user_home, ".local", "bin", "code"),
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    elif sys.platform == "darwin":
        common_paths = [
            "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
            "/usr/local/bin/code"
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
    
    # Check PATH
    try:
        subprocess.run(["code", "--version"], check=True, capture_output=True, text=True, timeout=5)
        return "code"
    except:
        pass
    
    return None

def is_vscode_installed():
    """Check if VSCode is installed."""
    return find_vscode_executable() is not None or os.path.exists(get_vscode_extensions_dir())

def fallback_install_extension(extension_id):
    """Fallback to CLI installation if direct download fails."""
    print(f"Attempting fallback CLI installation for '{extension_id}'...")
    
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {"status": "Error", "message": "VSCode is not installed and direct installation failed."}
    
    try:
        # Kill any existing VSCode processes
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "Code.exe"], capture_output=True, check=False)
        else:
            subprocess.run(["pkill", "-f", "code"], capture_output=True, check=False)
        
        # Simple CLI installation
        install_command = [vscode_executable, "--install-extension", extension_id, "--force"]
        use_shell = sys.platform == "win32"
        
        result = subprocess.run(install_command, check=True, shell=use_shell, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            return {"status": "Success", "message": f"Extension '{extension_id}' installed via CLI fallback."}
        else:
            return {"status": "Error", "message": f"CLI installation failed with return code {result.returncode}"}
            
    except Exception as e:
        return {"status": "Error", "message": f"Fallback installation failed: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python vscode_extension.py <install|uninstall> <extension_id>")
        print("This version uses direct marketplace download to avoid opening VSCode.")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    extension_id = sys.argv[2]
    
    if action == "install":
        result = install_extension(extension_id)
        # If direct installation failed, try fallback
        if result["status"] == "Error" and "download" in result["message"].lower():
            print("Direct installation failed, trying CLI fallback...")
            result = fallback_install_extension(extension_id)
    elif action == "uninstall":
        result = uninstall_extension(extension_id)
    else:
        print("Invalid action. Use 'install' or 'uninstall'.")
        sys.exit(1)
        
    print(result["message"])
    if result["status"] == "Error":
        sys.exit(1)