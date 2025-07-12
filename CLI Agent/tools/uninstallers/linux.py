import subprocess
import shutil
import logging
from tools.utils.name_resolver import resolve_tool_name
from tools.utils.os_utils import get_available_package_manager, is_sudo_available, is_snap_available

logger = logging.getLogger(__name__)


def run_uninstall_cmd(tool_name: str, manager: str) -> subprocess.CompletedProcess | None:
    try:
        cmd_map = {
            "apt": ["sudo", "apt-get", "remove", "-y", tool_name],
            "dnf": ["sudo", "dnf", "remove", "-y", tool_name],
            "pacman": ["sudo", "pacman", "-R", "--noconfirm", tool_name],
            "apk": ["sudo", "apk", "del", tool_name],
        }
        cmd = cmd_map.get(manager)
        if not cmd:
            logger.error(f"Unsupported package manager: {manager}")
            return None

        logger.info(f"Running uninstall command: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=True, text=True)

    except Exception as e:
        logger.error(f"Uninstallation failed for {tool_name}: {e}")
        return None


def uninstall_with_snap(tool_name: str) -> subprocess.CompletedProcess | None:
    try:
        list_cmd = ["snap", "list"]
        snap_list = subprocess.run(list_cmd, capture_output=True, text=True)
        if tool_name.lower() not in snap_list.stdout.lower():
            return None

        cmd = ["sudo", "snap", "remove", tool_name]
        logger.info(f"Trying snap uninstall: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        logger.error(f"Snap uninstall failed for {tool_name}: {e}")
        return None


def uninstall_linux_tool(tool: str, version: str = "latest") -> dict:
    if not is_sudo_available():
        return {
            "status": "error",
            "message": "Sudo access required. Please run `sudo -v` and try again."
        }

    pkg_manager = get_available_package_manager()
    if pkg_manager == "unknown":
        return {
            "status": "error",
            "message": "No supported package manager found on this system."
        }

    resolved = resolve_tool_name(tool, "linux", version)
    candidate_names = [resolved.get("name", tool)] + resolved.get("snap_alternatives", [])

    for name in candidate_names:
        result = run_uninstall_cmd(name, pkg_manager)
        if result and result.returncode == 0:
            logger.info(f"Successfully uninstalled '{name}' using '{pkg_manager}'")
            return {
                "status": "success",
                "message": f"Uninstalled '{name}' successfully via {pkg_manager}.",
                "stdout": result.stdout.strip()
            }

    if is_snap_available():
        for name in candidate_names:
            snap_result = uninstall_with_snap(name)
            if snap_result and snap_result.returncode == 0:
                logger.info(f"Successfully uninstalled '{name}' via snap.")
                return {
                    "status": "success",
                    "message": f"Uninstalled '{name}' successfully via snap.",
                    "stdout": snap_result.stdout.strip()
                }

    return {
        "status": "error",
        "message": f"Failed to uninstall '{tool}' using all known methods."
    }
