import shutil
import subprocess
import logging
from tools.utils.os_utils import get_linux_distro

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    if shutil.which("sudo") is None:
        return {
            "status": "error",
            "message": "sudo not found. Please install sudo or run as root."
        }

    distro = get_linux_distro()

    try:
        if distro in ("debian", "ubuntu"):
            if shutil.which("apt-get") is None:
                return {"status": "error", "message": "APT not found. Cannot update."}

            subprocess.run(["sudo", "apt-get", "update"], capture_output=True, text=True, check=True)

            if tool_name == "all":
                result = subprocess.run(["sudo", "apt-get", "upgrade", "-y"], capture_output=True, text=True, check=True)
            else:
                result = subprocess.run(["sudo", "apt-get", "install", "--only-upgrade", "-y", tool_name], capture_output=True, text=True, check=True)

        elif distro in ("fedora", "centos", "rhel"):
            if shutil.which("dnf") is None:
                return {"status": "error", "message": "DNF not found. Cannot update."}

            if tool_name == "all":
                result = subprocess.run(["sudo", "dnf", "upgrade", "-y"], capture_output=True, text=True, check=True)
            else:
                result = subprocess.run(["sudo", "dnf", "upgrade", "-y", tool_name], capture_output=True, text=True, check=True)

        elif distro in ("arch", "manjaro"):
            if shutil.which("pacman") is None:
                return {"status": "error", "message": "Pacman not found. Cannot update."}

            subprocess.run(["sudo", "pacman", "-Sy"], capture_output=True, text=True, check=True)

            if tool_name == "all":
                result = subprocess.run(["sudo", "pacman", "-Su", "--noconfirm"], capture_output=True, text=True, check=True)
            else:
                result = subprocess.run(["sudo", "pacman", "-S", "--noconfirm", tool_name], capture_output=True, text=True, check=True)

        elif distro == "alpine":
            if shutil.which("apk") is None:
                return {"status": "error", "message": "APK not found. Cannot update."}

            subprocess.run(["sudo", "apk", "update"], capture_output=True, text=True, check=True)

            if tool_name == "all":
                result = subprocess.run(["sudo", "apk", "upgrade"], capture_output=True, text=True, check=True)
            else:
                result = subprocess.run(["sudo", "apk", "add", "--upgrade", tool_name], capture_output=True, text=True, check=True)

        else:
            return {"status": "error", "message": f"Unsupported Linux distribution: {distro}"}

        return {
            "status": "success",
            "message": f"{'All packages' if tool_name == 'all' else tool_name} updated successfully via {distro.capitalize()}",
            "details": result.stdout.strip(),
            "distribution": distro
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Update failed: {e.stderr.strip() if e.stderr else str(e)}")
        return {
            "status": "error",
            "message": f"Failed to update {tool_name} on {distro}",
            "details": e.stderr.strip() or e.stdout.strip() or str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return {
            "status": "error",
            "message": f"Unexpected error during update: {str(e)}"
        }

# Legacy compatibility
def update_tool_linux(tool_name: str, version: str = "latest") -> dict:
    return handle_tool(tool_name, version)
