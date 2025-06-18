import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def install_tool_mac(tool_name: str, version: str = "latest") -> dict:
    if shutil.which("brew") is None:
        logger.error("Homebrew not found. Installation cannot proceed.")
        return {
            "status": "error",
            "message": "Homebrew not found. Please install Homebrew."
        }

    is_cask = tool_name.lower() in {
        "docker", "visual-studio-code", "google-chrome", "slack", "zoom"
    }

    command = ["brew", "install", "--cask", tool_name] if is_cask else ["brew", "install", tool_name]

    try:
        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        logger.info(f"Installation successful: {tool_name}")
        return {
            "status": "success",
            "message": f"{tool_name} installed successfully.",
            "details": result.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Installation failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to install {tool_name}.",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
