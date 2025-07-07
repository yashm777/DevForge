import shutil
import subprocess
import logging
from tools.utils.os_utils import get_linux_distro
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_version(tool_name: str, version: str = "latest") -> dict:
    """
    Check the version of a tool on Linux.

    Args:
        tool_name (str): Name of the tool to check version for.
        version (str): Unused but kept for interface consistency.

    Returns:
        dict: Status message and version information.
    """
    try:
        if shutil.which(tool_name) is None:
            return {
                "status": "error",
                "message": f"'{tool_name}' is not installed or not in PATH"
            }

        # Try common version flags
        version_commands = [
            [tool_name, "--version"],
            [tool_name, "-v"],
            [tool_name, "-V"],
            [tool_name, "version"]
        ]

        for cmd in version_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name}",
                        "version": result.stdout.strip(),
                        "command": " ".join(cmd)
                    }
            except Exception as e:
                logger.debug(f"Command {cmd} failed: {e}")
                continue

        # --- Fallback: Try distro-specific package manager output ---
        distro = get_linux_distro()
        logger.debug(f"Falling back to distro package manager version detection for {distro}")

        if distro in ("debian", "ubuntu") and shutil.which("dpkg"):
            try:
                result = subprocess.run(["dpkg", "-l", tool_name], capture_output=True, text=True, timeout=5)
                for line in result.stdout.strip().splitlines():
                    if line.startswith('ii') and tool_name in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return {
                                "status": "success",
                                "message": f"Version info for {tool_name} (APT)",
                                "version": parts[2],
                                "source": "apt/dpkg"
                            }
            except Exception as e:
                logger.debug(f"dpkg failed: {e}")

        elif distro in ("fedora", "centos", "rhel") and shutil.which("rpm"):
            try:
                result = subprocess.run(["rpm", "-q", tool_name], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return {
                        "status": "success",
                        "message": f"Version info for {tool_name} (RPM)",
                        "version": result.stdout.strip(),
                        "source": "rpm"
                    }
            except Exception as e:
                logger.debug(f"rpm failed: {e}")

        elif distro in ("arch", "manjaro") and shutil.which("pacman"):
            try:
                result = subprocess.run(["pacman", "-Q", tool_name], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return {
                        "status": "success",
                        "message": f"Version info for {tool_name} (Pacman)",
                        "version": result.stdout.strip(),
                        "source": "pacman"
                    }
            except Exception as e:
                logger.debug(f"pacman failed: {e}")

        elif distro == "alpine" and shutil.which("apk"):
            try:
                result = subprocess.run(["apk", "info", tool_name], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return {
                        "status": "success",
                        "message": f"Version info for {tool_name} (APK)",
                        "version": result.stdout.strip(),
                        "source": "apk"
                    }
            except Exception as e:
                logger.debug(f"apk failed: {e}")

        return {
            "status": "error",
            "message": f"Could not determine version for {tool_name}",
            "details": "Tool is installed, but no supported version method succeeded."
        }

    except Exception as e:
        logger.error(f"Exception while checking version for {tool_name}: {e}")
        return {
            "status": "error",
            "message": f"Error checking version for {tool_name}",
            "details": str(e)
        }

# Compatibility wrapper
def version_tool_linux(tool_name: str, version: str = "latest") -> dict:
    return check_version(tool_name, version)
