import shutil
import subprocess
import logging
from tools.os_utils import has_command, get_os_type, get_linux_distribution

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_linux_package_manager(distro=None):
    """
    Detect and return the package manager based on distro or available commands.
    Args:
      distro (str|None): optional distro id to help determine package manager
    Returns:
      str or None: package manager command name
    """
    # Map common distros to package managers
    distro_pm_map = {
        "ubuntu": "apt",
        "debian": "apt",
        "fedora": "dnf",
        "centos": "yum",
        "rhel": "yum",
        "arch": "pacman",
        "manjaro": "pacman",
        "opensuse": "zypper",
        "alpine": "apk"
    }

    if distro and distro in distro_pm_map:
        pm = distro_pm_map[distro]
        if has_command(pm):
            return pm

    # Fallback: detect package manager by checking commands
    for pm in ["apt", "dnf", "yum", "pacman", "zypper", "apk"]:
        if has_command(pm):
            return pm

    return None

def install_tool_linux(tool_name: str, version: str = "latest") -> dict:
    if shutil.which(tool_name):
        logger.info(f"{tool_name} is already installed.")
        return {
            "status": "success",
            "message": f"{tool_name} is already installed."
        }

    os_type = get_os_type()
    if os_type != "linux":
        return {
            "status": "error",
            "message": f"Invalid call: OS is {os_type}, not Linux."
        }

    distro = get_linux_distribution()
    logger.info(f"Detected Linux distribution: {distro}")

    package_manager = get_linux_package_manager(distro)
    if not package_manager:
        return {
            "status": "error",
            "message": "No supported Linux package manager found on this system."
        }

    logger.info(f"Using package manager: {package_manager}")

    if version != "latest":
        logger.warning("Version-specific install is not supported yet. Proceeding with latest.")

    install_cmds = {
        "apt":    [["sudo", "apt", "update"], ["sudo", "apt", "install", "-y", tool_name]],
        "dnf":    [["sudo", "dnf", "install", "-y", tool_name]],
        "yum":    [["sudo", "yum", "install", "-y", tool_name]],
        "pacman": [["sudo", "pacman", "-Sy", "--noconfirm", tool_name]],
        "zypper": [["sudo", "zypper", "install", "-y", tool_name]],
        "apk":    [["sudo", "apk", "add", tool_name]],
    }

    try:
        for command in install_cmds.get(package_manager, []):
            logger.info(f"Running: {' '.join(command)}")
            subprocess.run(command, check=True, capture_output=True, text=True)
        return {
            "status": "success",
            "message": f"{tool_name} installed successfully via {package_manager}."
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Installation failed with {package_manager}: {e.stderr.strip() if e.stderr else e}")
        return {
            "status": "error",
            "message": f"Failed to install {tool_name} via {package_manager}.",
            "details": e.stderr.strip() if e.stderr else "No additional details."
        }

    except Exception as e:
        logger.exception("Unexpected error during installation.")
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }
# This code provides a Linux-specific tool installation function that detects the package manager and installs the specified tool.
# It handles various Linux distributions and uses subprocess to run the installation commands.