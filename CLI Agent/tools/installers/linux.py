import subprocess
import shutil
import platform
import logging
from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_sudo_access():
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Sudo check failed: {e}")
        return False

def get_package_manager():
    if shutil.which("apt-get"):
        return "apt"
    elif shutil.which("dnf"):
        return "dnf"
    elif shutil.which("pacman"):
        return "pacman"
    elif shutil.which("apk"):
        return "apk"
    return None

def build_install_command(manager, package):
    if manager == "apt":
        return [["sudo", "apt-get", "update"], ["sudo", "apt-get", "install", "-y", package]]
    elif manager == "dnf":
        return [["sudo", "dnf", "install", "-y", package]]
    elif manager == "pacman":
        return [["sudo", "pacman", "-Sy", "--noconfirm", package]]
    elif manager == "apk":
        return [["sudo", "apk", "add", package]]
    return []

def run_commands(command_list):
    for cmd in command_list:
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return result
    return result

def install_linux_tool(tool, version="latest"):
    if not check_sudo_access():
        return {
            "status": "error",
            "message": "sudo access required. Run: `sudo -v` and try again."
        }

    package_manager = get_package_manager()
    if not package_manager:
        return {"status": "error", "message": "Unsupported Linux package manager."}

    # --- Step 1: Try installing using the raw tool name ---
    raw_cmds = build_install_command(package_manager, tool)
    result_raw = run_commands(raw_cmds)

    if result_raw and result_raw.returncode == 0:
        return {
            "status": "success",
            "message": f"Installed '{tool}' successfully.",
            "stdout": result_raw.stdout.strip(),
            "warnings": result_raw.stderr.strip() or None
        }

    logger.warning(f"Raw install failed for '{tool}': {result_raw.stderr.strip()}")

    # --- Step 2: Resolve proper name and retry ---
    os_type = platform.system().lower()
    resolved = resolve_tool_name(tool, os_type, version)
    resolved_tool = resolved.get("name", tool)
    fallback_msg = resolved.get("fallback")

    if resolved_tool == tool:
        # Same name, no point in retrying
        return {
            "status": "error",
            "message": f"Installation failed for '{tool}'. Error: {result_raw.stderr.strip() or result_raw.stdout.strip()}"
        }

    logger.info(f"Trying resolved name: {resolved_tool}")
    resolved_cmds = build_install_command(package_manager, resolved_tool)
    result_resolved = run_commands(resolved_cmds)

    if result_resolved and result_resolved.returncode == 0:
        message = f"Installed '{resolved_tool}' successfully."
        if fallback_msg:
            message = f"{fallback_msg}\n{message}"
        return {
            "status": "success",
            "message": message,
            "stdout": result_resolved.stdout.strip(),
            "warnings": result_resolved.stderr.strip() or None
        }

    return {
        "status": "error",
        "message": f"Installation failed for both '{tool}' and resolved name '{resolved_tool}'.",
        "stderr": result_resolved.stderr.strip() if result_resolved else None
    }
