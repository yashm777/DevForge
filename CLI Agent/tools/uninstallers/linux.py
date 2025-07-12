import subprocess
import shutil
import logging
from tools.utils.name_resolver import resolve_tool_name
from tools.utils.os_utils import get_available_package_manager, is_sudo_available, is_snap_available

logger = logging.getLogger(__name__)

def is_snap_installed(tool: str) -> bool:
    try:
        result = subprocess.run(["snap", "list", tool], capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and tool in result.stdout
    except Exception as e:
        logger.debug(f"Snap list check failed for {tool}: {e}")
        return False

def is_tool_installed(tool: str) -> bool:
    # Check PATH
    if shutil.which(tool):
        return True
    # Check snap
    if is_snap_installed(tool):
        return True
    return False

def is_uninstall_successful(result: subprocess.CompletedProcess | None) -> bool:
    if not result or result.returncode != 0:
        return False

    combined_output = f"{result.stdout.strip()} {result.stderr.strip()}".lower()
    error_signals = [
        "not installed",
        "unable to locate package",
        "no such snap",
        "package not found",
        "is not installed",
        "is not installed, so not removed"
    ]

    if any(err in combined_output for err in error_signals):
        return False

    return True

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

    # Early validation: refuse to uninstall if tool not installed
    if not is_tool_installed(tool):
        return {
            "status": "error",
            "message": f"'{tool}' does not appear to be installed. Cannot uninstall."
        }

    pkg_manager = get_available_package_manager()
    if pkg_manager == "unknown":
        return {
            "status": "error",
            "message": "No supported package manager found on this system."
        }

    # Try uninstall raw tool name first
    result = run_uninstall_cmd(tool, pkg_manager)
    if is_uninstall_successful(result):
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
        # Also validate resolved tool is installed
        if not is_tool_installed(resolved_tool):
            return {
                "status": "error",
                "message": f"Resolved tool '{resolved_tool}' does not appear to be installed. Cannot uninstall."
            }

        result = run_uninstall_cmd(resolved_tool, pkg_manager)
        if is_uninstall_successful(result):
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
        if is_uninstall_successful(snap_result):
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
