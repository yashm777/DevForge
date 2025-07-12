import shutil
import subprocess
import logging
from tools.utils.os_utils import get_linux_distro, is_snap_available
from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_snap_version(tool_name):
    if not is_snap_available():
        return None

    try:
        snap_list = subprocess.run(
            ["snap", "list", tool_name],
            capture_output=True, text=True, timeout=5
        )
        if snap_list.returncode != 0 or "error:" in snap_list.stderr.lower():
            return None

        lines = snap_list.stdout.strip().splitlines()
        if len(lines) < 2:
            return None

        parts = lines[1].split()
        if len(parts) < 2:
            return None

        version = parts[1]
        return {
            "version": version,
            "source": "snap"
        }
    except Exception as e:
        logger.debug(f"Snap version check failed: {e}")
        return None

def check_version(tool_name: str, version: str = "latest") -> dict:
    try:
        resolved = resolve_tool_name(tool_name, "linux", version)
        resolved_name = resolved.get("name", tool_name)

        # First check using shutil.which
        if shutil.which(resolved_name):
            version_commands = [
                [resolved_name, "--version"],
                [resolved_name, "-v"],
                [resolved_name, "-V"],
                [resolved_name, "version"]
            ]
            for cmd in version_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    output = (result.stdout + result.stderr).strip()
                    if result.returncode == 0 and output:
                        return {
                            "status": "success",
                            "message": f"Version information for {tool_name}",
                            "version": output,
                            "command": " ".join(cmd),
                            "source": "executable"
                        }
                except Exception as e:
                    logger.debug(f"Command {cmd} failed: {e}")

        # Check snap
        snap_version = check_snap_version(resolved_name)
        if snap_version:
            return {
                "status": "success",
                "message": f"{tool_name} found as snap package '{resolved_name}' version {snap_version['version']}",
                "version": snap_version["version"],
                "source": "snap"
            }

        # Distro-specific package manager fallback
        distro = get_linux_distro()
        if distro in ("debian", "ubuntu") and shutil.which("dpkg"):
            try:
                result = subprocess.run(["dpkg", "-l", resolved_name], capture_output=True, text=True, timeout=5)
                for line in result.stdout.strip().splitlines():
                    if line.startswith('ii') and resolved_name in line:
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
                result = subprocess.run(["rpm", "-q", resolved_name], capture_output=True, text=True, timeout=5)
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
                result = subprocess.run(["pacman", "-Q", resolved_name], capture_output=True, text=True, timeout=5)
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
                result = subprocess.run(["apk", "info", resolved_name], capture_output=True, text=True, timeout=5)
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
            "details": "Tool is not installed or no supported version method succeeded."
        }

    except Exception as e:
        logger.error(f"Exception while checking version for {tool_name}: {e}")
        return {
            "status": "error",
            "message": f"Error checking version for {tool_name}",
            "details": str(e)
        }
