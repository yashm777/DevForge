import subprocess
import shutil
import logging
from tools.utils.name_resolver import resolve_tool_name

logging.basicConfig(level=logging.INFO)


def check_sudo_access():
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except Exception as e:
        logging.error(f"Sudo check failed: {e}")
        return False


def run_uninstall_cmd(tool_name):
    try:
        if shutil.which("apt-get"):
            cmd = ["sudo", "apt-get", "remove", "-y", tool_name]
        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "remove", "-y", tool_name]
        elif shutil.which("pacman"):
            cmd = ["sudo", "pacman", "-R", "--noconfirm", tool_name]
        elif shutil.which("apk"):
            cmd = ["sudo", "apk", "del", tool_name]
        else:
            logging.error("No supported package manager found.")
            return None
        
        logging.info(f"Running uninstall command: {' '.join(cmd)}")
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30)

    except subprocess.TimeoutExpired:
        logging.error(f"Uninstallation timed out for {tool_name}")
        return None
    except Exception as e:
        logging.error(f"Uninstallation failed for {tool_name}: {e}")
        return None


def uninstall_linux_tool(tool, version="latest"):
    if not check_sudo_access():
        return {
            "status": "error",
            "message": "Sudo access is required. Run: `sudo -v` before trying again."
        }

    # --- Step 1: Try uninstalling using the raw name ---
    first_try = run_uninstall_cmd(tool)
    if first_try and first_try.returncode == 0:
        logging.info(f"Successfully uninstalled '{tool}' using raw name.")
        return {
            "status": "success",
            "message": f"Uninstalled '{tool}' successfully.",
            "stdout": first_try.stdout.strip()
        }

    # --- Step 2: Try resolved tool name ---
    resolved = resolve_tool_name(tool, "linux", version)
    resolved_tool = resolved.get("name", tool)
    fallback_msg = resolved.get("fallback")

    if resolved_tool != tool:
        logging.info(f"Trying with resolved tool name: {resolved_tool}")
        second_try = run_uninstall_cmd(resolved_tool)
        if second_try and second_try.returncode == 0:
            logging.info(f"Successfully uninstalled '{resolved_tool}' using resolved name.")
            return {
                "status": "success",
                "message": f"Uninstalled '{resolved_tool}' successfully." + (f"\nNote: {fallback_msg}" if fallback_msg else ""),
                "stdout": second_try.stdout.strip()
            }

    # --- Step 3: Failure ---
    error_msg = (
        first_try.stderr.strip() if first_try and first_try.stderr
        else "Unknown error or unsupported package manager."
    )
    logging.error(f"Uninstallation failed for '{tool}' and '{resolved_tool}'. Error: {error_msg}")

    return {
        "status": "error",
        "message": f"Uninstallation failed for both '{tool}' and resolved name '{resolved_tool}'.",
        "stderr": error_msg
    }
