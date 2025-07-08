import subprocess
import shutil
import logging
from tools.utils.os_utils import (
    get_os_type,
    get_available_package_manager,
    is_sudo_available
)
from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_sudo_access() -> bool:
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Sudo check failed: {e}")
        return False

def run_commands(command_list: list[list[str]]) -> subprocess.CompletedProcess | None:
    for cmd in command_list:
        logger.info(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return None
        if result.returncode != 0:
            logger.warning(f"Command failed: {' '.join(cmd)}\nError: {result.stderr.strip()}")
            return result
    return result  # last command's result

def is_tool_installed(tool: str) -> bool:
    return shutil.which(tool) is not None

def is_snap_available() -> bool:
    return shutil.which("snap") is not None

def build_install_command(manager: str, package: str) -> list[list[str]]:
    match manager:
        case "apt":
            return [["sudo", "apt-get", "update"], ["sudo", "apt-get", "install", "-y", package]]
        case "dnf":
            return [["sudo", "dnf", "install", "-y", package]]
        case "pacman":
            return [["sudo", "pacman", "-Sy", "--noconfirm", package]]
        case "apk":
            return [["sudo", "apk", "add", package]]
        case _:
            return []

def install_with_package_manager(tool: str, resolved_tool: str, manager: str, fallback_msg: str | None = None) -> dict:
    raw_cmds = build_install_command(manager, tool)
    raw_result = run_commands(raw_cmds)
    if raw_result and raw_result.returncode == 0:
        return {
            "status": "success",
            "message": f"Installed '{tool}' via {manager}.",
            "stdout": raw_result.stdout.strip(),
            "warnings": raw_result.stderr.strip() or None
        }

    logger.warning(f"Raw install failed for '{tool}': {raw_result.stderr.strip() if raw_result else 'Unknown error'}")

    if resolved_tool != tool:
        resolved_cmds = build_install_command(manager, resolved_tool)
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

    return None

def build_snap_install_command(package: str, classic=False) -> list[list[str]]:
    cmd = ["sudo", "snap", "install", package]
    if classic:
        cmd.append("--classic")
    return [cmd]

def install_with_snap(resolved_tool: str, classic_snap: bool = False, fallback_msg: str | None = None) -> dict:
    if not is_snap_available():
        snap_install_result = ensure_package_manager_installed("snap")
        if not snap_install_result:
            return {"status": "error", "message": "Snap is not installed and automatic installation failed."}

    snap_cmd = build_snap_install_command(resolved_tool, classic=classic_snap)
    snap_result = run_commands(snap_cmd)

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

def ensure_package_manager_installed(manager: str) -> bool:
    if shutil.which(manager):
        logger.info(f"Package manager '{manager}' is already installed.")
        return True

    logger.info(f"Package manager '{manager}' is missing. Attempting to install it...")

    os_type = get_os_type()
    try:
        if os_type == "linux":
            if manager == "apt":
                logger.error("APT is missing. Please install it manually.")
                return False
            if manager == "dnf":
                logger.error("DNF is missing. Please install it manually.")
                return False
            if manager == "pacman":
                logger.error("Pacman is missing. Please install it manually.")
                return False
            if manager == "apk":
                logger.error("APK is missing. Please install it manually.")
                return False
            if manager == "snap":
                if shutil.which("apt-get"):
                    subprocess.run(["sudo", "apt-get", "update"], capture_output=True, text=True, check=False)
                    result = subprocess.run(["sudo", "apt-get", "install", "-y", "snapd"], capture_output=True, text=True, check=False)
                    if result.returncode == 0:
                        logger.info("snapd installed successfully.")
                        return True
                logger.error("Failed to install snapd. Please install it manually.")
                return False

        elif os_type == "mac":
            if manager == "brew":
                logger.error("Homebrew is missing. Please install it manually from https://brew.sh/")
                return False

        elif os_type == "windows":
            if manager == "winget":
                logger.error("winget is missing. Please install it manually from Microsoft Store.")
                return False

        else:
            logger.error(f"Unsupported OS for package manager installation: {os_type}")
            return False

    except Exception as e:
        logger.error(f"Exception while installing package manager '{manager}': {e}")
        return False

    return False

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

    # Snap fallback: only try if snap is available or can be installed
    if is_snap_available() or ensure_package_manager_installed("snap"):
        snap_result = install_with_snap(resolved_tool, classic_snap, fallback_msg)
        if snap_result["status"] == "success":
            return snap_result
        else:
            # Both package manager and snap failed
            logger.error(f"Installation failed via both package manager '{manager}' and snap for '{tool}'.")
            return {
                "status": "error",
                "message": f"Installation failed for '{tool}' using both package manager '{manager}' and snap.",
                "details": snap_result.get("stderr")
            }

    return {
        "status": "error",
        "message": "Neither the package manager nor snap is available for installation."
    }
