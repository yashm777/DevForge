import shutil
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def uninstall_tool_mac(tool_name: str) -> dict:
    """
    Uninstalls a tool on macOS using Homebrew or Homebrew Cask.

    Args:
        tool_name (str): Name of the software to uninstall.

    Returns:
        dict: Status message and optional details.
    """
    # Check if Homebrew is installed
    if shutil.which("brew") is None:
        logger.error("Homebrew not found. Cannot uninstall.")
        return {
            "status": "error",
            "message": "Homebrew not found. Please install Homebrew first."
        }

    # Try to determine if it's a cask (GUI) package
    check_command = ["brew", "list", "--cask", tool_name]
    is_cask = subprocess.call(check_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

    # Construct uninstall command based on type
    uninstall_command = ["brew", "uninstall", "--cask", tool_name] if is_cask else ["brew", "uninstall", tool_name]

    try:
        logger.info(f"Running command: {' '.join(uninstall_command)}")
        result = subprocess.run(uninstall_command, capture_output=True, text=True, check=True)

        logger.info(f"Uninstallation successful: {tool_name}")
        return {
            "status": "success",
            "message": f"{tool_name} uninstalled successfully.",
            "details": result.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Uninstallation failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to uninstall {tool_name}.",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
