import shutil
import subprocess
import logging
from tools.os_utils import get_linux_distro

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    """
    Uninstalls a tool on supported Linux distributions using their native package managers.

    Supported:
        - APT-based (Debian, Ubuntu)
        - APK-based (Alpine)
        - Pacman-based (Arch)

    Args:
        tool_name (str): Name of the software to uninstall.
        version (str): Version parameter (not used for uninstall).

    Returns:
        dict: Status message and optional details.
    """
    if shutil.which("sudo") is None:
        return {
            "status": "error",
            "message": "sudo not found. Please install sudo or run as root."
        }

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

    elif distro in ("fedora", "centos", "rhel"):
        if shutil.which("dnf") is None:
            logger.error("DNF not found.")
            return {
                "status": "error",
                "message": "DNF not found. Cannot uninstall."
            }
        command = ["sudo", "dnf", "remove", "-y", tool_name]

    elif distro == "alpine":
        if shutil.which("apk") is None:
            logger.error("APK not found.")
            return {
                "status": "error",
                "message": "APK not found. Cannot uninstall."
            }
        command = ["sudo", "apk", "del", tool_name]

    elif distro in ("arch", "manjaro"):
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
            "message": f"{tool_name} uninstalled successfully on {distro}",
            "details": result.stdout.strip(),
            "distribution": distro
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Uninstallation failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to uninstall {tool_name} on {distro}",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
    except Exception as e:
        logger.error(f"Unexpected error during uninstallation: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during uninstallation: {str(e)}"
        }

# Legacy function for backward compatibility
def uninstall_tool_linux(tool_name: str, version: str = "latest") -> dict:
    return handle_tool(tool_name, version)
