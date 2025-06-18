import shutil
import subprocess
import logging
from tools.os_utils import get_linux_distro

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def uninstall_tool_linux(tool_name: str) -> dict:
    """
    Uninstalls a tool on supported Linux distributions using their native package managers.

    Supported:
        - APT-based (Debian, Ubuntu)
        - APK-based (Alpine)
        - Pacman-based (Arch)

    Args:
        tool_name (str): Name of the software to uninstall.

    Returns:
        dict: Status message and optional details.
    """
    distro = get_linux_distro()

    # Select the appropriate uninstall command based on distro
    if distro in ("debian", "ubuntu"):
        if shutil.which("apt") is None:
            logger.error("APT not found.")
            return {
                "status": "error",
                "message": "APT not found. Cannot uninstall."
            }
        command = ["sudo", "apt", "remove", "-y", tool_name]

    elif distro == "alpine":
        if shutil.which("apk") is None:
            logger.error("APK not found.")
            return {
                "status": "error",
                "message": "APK not found. Cannot uninstall."
            }
        command = ["sudo", "apk", "del", tool_name]

    elif distro == "arch":
        if shutil.which("pacman") is None:
            logger.error("Pacman not found.")
            return {
                "status": "error",
                "message": "Pacman not found. Cannot uninstall."
            }
        command = ["sudo", "pacman", "-R", "--noconfirm", tool_name]

    else:
        logger.error(f"Unsupported Linux distribution: {distro}")
        return {
            "status": "error",
            "message": f"Unsupported Linux distribution: {distro}"
        }

    # Try running the uninstall command
    try:
        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, capture_output=True, text=True, check=True)

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
