import shutil
import subprocess
import logging
from tools.utils.os_utils import get_linux_distro, is_snap_available
from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_java_versions_via_update_alternatives():
    try:
        result = subprocess.run(
            ["update-alternatives", "--list", "java"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        
        java_paths = result.stdout.strip().splitlines()
        versions = []
        active_path_result = subprocess.run(
            ["update-alternatives", "--query", "java"],
            capture_output=True, text=True, timeout=5
        )
        active_path = None
        for line in active_path_result.stdout.splitlines():
            if line.startswith("Value:"):
                active_path = line.split(":", 1)[1].strip()
                break

        for path in java_paths:
            try:
                ver_result = subprocess.run(
                    [path, "-version"],
                    capture_output=True, text=True, timeout=5
                )
                if ver_result.returncode == 0:
                    version_line = ver_result.stderr.splitlines()[0]
                    versions.append({
                        "path": path,
                        "version_info": version_line,
                        "is_active": (path == active_path)
                    })
            except Exception as e:
                logger.debug(f"Failed to get version for {path}: {e}")
        return versions
    except Exception as e:
        logger.debug(f"update-alternatives check failed: {e}")
        return None

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
        # Special case for Java via update-alternatives
        if tool_name.lower() in ["java", "jdk", "default-jdk"]:
            java_versions = check_java_versions_via_update_alternatives()
            if java_versions:
                versions_summary = []
                for v in java_versions:
                    mark = "(active)" if v["is_active"] else ""
                    versions_summary.append(f"{v['version_info']} at {v['path']} {mark}")
                return {
                    "status": "success",
                    "message": "Java versions found:\n" + "\n".join(versions_summary),
                    "versions": java_versions
                }
            else:
                distro = get_linux_distro()
                if distro in ("debian", "ubuntu") and shutil.which("dpkg"):
                    result = subprocess.run(["dpkg", "-l", tool_name], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and tool_name in result.stdout:
                        lines = result.stdout.strip().splitlines()
                        for line in lines:
                            if line.startswith('ii') and tool_name in line:
                                parts = line.split()
                                if len(parts) >= 3:
                                    return {
                                        "status": "success",
                                        "message": f"Version info for {tool_name} (APT)",
                                        "version": parts[2],
                                        "source": "apt/dpkg"
                                    }

        # If not installed on PATH, check snap
        if shutil.which(tool_name) is None:
            resolved = resolve_tool_name(tool_name, "linux", version)
            snap_name = resolved.get("name")
            snap_version = check_snap_version(snap_name)
            if snap_version:
                return {
                    "status": "success",
                    "message": f"{tool_name} found as snap package '{snap_name}' version {snap_version['version']}",
                    "version": snap_version["version"],
                    "source": "snap"
                }
            else:
                return {
                    "status": "error",
                    "message": f"'{tool_name}' is not installed or not found in PATH or snap."
                }

        # Try common version commands
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

        # Distro-specific version queries fallback
        distro = get_linux_distro()
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
