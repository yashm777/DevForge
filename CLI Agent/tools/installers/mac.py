import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    """Handle tool installation on macOS"""
    if shutil.which("brew") is None:
        logger.error("Homebrew not found. Installation cannot proceed.")
        return {
            "status": "error",
            "message": "Homebrew not found. Please install Homebrew first: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        }

    # Define cask applications (GUI apps)
    cask_apps = {
        "docker", "visual-studio-code", "google-chrome", "slack", "zoom", 
        "firefox", "discord", "spotify", "postman", "insomnia", "tableplus"
    }

    is_cask = tool_name.lower() in cask_apps

    try:
        if is_cask:
            command = ["brew", "install", "--cask", tool_name]
            logger.info(f"Installing cask: {tool_name}")
        else:
            command = ["brew", "install", tool_name]
            logger.info(f"Installing formula: {tool_name}")

        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        logger.info(f"Installation successful: {tool_name}")
        return {
            "status": "success",
            "message": f"{tool_name} installed successfully via Homebrew",
            "details": result.stdout.strip(),
            "type": "cask" if is_cask else "formula"
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Installation failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to install {tool_name} via Homebrew",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
    except Exception as e:
        logger.error(f"Unexpected error during installation: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during installation: {str(e)}"
        }

# Legacy function for backward compatibility
def install_tool_mac(tool_name: str, version: str = "latest") -> dict:
    return handle_tool(tool_name, version)
# Legacy function for backward compatibility