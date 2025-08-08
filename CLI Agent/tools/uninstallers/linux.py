import subprocess
import shutil
import logging
import os
from tools.utils.name_resolver import resolve_tool_name, SDKMAN_TOOLS
from tools.utils.os_utils import (
    get_linux_distro,
    get_available_package_manager,
    is_sudo_available,
    is_snap_available,
)

logger = logging.getLogger(__name__)

def is_package_installed(pkg_name: str, pkg_manager: str) -> bool:
    try:
        if pkg_manager == "apt":
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", pkg_name],
                capture_output=True, text=True
            )
            return "install ok installed" in result.stdout
        elif pkg_manager == "snap":
            result = subprocess.run(
                ["snap", "list", pkg_name],
                capture_output=True, text=True
            )
            return pkg_name in result.stdout
        return True  
    except Exception as e:
        logger.warning(f"Failed to check if {pkg_name} is installed: {e}")
        return False

def run_uninstall_cmd(tool_name: str, manager: str) -> bool:
    try:
        if manager == "apt":
            cmd = ["apt-get", "purge", "-y", tool_name]
        elif manager == "snap" and is_snap_available():
            cmd = ["snap", "remove", tool_name]
        else:
            logger.warning(f"Unsupported or unavailable package manager: {manager}")
            return False

        if is_sudo_available():
            cmd.insert(0, "sudo")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"{tool_name} uninstalled successfully.")
            return True
        else:
            logger.error(f"Failed to uninstall {tool_name}: {result.stderr.strip() or result.stdout.strip()}")
            return False
    except Exception as e:
        logger.exception(f"Exception during uninstall: {e}")
        return False

def is_sdkman_available() -> bool:
    return shutil.which("sdk") is not None or os.path.exists(os.path.expanduser("~/.sdkman/bin/sdk"))

def uninstall_with_sdkman(candidate: str, version: str = None) -> dict:
    try:
        cmd = ["sdk", "uninstall", candidate]
        if version and version != "latest":
            cmd.append(version)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": f"Uninstalled {candidate} {version or ''} via SDKMAN!".strip()}
        else:
            return {"status": "error", "message": result.stderr or result.stdout}
    except Exception as e:
        return {"status": "error", "message": f"SDKMAN! uninstall failed: {e}"}

def uninstall_linux_tool(tool: str, version: str | None = None):
    success, failed = []

    distro = get_linux_distro()
    pkg_manager = get_available_package_manager()

    if not pkg_manager:
        return {"status": "error", "message": "No supported package manager found."}

    resolved = resolve_tool_name(tool, "linux", context="uninstall", version=version)
    pkg_name = resolved["name"]
    logger.info(f"Resolved uninstall package: {pkg_name}")

    # --- SDKMAN! support for specific tools ---
    sdkman_candidate = resolved.get("sdkman_candidate") or SDKMAN_TOOLS.get(tool.lower())
    if sdkman_candidate and is_sdkman_available():
        sdkman_result = uninstall_with_sdkman(sdkman_candidate, version)
        if sdkman_result["status"] == "success":
            return sdkman_result
        else:
            logger.warning(f"SDKMAN! uninstall failed or not found for {sdkman_candidate}, falling back to system package managers.")

    # Generic uninstall for all other tools (including non-SDKMAN! Java)
    if is_package_installed(pkg_name, pkg_manager):
        if run_uninstall_cmd(pkg_name, pkg_manager):
            success.append(pkg_name)
        else:
            failed.append(pkg_name)
    else:
        logger.info(f"{pkg_name} is not installed. Skipping.")
        failed.append(pkg_name)

    if failed:
        return {
            "status": "partial" if success else "error",
            "message": f"Uninstall finished. Success: {success}. Failed: {failed}"
        }
    else:
        return {
            "status": "success",
            "message": f"Uninstalled: {success}" if success else f"Nothing to uninstall. Packages not found."
        }
