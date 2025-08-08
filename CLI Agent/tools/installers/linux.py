import subprocess
import shutil
import logging
import os
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
from tools.utils.name_resolver import resolve_tool_name, SDKMAN_TOOLS
from llm_parser.parser import generate_smart_tool_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_install_command(manager: str, package: str) -> list[list[str]]:
    logger.info(f"Building install command for manager '{manager}' and package '{package}'")
    if manager == "apt":
        return [["sudo", "apt-get", "update"], ["sudo", "apt-get", "install", "-y", package]]
    else:
        logger.warning(f"Unsupported package manager '{manager}'")
        return []


def install_with_package_manager(tool: str, resolved_tool: str, manager: str, fallback_msg: str | None = None) -> dict | None:
    logger.info(f"install_with_package_manager called with tool='{tool}', resolved_tool='{resolved_tool}', manager='{manager}'")
    resolved_cmds = build_install_command(manager, resolved_tool)
    logger.info(f"Trying to install resolved package '{resolved_tool}' using {manager} with commands: {resolved_cmds}")
    resolved_result = run_commands(resolved_cmds)

    if resolved_result and resolved_result.returncode == 0:
        message = f"Installed '{resolved_tool}' via {manager}."
        if fallback_msg:
            message = f"{fallback_msg}\n{message}"
        logger.info(f"Successfully installed '{resolved_tool}' via {manager}")
        return {
            "status": "success",
            "message": message,
            "warnings": resolved_result.stderr.strip() or None
        }

    logger.warning(f"Resolved install failed for '{resolved_tool}': {resolved_result.stderr.strip() if resolved_result else 'Unknown error'}")
    return None


def build_snap_install_command(package: str, classic: bool = False) -> list[list[str]]:
    logger.info(f"Building snap install command for package '{package}' with classic={classic}")
    cmd = ["sudo", "snap", "install", package]
    if classic:
        cmd.append("--classic")
    return [cmd]


def install_with_snap(resolved_tool: str, classic_snap: bool = False, fallback_msg: str | None = None) -> dict:
    logger.info(f"install_with_snap called with resolved_tool='{resolved_tool}', classic_snap={classic_snap}")
    if not is_snap_available():
        logger.info("Snap not available. Attempting to install snap.")
        snap_install_result = ensure_package_manager_installed("snap")
        if not snap_install_result:
            logger.error("Snap is not installed and automatic installation failed.")
            return {
                "status": "error",
                "message": "Snap is not installed and automatic installation failed."
            }

    snap_cmds = build_snap_install_command(resolved_tool, classic=classic_snap)
    logger.info(f"Running snap install commands: {snap_cmds}")
    snap_result = run_commands(snap_cmds)

    if snap_result and snap_result.returncode == 0:
        message = f"Installed '{resolved_tool}' via snap."
        if fallback_msg:
            message = f"{fallback_msg}\n{message}"
        logger.info(f"Successfully installed '{resolved_tool}' via snap")
        return {
            "status": "success",
            "message": message,
            "warnings": snap_result.stderr.strip() or None
        }

    err_detail = snap_result.stderr.strip() if snap_result and snap_result.stderr else "No error details available."
    logger.error(f"Snap install failed for '{resolved_tool}': {err_detail}")

    return {
        "status": "error",
        "message": f"Snap install failed for '{resolved_tool}'. See logs for details.",
        "stderr": err_detail
    }


def is_sdkman_available() -> bool:
    return shutil.which("sdk") is not None or os.path.exists(os.path.expanduser("~/.sdkman/bin/sdk"))


def ensure_curl_installed() -> bool:
    if shutil.which("curl"):
        return True
    logger.info("curl not found. Attempting to install curl.")
    manager = get_available_package_manager()
    if manager == "apt":
        subprocess.run(["sudo", "apt-get", "update"])
        result = subprocess.run(["sudo", "apt-get", "install", "-y", "curl"])
    else:
        logger.error("No supported package manager found to install curl.")
        return False
    return result.returncode == 0


def install_sdkman() -> bool:
    try:
        if not ensure_curl_installed():
            logger.error("curl is required to install SDKMAN! but could not be installed.")
            return False
        install_cmd = (
            'curl -s "https://get.sdkman.io" | bash && '
            'source "$HOME/.sdkman/bin/sdkman-init.sh"'
        )
        result = subprocess.run(install_cmd, shell=True, executable="/bin/bash")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Failed to install SDKMAN!: {e}")
        return False


def install_with_sdkman(candidate: str, version: str = "latest") -> dict:
    try:
        cmd = ["sdk", "install", candidate]
        if version and version != "latest":
            cmd.append(version)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": f"Installed {candidate} {version} via SDKMAN!"}
        else:
            return {"status": "error", "message": result.stderr or result.stdout}
    except Exception as e:
        return {"status": "error", "message": f"SDKMAN! install failed: {e}"}


def install_linux_tool(tool: str, version: str = "latest") -> dict:
    logger.info(f"install_linux_tool called with tool='{tool}', version='{version}'")

    if not is_sudo_available():
        logger.error("sudo command is not available")
        return {
            "status": "error",
            "message": "sudo command is not available. Please install sudo or run as root."
        }

    if not check_sudo_access():
        logger.error("sudo access check failed")
        return {
            "status": "error",
            "message": "sudo access required. Run: `sudo -v` and try again."
        }

    if is_tool_installed(tool):
        logger.info(f"Tool '{tool}' is already installed on the system")
        return {
            "status": "skipped",
            "message": f"'{tool}' is already installed on the system."
        }

    os_type = get_os_type()
    logger.info(f"Detected OS type: {os_type}")

    manager = get_available_package_manager()
    logger.info(f"Available package manager: {manager}")

    resolved = resolve_tool_name(tool, os_type, version)
    logger.info(f"Resolved tool name details: {resolved}")

    resolved_tool = resolved.get("name", tool)
    fallback_msg = resolved.get("fallback")
    classic_snap = resolved.get("classic_snap", False)

    # --- SDKMAN! support for specific tools ---
    sdkman_candidate = SDKMAN_TOOLS.get(tool.lower())
    if sdkman_candidate:
        sdkman_candidate = resolved.get("sdkman_candidate", sdkman_candidate)
        if not is_sdkman_available():
            logger.info("SDKMAN! not found. Attempting to install SDKMAN!")
            if not install_sdkman():
                logger.error("SDKMAN! installation failed.")
            else:
                logger.info("SDKMAN! installed successfully.")
        if is_sdkman_available():
            sdkman_result = install_with_sdkman(sdkman_candidate, version)
            if sdkman_result["status"] == "success":
                return sdkman_result

    # Only support apt and snap as package managers
    if manager == "apt":
        if not ensure_package_manager_installed(manager):
            logger.error(f"Package manager '{manager}' not available and could not be installed")
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
            logger.error(f"Installation failed for '{tool}' using both package manager '{manager}' and snap.")
            return {
                "status": "error",
                "message": f"Installation failed for '{tool}' using both package manager '{manager}' and snap.\nManual installation guide: {website_hint}",
                "details": snap_result.get("stderr"),
                "manual_url": website_hint
            }

    manual_link = generate_smart_tool_url(tool)
    logger.error(f"Neither the package manager nor snap is available for installation for tool '{tool}'.")
    return {
        "status": "error",
        "message": f"Neither the package manager nor snap is available for installation.\nManual installation guide: {manual_link}",
        "manual_url": tool
    }
