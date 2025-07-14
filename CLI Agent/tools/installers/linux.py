import subprocess
import shutil
import logging
from tools.utils.os_utils import (
    get_os_type,
    get_available_package_manager,
    is_sudo_available,
    is_snap_available,
    check_sudo_access,
    ensure_package_manager_installed,
    is_tool_installed,
    run_commands
)
from tools.utils.name_resolver import resolve_tool_name
from llm_parser.parser import generate_smart_tool_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_install_command(manager: str, package: str) -> list[list[str]]:
    if manager == "apt":
        return [["sudo", "apt-get", "update"], ["sudo", "apt-get", "install", "-y", package]]
    elif manager == "dnf":
        return [["sudo", "dnf", "install", "-y", package]]
    elif manager == "pacman":
        return [["sudo", "pacman", "-Sy", "--noconfirm", package]]
    elif manager == "apk":
        return [["sudo", "apk", "add", package]]
    else:
        return []


def install_with_package_manager(tool: str, resolved_tool: str, manager: str, fallback_msg: str | None = None) -> dict | None:
    # Always try resolved_tool first
    resolved_cmds = build_install_command(manager, resolved_tool)
    logger.info(f"Trying to install resolved package '{resolved_tool}' using {manager}")
    resolved_result = run_commands(resolved_cmds)

    if resolved_result and resolved_result.returncode == 0:
        message = f"Installed '{resolved_tool}' via {manager}."
        if fallback_msg:
            message = f"{fallback_msg}\n{message}"
        return {
            "status": "success",
            "message": message,
            "stdout": resolved_result.stdout.strip(),
            "warnings": resolved_result.stderr.strip() or None
        }

    logger.warning(f"Resolved install failed for '{resolved_tool}': {resolved_result.stderr.strip() if resolved_result else 'Unknown error'}")

    # Only try raw tool name if it's different from resolved
    if resolved_tool != tool:
        raw_cmds = build_install_command(manager, tool)
        logger.info(f"Falling back to install raw tool '{tool}' using {manager}")
        raw_result = run_commands(raw_cmds)

        if raw_result and raw_result.returncode == 0:
            return {
                "status": "success",
                "message": f"Installed '{tool}' via {manager} (fallback).",
                "stdout": raw_result.stdout.strip(),
                "warnings": raw_result.stderr.strip() or None
            }

        logger.warning(f"Raw install failed for '{tool}': {raw_result.stderr.strip() if raw_result else 'Unknown error'}")

    return None



def build_snap_install_command(package: str, classic: bool = False) -> list[list[str]]:
    cmd = ["sudo", "snap", "install", package]
    if classic:
        cmd.append("--classic")
    return [cmd]


def install_with_snap(resolved_tool: str, classic_snap: bool = False, fallback_msg: str | None = None) -> dict:
    if not is_snap_available():
        snap_install_result = ensure_package_manager_installed("snap")
        if not snap_install_result:
            return {
                "status": "error",
                "message": "Snap is not installed and automatic installation failed."
            }

    snap_cmds = build_snap_install_command(resolved_tool, classic=classic_snap)
    snap_result = run_commands(snap_cmds)

    if snap_result and snap_result.returncode == 0:
        message = f"Installed '{resolved_tool}' via snap."
        if fallback_msg:
            message = f"{fallback_msg}\n{message}"
        return {
            "status": "success",
            "message": message,
            "stdout": snap_result.stdout.strip(),
            "warnings": snap_result.stderr.strip() or None
        }

    err_detail = snap_result.stderr.strip() if snap_result and snap_result.stderr else "No error details available."
    logger.error(f"Snap install failed for '{resolved_tool}': {err_detail}")

    return {
        "status": "error",
        "message": f"Snap install failed for '{resolved_tool}'. See logs for details.",
        "stderr": err_detail
    }


def install_linux_tool(tool: str, version: str = "latest") -> dict:
    if not is_sudo_available():
        return {
            "status": "error",
            "message": "sudo command is not available. Please install sudo or run as root."
        }

    if not check_sudo_access():
        return {
            "status": "error",
            "message": "sudo access required. Run: `sudo -v` and try again."
        }

    if is_tool_installed(tool):
        return {
            "status": "skipped",
            "message": f"'{tool}' is already installed on the system."
        }

    os_type = get_os_type()
    manager = get_available_package_manager()
    resolved = resolve_tool_name(tool, os_type, version)

    resolved_tool = resolved.get("name", tool)
    fallback_msg = resolved.get("fallback")
    classic_snap = resolved.get("classic_snap", False)

    if manager and manager != "unknown":
        if not ensure_package_manager_installed(manager):
            return {
                "status": "error",
                "message": f"Required package manager '{manager}' is not available and could not be installed automatically. Please install it manually."
            }

        result = install_with_package_manager(tool, resolved_tool, manager, fallback_msg)
        if result:
            return result

    if is_snap_available() or ensure_package_manager_installed("snap"):
        snap_result = install_with_snap(resolved_tool, classic_snap, fallback_msg)
        if snap_result["status"] == "success":
            return snap_result
        else:
            website_hint = generate_smart_tool_url(resolved_tool)
            return {
                "status": "error",
                "message": f"Installation failed for '{tool}' using both package manager '{manager}' and snap.\nManual installation guide: {website_hint}",
                "details": snap_result.get("stderr"),
                "manual_url": website_hint
            }

    manual_link = generate_smart_tool_url(tool)
    return {
        "status": "error",
        "message": f"Neither the package manager nor snap is available for installation.\nManual installation guide: {manual_link}",
        "manual_url": manual_link
    }
