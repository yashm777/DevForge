"""
Mac VS Code Extension Installer

This file helps install and manage VS Code extensions on Mac computers.
Enhanced with Mac-specific VS Code path detection and installation methods.
"""

import subprocess
import sys
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_vscode_executable():
    """
    Find the path to the VSCode executable on Mac, prioritizing official locations.
    
    Returns:
        str or None: Path to VS Code executable or None if not found
    """
    # Mac-specific VS Code locations
    mac_paths = [
        "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
        "/usr/local/bin/code",
        "/opt/homebrew/bin/code",
        os.path.expanduser("~/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code")
    ]
    
    # Check common Mac locations first
    for path in mac_paths:
        if os.path.exists(path):
            try:
                # Test if the executable works
                result = subprocess.run([path, "--version"], 
                                      check=True, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    logger.info(f"Found VS Code at: {path}")
                    return path
            except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                continue
    
    # Fallback to checking if 'code' is in the PATH
    try:
        result = subprocess.run(["code", "--version"], 
                              check=True, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("Found VS Code in PATH")
            return "code"
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass
    
    logger.warning("VS Code executable not found")
    return None

def is_vscode_installed():
    """
    Check if VSCode is installed on Mac.
    
    Returns:
        bool: True if VS Code is installed, False otherwise
    """
    return find_vscode_executable() is not None

def get_installed_extensions():
    """
    Get a list of installed VSCode extensions.
    
    Returns:
        set: Set of installed extension IDs
    """
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        logger.warning("Cannot get extensions: VS Code not found")
        return set()
    
    try:
        result = subprocess.run([vscode_executable, "--list-extensions"], 
                              check=True, capture_output=True, text=True, timeout=30)
        extensions = set(line.strip() for line in result.stdout.strip().split('\n') if line.strip())
        logger.info(f"Found {len(extensions)} installed extensions")
        return extensions
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.error(f"Failed to get extensions list: {e}")
        return set()

def install_extension(extension_id):
    """
    Install a VSCode extension on Mac and verify its installation.
    
    Args:
        extension_id (str): The ID of the extension to install (e.g., 'ms-python.python')
        
    Returns:
        dict: A dictionary with status and message
    """
    logger.info(f"Installing VS Code extension: {extension_id}")
    
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {
            "status": "error", 
            "message": "VS Code is not installed or could not be found on this Mac system."
        }

    # Get extensions before installation
    extensions_before = get_installed_extensions()
    
    # Check if already installed (case-insensitive)
    if any(extension_id.lower() == ext.lower() for ext in extensions_before):
        return {
            "status": "success", 
            "message": f"Extension '{extension_id}' is already installed."
        }

    logger.info(f"Attempting to install '{extension_id}'...")

    try:
        # Install the extension
        install_command = [vscode_executable, "--install-extension", extension_id, "--force"]
        result = subprocess.run(install_command, 
                              check=True, capture_output=True, text=True, timeout=120)
        
        # Verify installation by checking extensions list
        extensions_after = get_installed_extensions()
        newly_installed_extensions = extensions_after - extensions_before

        # Check if the extension was successfully installed
        if any(extension_id.lower() == ext.lower() for ext in newly_installed_extensions):
            logger.info(f"Successfully installed and verified: {extension_id}")
            return {
                "status": "success", 
                "message": f"Extension '{extension_id}' installed and verified successfully."
            }
        
        # Check if extension is present (might have been there but not detected before)
        if any(extension_id.lower() == ext.lower() for ext in extensions_after):
            logger.info(f"Extension present after installation: {extension_id}")
            return {
                "status": "success", 
                "message": f"Extension '{extension_id}' is present after installation attempt."
            }

        # Installation command succeeded but extension not found
        logger.warning(f"Installation command succeeded but extension not verified: {extension_id}")
        return {
            "status": "error", 
            "message": f"Installation of '{extension_id}' completed but failed verification."
        }

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        logger.error(f"Failed to install {extension_id}: {error_msg}")
        return {
            "status": "error", 
            "message": f"Failed to install extension '{extension_id}'. Error: {error_msg}"
        }
    except subprocess.TimeoutExpired:
        logger.error(f"Installation timed out for {extension_id}")
        return {
            "status": "error", 
            "message": f"Installation of '{extension_id}' timed out. The extension may still be installing in the background."
        }
    except FileNotFoundError:
        return {
            "status": "error", 
            "message": "The VS Code 'code' command is not available in your system PATH."
        }

def uninstall_extension(extension_id):
    """
    Uninstall a VSCode extension on Mac and verify its removal.
    
    Args:
        extension_id (str): The ID of the extension to uninstall (e.g., 'ms-python.python')
        
    Returns:
        dict: A dictionary with status and message
    """
    logger.info(f"Uninstalling VS Code extension: {extension_id}")
    
    vscode_executable = find_vscode_executable()
    if not vscode_executable:
        return {
            "status": "error", 
            "message": "VS Code is not installed or could not be found on this Mac system."
        }

    # Get extensions before uninstallation
    extensions_before = get_installed_extensions()
    
    # Check if extension is installed
    if not any(extension_id.lower() == ext.lower() for ext in extensions_before):
        return {
            "status": "success", 
            "message": f"Extension '{extension_id}' is not installed."
        }

    logger.info(f"Attempting to uninstall '{extension_id}'...")

    try:
        # Uninstall the extension
        uninstall_command = [vscode_executable, "--uninstall-extension", extension_id]
        result = subprocess.run(uninstall_command, 
                              check=True, capture_output=True, text=True, timeout=60)
        
        # Verify uninstallation by checking extensions list
        extensions_after = get_installed_extensions()

        # Check if the extension was successfully removed
        if not any(extension_id.lower() == ext.lower() for ext in extensions_after):
            logger.info(f"Successfully uninstalled and verified: {extension_id}")
            return {
                "status": "success", 
                "message": f"Extension '{extension_id}' uninstalled and verified successfully."
            }
        
        # Uninstallation command succeeded but extension still present
        logger.warning(f"Uninstallation command succeeded but extension still present: {extension_id}")
        return {
            "status": "error", 
            "message": f"Uninstallation of '{extension_id}' completed but failed verification."
        }

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        logger.error(f"Failed to uninstall {extension_id}: {error_msg}")
        return {
            "status": "error", 
            "message": f"Failed to uninstall extension '{extension_id}'. Error: {error_msg}"
        }
    except subprocess.TimeoutExpired:
        logger.error(f"Uninstallation timed out for {extension_id}")
        return {
            "status": "error", 
            "message": f"Uninstallation of '{extension_id}' timed out."
        }
    except FileNotFoundError:
        return {
            "status": "error", 
            "message": "The VS Code 'code' command is not available in your system PATH."
        }

def install_mac_vscode_extension(extension_id, version=None):
    """
    Main function to install VS Code extensions on Mac following the project pattern.
    
    Args:
        extension_id (str): The ID of the extension to install
        version (str, optional): Specific version to install (not commonly used for VS Code extensions)
        
    Returns:
        dict: Status and message dictionary
    """
    logger.info(f"Mac VS Code extension install request: {extension_id}")
    
    try:
        result = install_extension(extension_id)
        return result
        
    except Exception as e:
        logger.error(f"Extension installation failed for {extension_id}: {e}")
        return {
            "status": "error",
            "message": f"Extension installation failed: {str(e)}",
            "details": {"extension_id": extension_id, "error": str(e)}
        }

def uninstall_mac_vscode_extension(extension_id):
    """
    Main function to uninstall VS Code extensions on Mac following the project pattern.
    
    Args:
        extension_id (str): The ID of the extension to uninstall
        
    Returns:
        dict: Status and message dictionary
    """
    logger.info(f"Mac VS Code extension uninstall request: {extension_id}")
    
    try:
        result = uninstall_extension(extension_id)
        return result
        
    except Exception as e:
        logger.error(f"Extension uninstallation failed for {extension_id}: {e}")
        return {
            "status": "error",
            "message": f"Extension uninstallation failed: {str(e)}",
            "details": {"extension_id": extension_id, "error": str(e)}
        }

if __name__ == "__main__":
    if len(sys.argv) not in [3, 4]:
        print("Usage: python vscode_extension_mac.py <install|uninstall> <extension_id> [version]")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    extension_id = sys.argv[2]
    version = sys.argv[3] if len(sys.argv) == 4 else None
    
    if action == "install":
        result = install_mac_vscode_extension(extension_id, version)
    elif action == "uninstall":
        result = uninstall_mac_vscode_extension(extension_id)
    else:
        print("Invalid action. Use 'install' or 'uninstall'.")
        sys.exit(1)
        
    print(result["message"])
    if result["status"] == "error":
        sys.exit(1)
