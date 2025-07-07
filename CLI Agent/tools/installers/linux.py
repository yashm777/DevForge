import subprocess
import shutil
import platform
import logging
from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_sudo_access():
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking sudo access: {e}")
        return False

def install_linux_tool(tool, version="latest"):
    if not check_sudo_access():
        return {
            "status": "error",
            "message": "sudo access required for package installation. Please run: sudo -v"
        }

    try:
        os_type = platform.system().lower()
        resolved = resolve_tool_name(tool, os_type, version)
        resolved_tool = resolved["name"]
        fallback_msg = resolved.get("fallback")

        if shutil.which("apt-get"):
            subprocess.run(["sudo", "apt-get", "update"], capture_output=True, text=True)
            cmd = ["sudo", "apt-get", "install", "-y", resolved_tool]
        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "install", "-y", resolved_tool]
        elif shutil.which("pacman"):
            cmd = ["sudo", "pacman", "-Sy", "--noconfirm", resolved_tool]
        elif shutil.which("apk"):
            cmd = ["sudo", "apk", "add", resolved_tool]
        else:
            return {"status": "error", "message": "No supported package manager found."}

        result = subprocess.run(cmd, capture_output=True, text=True)

        message = result.stdout.strip() or f"Installed {resolved_tool}"
        if fallback_msg:
            message = f"{fallback_msg}\n{message}"

        if result.returncode == 0:
            return {
                "status": "success",
                "message": message,
                "warnings": result.stderr.strip() if result.stderr.strip() else None
            }
        else:
            logger.warning(f"Installation failed: {result.stderr.strip()}")
            return {
                "status": "error",
                "message": result.stderr.strip() or result.stdout.strip()
            }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Installation failed: {e.stderr.strip() if e.stderr else str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }
