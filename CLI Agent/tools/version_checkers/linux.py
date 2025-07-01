import shutil
import subprocess
import logging
from tools.os_utils import get_linux_distro

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_version(tool_name: str, version: str = "latest") -> dict:
    """
    Check the version of a tool on Linux.

    Args:
        tool_name (str): Name of the tool to check version for.
        version (str): Version parameter (not used for version check).

    Returns:
        dict: Status message and version information.
    """
    try:
        # Check if the tool is installed
        if shutil.which(tool_name) is None:
            return {
                "status": "error",
                "message": f"{tool_name} is not installed or not in PATH"
            }

        # Try different version command patterns
        version_commands = [
            [tool_name, "--version"],
            [tool_name, "-v"],
            [tool_name, "-V"],
            [tool_name, "version"]
        ]

        for cmd in version_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    version_output = result.stdout.strip()
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name}",
                        "version": version_output,
                        "command": " ".join(cmd)
                    }
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                continue

        # If no version command worked, try package managers
        distro = get_linux_distro()
        
        if distro in ("debian", "ubuntu") and shutil.which("dpkg"):
            try:
                dpkg_cmd = ["dpkg", "-l", tool_name]
                result = subprocess.run(dpkg_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    # Parse dpkg output to extract version
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if line.startswith('ii') and tool_name in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                return {
                                    "status": "success",
                                    "message": f"Version information for {tool_name} (APT)",
                                    "version": parts[2],
                                    "source": "apt"
                                }
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass

        elif distro in ("fedora", "centos", "rhel") and shutil.which("rpm"):
            try:
                rpm_cmd = ["rpm", "-q", tool_name]
                result = subprocess.run(rpm_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name} (RPM)",
                        "version": result.stdout.strip(),
                        "source": "rpm"
                    }
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass

        elif distro in ("arch", "manjaro") and shutil.which("pacman"):
            try:
                pacman_cmd = ["pacman", "-Q", tool_name]
                result = subprocess.run(pacman_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name} (Pacman)",
                        "version": result.stdout.strip(),
                        "source": "pacman"
                    }
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass

        elif distro == "alpine" and shutil.which("apk"):
            try:
                apk_cmd = ["apk", "info", tool_name]
                result = subprocess.run(apk_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name} (APK)",
                        "version": result.stdout.strip(),
                        "source": "apk"
                    }
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass

        return {
            "status": "error",
            "message": f"Could not determine version for {tool_name}",
            "details": "Tool is installed but version command failed"
        }

    except Exception as e:
        logger.error(f"Error checking version for {tool_name}: {e}")
        return {
            "status": "error",
            "message": f"Error checking version for {tool_name}",
            "details": str(e)
        }

# Legacy function for backward compatibility
def version_tool_linux(tool_name: str, version: str = "latest") -> dict:
    return check_version(tool_name, version) 