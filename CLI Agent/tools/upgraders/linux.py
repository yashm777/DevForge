import subprocess
import logging
import platform
from tools.utils.os_utils import get_linux_distro, get_available_package_manager, is_sudo_available, is_snap_available
from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_update_commands(distro, package_name, tool_name):
    """Return list of commands to update the given package for the distro."""
    if distro in ("ubuntu", "debian"):
        cmds = [["sudo", "apt-get", "update"]]
        if tool_name == "all":
            cmds.append(["sudo", "apt-get", "upgrade", "-y"])
        else:
            cmds.append(["sudo", "apt-get", "install", "--only-upgrade", "-y", package_name])
        return cmds

    elif distro in ("fedora", "centos", "rhel"):
        if tool_name == "all":
            return [["sudo", "dnf", "upgrade", "-y"]]
        else:
            return [["sudo", "dnf", "upgrade", "-y", package_name]]

    elif distro in ("arch", "manjaro"):
        cmds = [["sudo", "pacman", "-Sy"]]
        if tool_name == "all":
            cmds.append(["sudo", "pacman", "-Su", "--noconfirm"])
        else:
            cmds.append(["sudo", "pacman", "-S", "--noconfirm", package_name])
        return cmds

    elif distro == "alpine":
        cmds = [["sudo", "apk", "update"]]
        if tool_name == "all":
            cmds.append(["sudo", "apk", "upgrade"])
        else:
            cmds.append(["sudo", "apk", "add", "--upgrade", package_name])
        return cmds

    else:
        return []

def run_commands(commands):
    """Run list of commands sequentially, stop on failure."""
    for cmd in commands:
        logger.info(f"Running command: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return None

        if result.returncode != 0:
            logger.error(f"Command failed: {' '.join(cmd)}\nError: {result.stderr.strip()}")
            return result
    return result

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    if not is_sudo_available():
        return {
            "status": "error",
            "message": "sudo not found or unavailable. Please install sudo or run as root."
        }

    if not check_sudo_access():
        return {
            "status": "error",
            "message": "No sudo access without password prompt. Run `sudo -v` or check sudoers config."
        }

    distro = get_linux_distro()
    os_type = platform.system().lower()

    resolved = resolve_tool_name(tool_name, os_type, version)
    resolved_name = resolved.get("name", tool_name)
    fallback_msg = resolved.get("fallback")

    manager = get_available_package_manager()
    if not manager or manager == "unknown":
        return {
            "status": "error",
            "message": f"No supported package manager found on {distro}."
        }

    update_cmds = build_update_commands(distro, resolved_name, tool_name)
    if not update_cmds:
        return {
            "status": "error",
            "message": f"Unsupported Linux distribution: {distro}"
        }

    result = run_commands(update_cmds)
    if result and result.returncode == 0:
        msg = f"{resolved_name} updated successfully via {distro.capitalize()}."
        if fallback_msg:
            msg = f"{fallback_msg}\n{msg}"
        return {
            "status": "success",
            "message": msg,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip() or None,
            "distribution": distro
        }

    logger.warning(f"Package manager update failed for '{resolved_name}': {result.stderr.strip() if result else 'No output'}")

    # Try snap fallback if snap is available and the package likely is a snap package
    if is_snap_available():
        # This could be improved by linking with name_resolver's snap info or a dynamic snap package list
        try:
            snap_cmd = ["sudo", "snap", "refresh", resolved_name]
            logger.info(f"Trying snap update: {' '.join(snap_cmd)}")
            snap_result = subprocess.run(snap_cmd, capture_output=True, text=True)
            if snap_result.returncode == 0:
                msg = f"{resolved_name} updated successfully via snap."
                if fallback_msg:
                    msg = f"{fallback_msg}\n{msg}"
                return {
                    "status": "success",
                    "message": msg,
                    "stdout": snap_result.stdout.strip(),
                    "stderr": snap_result.stderr.strip() or None,
                    "distribution": "snap"
                }
            else:
                logger.error(f"Snap update failed: {snap_result.stderr.strip()}")
                return {
                    "status": "error",
                    "message": f"Failed to update {resolved_name} via snap.",
                    "details": snap_result.stderr.strip()
                }
        except Exception as e:
            logger.error(f"Unexpected error during snap update: {e}")
            return {
                "status": "error",
                "message": f"Unexpected error during snap update: {str(e)}"
            }

    return {
        "status": "error",
        "message": f"Failed to update {resolved_name} on {distro} and no suitable snap fallback.",
        "stderr": result.stderr.strip() if result else None
    }

# Legacy compatibility wrapper
def update_tool_linux(tool_name: str, version: str = "latest") -> dict:
    return handle_tool(tool_name, version)


def check_sudo_access():
    import subprocess
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Sudo check failed: {e}")
        return False
