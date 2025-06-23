import shutil
import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    """
    Uninstalls a tool on macOS using Homebrew or Homebrew Cask.

    Args:
        tool_name (str): Name of the software to uninstall.
        version (str): Version parameter (not used for uninstall).

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
            "message": f"{tool_name} uninstalled successfully via Homebrew",
            "details": result.stdout.strip(),
            "type": "cask" if is_cask else "formula"
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Uninstallation failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to uninstall {tool_name} via Homebrew",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
    except Exception as e:
        logger.error(f"Unexpected error during uninstallation: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during uninstallation: {str(e)}"
        }

# Legacy function for backward compatibility
def uninstall_tool_mac(tool_name: str, version: str = "latest") -> dict:
    return handle_tool(tool_name, version)
