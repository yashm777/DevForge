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

    except subprocess.TimeoutExpired:
        logger.error(f"Uninstallation timed out for {tool_name}")
        return None
    except Exception as e:
        logger.error(f"Uninstallation failed for {tool_name}: {e}")
        return None

def uninstall_with_snap(tool_name: str) -> subprocess.CompletedProcess | None:
    try:
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

    # Try uninstall raw tool name first
    result = run_uninstall_cmd(tool, pkg_manager)
    if result and result.returncode == 0:
        logger.info(f"Successfully uninstalled '{tool}' using package manager '{pkg_manager}'.")
        return {
            "status": "success",
            "message": f"Uninstalled '{tool}' successfully.",
            "stdout": result.stdout.strip()
        }

    # Try resolved tool name
    resolved = resolve_tool_name(tool, "linux", version)
    resolved_tool = resolved.get("name", tool)
    fallback_msg = resolved.get("fallback")

    if resolved_tool != tool:
        result = run_uninstall_cmd(resolved_tool, pkg_manager)
        if result and result.returncode == 0:
            msg = f"Uninstalled '{resolved_tool}' successfully."
            if fallback_msg:
                msg += f"\nNote: {fallback_msg}"
            logger.info(msg)
            return {
                "status": "success",
                "message": msg,
                "stdout": result.stdout.strip()
            }

    # If both fail, try snap uninstall if snap is available
    if is_snap_available():
        snap_result = uninstall_with_snap(resolved_tool)
        if snap_result and snap_result.returncode == 0:
            logger.info(f"Successfully uninstalled '{resolved_tool}' via snap.")
            return {
                "status": "success",
                "message": f"Uninstalled '{resolved_tool}' successfully via snap.",
                "stdout": snap_result.stdout.strip()
            }

    # All uninstall attempts failed
    error_detail = ""
    if result:
        error_detail = result.stderr.strip() or result.stdout.strip()
    else:
        error_detail = "Uninstallation commands did not execute successfully."

    logger.error(f"Uninstallation failed for '{tool}' and '{resolved_tool}'. Details: {error_detail}")

    return {
        "status": "error",
        "message": f"Failed to uninstall '{tool}' and '{resolved_tool}'.",
        "stderr": error_detail
    }
