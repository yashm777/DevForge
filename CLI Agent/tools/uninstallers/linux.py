import shutil
import subprocess
import logging
from tools.utils.os_utils import get_linux_distro

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    """
    Uninstalls a tool on supported Linux distributions using their native package managers.
    """
    if shutil.which("sudo") is None:
        return {
            "status": "error",
            "message": "sudo not found. Please install sudo or run as root."
        }

    distro = get_linux_distro()

    # Command mapping based on distro
    UNINSTALL_COMMANDS = {
        "ubuntu":    lambda t: ["sudo", "apt", "remove", "-y", t],
        "debian":    lambda t: ["sudo", "apt", "remove", "-y", t],
        "fedora":    lambda t: ["sudo", "dnf", "remove", "-y", t],
        "centos":    lambda t: ["sudo", "dnf", "remove", "-y", t],
        "rhel":      lambda t: ["sudo", "dnf", "remove", "-y", t],
        "arch":      lambda t: ["sudo", "pacman", "-Rns", "--noconfirm", t],
        "manjaro":   lambda t: ["sudo", "pacman", "-Rns", "--noconfirm", t],
        "alpine":    lambda t: ["sudo", "apk", "del", t],
    }

    if distro not in UNINSTALL_COMMANDS:
        logger.error(f"Unsupported Linux distribution: {distro}")
        return {
            "status": "error",
            "message": f"Unsupported Linux distribution: {distro}"
        }

    command = UNINSTALL_COMMANDS[distro](tool_name)

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
