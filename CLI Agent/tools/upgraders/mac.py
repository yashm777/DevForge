import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    """
    Update a tool on macOS using Homebrew.

    Args:
        tool_name (str): Name of the tool to update.
        version (str): Version to update to (defaults to latest).

    Returns:
        dict: Status message and update information.
    """
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
    return handle_tool(tool_name, version) 