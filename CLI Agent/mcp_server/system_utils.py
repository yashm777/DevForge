# system_utils.py - MCP Server system initialization utilities
# This module is part of the MCP server implementation and handles system setup
import subprocess
from tools.os_utils import get_os_type, is_linux, is_mac, has_command

def install_homebrew():
    """
    Automatically installs Homebrew on macOS if it's missing.
    This is needed because many Mac users don't have Homebrew installed by default.
    Returns:
        dict: Installation result with status and message
    """
    if not is_mac():
        return {"status": "error", "message": "Homebrew can only be installed on macOS"}
    
    # Check if already installed
    if has_command("brew"):
        return {"status": "success", "message": "Homebrew is already installed"}
    
    try:
        print("Installing Homebrew... This may take a few minutes.")
        
        # Download and run the official Homebrew installation script
        install_command = [
            "/bin/bash", "-c", 
            "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        ]
        
        # Run the installation command
        result = subprocess.run(install_command, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return {"status": "success", "message": "Homebrew installed successfully"}
        else:
            return {"status": "error", "message": f"Homebrew installation failed: {result.stderr}"}
            
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Homebrew installation timed out"}
    except Exception as e:
        return {"status": "error", "message": f"Error installing Homebrew: {e}"}

def check_and_setup_package_managers():
    """
    Checks and sets up package managers for Mac and Linux only.
    For Mac: Installs Homebrew if missing
    For Linux: Checks if apt/yum/dnf is available and updates package lists
    Returns:
        dict: Setup result with detailed information
    """
    os_type = get_os_type()
    
    result = {
        "os_type": os_type,
        "package_manager": None,
        "installation_needed": False,
        "setup_success": False,
        "messages": []
    }
    
    try:
        if is_mac():
            # For macOS, we need Homebrew
            if has_command("brew"):
                result["package_manager"] = "brew"
                result["messages"].append("Homebrew is available")
                result["setup_success"] = True
            else:
                result["installation_needed"] = True
                result["messages"].append("Homebrew not found, installing...")
                
                # Auto-install Homebrew
                install_result = install_homebrew()
                result["messages"].append(install_result["message"])
                
                if install_result["status"] == "success":
                    result["package_manager"] = "brew"
                    result["setup_success"] = True
                else:
                    result["setup_success"] = False
                    
        elif is_linux():
            # For Linux, check for available package managers
            if has_command("apt"):
                result["package_manager"] = "apt"
                result["messages"].append("APT package manager is available")
                
                # Update package lists for better tool availability
                try:
                    print("Updating package lists...")
                    update_result = subprocess.run(
                        ["sudo", "apt", "update"], 
                        capture_output=True, 
                        text=True, 
                        timeout=60
                    )
                    if update_result.returncode == 0:
                        result["messages"].append("APT package lists updated")
                    else:
                        result["messages"].append("APT update failed, but APT is available")
                except:
                    result["messages"].append("APT available but couldn't update (no sudo?)")
                    
                result["setup_success"] = True
                
            elif has_command("yum"):
                result["package_manager"] = "yum"
                result["messages"].append("YUM package manager is available")
                result["setup_success"] = True
                
            elif has_command("dnf"):
                result["package_manager"] = "dnf"
                result["messages"].append("DNF package manager is available")
                result["setup_success"] = True
                
            else:
                result["messages"].append("No supported package manager found on Linux")
                result["setup_success"] = False
        
        return result
        
    except Exception as e:
        result["messages"].append(f"Package manager setup failed: {e}")
        result["setup_success"] = False
        return result
