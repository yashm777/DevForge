import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool_mac(tool_name: str, version: str = "latest") -> dict:
    """
    Update a tool on macOS using appropriate package manager.

    Args:
        tool_name (str): Name of the tool to update.
        version (str): Version to update to (defaults to latest).

    Returns:
        dict: Status message and update information.
    """
    # Handle Python packages (pip, setuptools, wheel, etc.)
    python_packages = ["pip", "setuptools", "wheel", "virtualenv", "pipenv"]
    
    if tool_name in python_packages:
        return _update_python_package(tool_name, version)
    
    # Handle npm packages
    npm_packages = ["npm", "yarn", "pnpm"]
    if tool_name in npm_packages:
        return _update_npm_package(tool_name, version)
    
    # Handle Homebrew packages (default)
    return _update_homebrew_package(tool_name, version)

def _update_python_package(tool_name: str, version: str) -> dict:
    """Update Python packages using pip."""
    try:
        # Check if pip is available
        if shutil.which("pip") is None and shutil.which("pip3") is None:
            return {
                "status": "error",
                "message": "pip not found. Please install Python first."
            }
        
        pip_cmd = "pip3" if shutil.which("pip3") else "pip"
        
        if tool_name == "pip":
            # Special case for pip itself
            command = [pip_cmd, "install", "--upgrade", "pip"]
        else:
            command = [pip_cmd, "install", "--upgrade", tool_name]
        
        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"{tool_name} updated successfully via pip",
            "details": result.stdout.strip(),
            "type": "python_package"
        }
    
    except subprocess.CalledProcessError as e:
        logger.error(f"pip update failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to update {tool_name} via pip",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
    except Exception as e:
        logger.error(f"Unexpected error during pip update: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during pip update: {str(e)}"
        }

def _update_npm_package(tool_name: str, version: str) -> dict:
    """Update npm packages using npm."""
    try:
        if shutil.which("npm") is None:
            return {
                "status": "error",
                "message": "npm not found. Please install Node.js first."
            }
        
        if tool_name == "npm":
            command = ["npm", "install", "-g", "npm@latest"]
        else:
            command = ["npm", "install", "-g", f"{tool_name}@latest"]
        
        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        
        return {
            "status": "success",
            "message": f"{tool_name} updated successfully via npm",
            "details": result.stdout.strip(),
            "type": "npm_package"
        }
    
    except subprocess.CalledProcessError as e:
        logger.error(f"npm update failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to update {tool_name} via npm",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
    except Exception as e:
        logger.error(f"Unexpected error during npm update: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during npm update: {str(e)}"
        }

def _update_homebrew_package(tool_name: str, version: str) -> dict:
    """Update packages using Homebrew."""
    if shutil.which("brew") is None:
        logger.error("Homebrew not found. Cannot update.")
        return {
            "status": "error",
            "message": "Homebrew not found. Please install Homebrew first."
        }

    try:
        # First, update Homebrew itself
        logger.info("Updating Homebrew...")
        subprocess.run(["brew", "update"], capture_output=True, text=True, check=True)

        # Check if the tool is installed
        if tool_name == "all":
            # Update all packages
            logger.info("Updating all Homebrew packages...")
            result = subprocess.run(["brew", "upgrade"], capture_output=True, text=True, check=True)
            
            return {
                "status": "success",
                "message": "All Homebrew packages updated successfully",
                "details": result.stdout.strip()
            }
        else:
            # Check if it's a cask or formula
            check_cask_cmd = ["brew", "list", "--cask", tool_name]
            is_cask = subprocess.call(check_cask_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

            if is_cask:
                command = ["brew", "upgrade", "--cask", tool_name]
                logger.info(f"Updating cask: {tool_name}")
            else:
                command = ["brew", "upgrade", tool_name]
                logger.info(f"Updating formula: {tool_name}")

            logger.info(f"Running command: {' '.join(command)}")
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            return {
                "status": "success",
                "message": f"{tool_name} updated successfully via Homebrew",
                "details": result.stdout.strip(),
                "type": "cask" if is_cask else "formula"
            }

    except subprocess.CalledProcessError as e:
        logger.error(f"Update failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to update {tool_name} via Homebrew",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
    except Exception as e:
        logger.error(f"Unexpected error during update: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during update: {str(e)}"
        }

# Legacy function for backward compatibility
def update_tool_mac(tool_name: str, version: str = "latest") -> dict:
    return handle_tool_mac(tool_name, version)