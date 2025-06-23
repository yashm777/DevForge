import shutil
import subprocess
import logging
from tools.os_utils import get_linux_distro

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    """
    Update a tool on Linux using the appropriate package manager.

    Args:
        tool_name (str): Name of the tool to update.
        version (str): Version to update to (defaults to latest).

    Returns:
        dict: Status message and update information.
    """
    if shutil.which("sudo") is None:
        return {
            "status": "error",
            "message": "sudo not found. Please install sudo or run as root."
        }

    distro = get_linux_distro()

    try:
        if distro in ("debian", "ubuntu"):
            if shutil.which("apt") is None:
                return {
                    "status": "error",
                    "message": "APT not found. Cannot update."
                }
            
            # Update package lists
            subprocess.run(["sudo", "apt", "update"], capture_output=True, text=True, check=True)
            
            if tool_name == "all":
                # Update all packages
                result = subprocess.run(["sudo", "apt", "upgrade", "-y"], capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": "All packages updated successfully via APT",
                    "details": result.stdout.strip(),
                    "distribution": distro
                }
            else:
                # Update specific package
                result = subprocess.run(["sudo", "apt", "install", "--only-upgrade", "-y", tool_name], capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": f"{tool_name} updated successfully via APT",
                    "details": result.stdout.strip(),
                    "distribution": distro
                }

        elif distro in ("fedora", "centos", "rhel"):
            if shutil.which("dnf") is None:
                return {
                    "status": "error",
                    "message": "DNF not found. Cannot update."
                }
            
            if tool_name == "all":
                # Update all packages
                result = subprocess.run(["sudo", "dnf", "update", "-y"], capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": "All packages updated successfully via DNF",
                    "details": result.stdout.strip(),
                    "distribution": distro
                }
            else:
                # Update specific package
                result = subprocess.run(["sudo", "dnf", "update", "-y", tool_name], capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": f"{tool_name} updated successfully via DNF",
                    "details": result.stdout.strip(),
                    "distribution": distro
                }

        elif distro in ("arch", "manjaro"):
            if shutil.which("pacman") is None:
                return {
                    "status": "error",
                    "message": "Pacman not found. Cannot update."
                }
            
            # Update package database
            subprocess.run(["sudo", "pacman", "-Sy"], capture_output=True, text=True, check=True)
            
            if tool_name == "all":
                # Update all packages
                result = subprocess.run(["sudo", "pacman", "-Su", "--noconfirm"], capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": "All packages updated successfully via Pacman",
                    "details": result.stdout.strip(),
                    "distribution": distro
                }
            else:
                # Update specific package
                result = subprocess.run(["sudo", "pacman", "-S", "--noconfirm", tool_name], capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": f"{tool_name} updated successfully via Pacman",
                    "details": result.stdout.strip(),
                    "distribution": distro
                }

        elif distro == "alpine":
            if shutil.which("apk") is None:
                return {
                    "status": "error",
                    "message": "APK not found. Cannot update."
                }
            
            # Update package index
            subprocess.run(["sudo", "apk", "update"], capture_output=True, text=True, check=True)
            
            if tool_name == "all":
                # Update all packages
                result = subprocess.run(["sudo", "apk", "upgrade"], capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": "All packages updated successfully via APK",
                    "details": result.stdout.strip(),
                    "distribution": distro
                }
            else:
                # Update specific package
                result = subprocess.run(["sudo", "apk", "add", "--upgrade", tool_name], capture_output=True, text=True, check=True)
                return {
                    "status": "success",
                    "message": f"{tool_name} updated successfully via APK",
                    "details": result.stdout.strip(),
                    "distribution": distro
                }

        else:
            return {
                "status": "error",
                "message": f"Unsupported Linux distribution: {distro}"
            }

    except subprocess.CalledProcessError as e:
        logger.error(f"Update failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to update {tool_name} on {distro}",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
    except Exception as e:
        logger.error(f"Unexpected error during update: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during update: {str(e)}"
        }

# Legacy function for backward compatibility
def update_tool_linux(tool_name: str, version: str = "latest") -> dict:
    return handle_tool(tool_name, version) 