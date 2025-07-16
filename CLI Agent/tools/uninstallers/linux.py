import subprocess
import logging
import shutil
import os

from tools.utils.os_utils import (
    get_os_type,
    get_linux_distro,
    get_available_package_manager,
    is_sudo_available,
    is_snap_available,
    get_related_packages,
)
from tools.utils.name_resolver import resolve_tool_name

logger = logging.getLogger(__name__)


def run_uninstall_cmd(tool_name: str, manager: str) -> bool:
    try:
        cmd_map = {
            "apt": ["sudo", "apt-get", "purge", "-y", tool_name],
            "dnf": ["sudo", "dnf", "remove", "-y", tool_name],
            "pacman": ["sudo", "pacman", "-R", "--noconfirm", tool_name],
            "apk": ["sudo", "apk", "del", tool_name],
        }
        cmd = cmd_map.get(manager)
        if not cmd:
            logger.error(f"Unsupported package manager: {manager}")
            return False

        logger.info(f"Running uninstall command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            logger.warning(f"Uninstall failed: {result.stderr.strip()}")
            return False

    except Exception as e:
        logger.error(f"Exception during uninstall: {e}")
        return False


def uninstall_with_snap(tool_name: str) -> bool:
    try:
        if not is_snap_available():
            return False

        result = subprocess.run(["snap", "list"], capture_output=True, text=True)
        if tool_name not in result.stdout:
            return False

        cmd = ["sudo", "snap", "remove", tool_name]
        logger.info(f"Trying snap uninstall: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Snap uninstall failed: {e}")
        return False


def clean_java_jvm_dirs() -> list:
    removed = []
    jvm_path = "/usr/lib/jvm"
    if os.path.exists(jvm_path):
        for entry in os.listdir(jvm_path):
            full_path = os.path.join(jvm_path, entry)
            if any(k in entry.lower() for k in ("jdk", "jre", "java")):
                try:
                    subprocess.run(["sudo", "rm", "-rf", full_path])
                    removed.append(full_path)
                    logger.info(f"Removed JVM directory: {full_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove JVM dir {full_path}: {e}")
    return removed


def clean_java_symlinks():
    java_bin = shutil.which("java")
    if java_bin:
        try:
            subprocess.run(["sudo", "rm", "-f", java_bin])
            logger.info(f"Removed java symlink at {java_bin}")
        except Exception as e:
            logger.warning(f"Failed to remove java symlink: {e}")


def uninstall_tool_linux(raw_tool: str, version: str = "latest") -> dict:
    if not is_sudo_available():
        return {"status": "error", "message": "Sudo required. Please run `sudo -v`."}

    pkg_manager = get_available_package_manager()
    if pkg_manager == "unknown":
        return {"status": "error", "message": "No supported package manager found."}

    resolved = resolve_tool_name(raw_tool, "linux", version, context="install")
    resolved_name = resolved.get("name", raw_tool)

    related_packages = get_related_packages(resolved_name, pkg_manager)
    logger.info(f"Detected related packages for '{raw_tool}': {related_packages}")

    success = []
    failed = []

    if related_packages:
        for pkg in related_packages:
            if run_uninstall_cmd(pkg, pkg_manager):
                success.append(pkg)
            else:
                failed.append(pkg)
    else:
        # No related packages detected, try directly
        if run_uninstall_cmd(resolved_name, pkg_manager):
            success.append(resolved_name)
        elif uninstall_with_snap(resolved_name):
            success.append(resolved_name)
        else:
            failed.append(resolved_name)

    # Java special cleanup
    if raw_tool.lower() == "java":
        removed_paths = clean_java_jvm_dirs()
        clean_java_symlinks()
        extra_hint = (
            "\nNote: For complete removal, consider running "
            "`sudo apt-get purge openjdk-<version>-jre:amd64` manually "
            "if any versions still remain."
        )
        return {
            "status": "success" if success else "error",
            "message": (
                f"Removed Java components: {success}. JVM dirs cleaned: {removed_paths}."
                + (extra_hint if success else "")
            ),
            "removed_dirs": removed_paths,
            "uninstalled_packages": success,
            "failed_packages": failed
        }

    if success:
        return {
            "status": "success",
            "message": f"Uninstalled: {', '.join(success)}",
            "uninstalled_packages": success,
            "failed_packages": failed
        }
    else:
        return {
            "status": "error",
            "message": f"Failed to uninstall any packages for '{raw_tool}'",
            "failed_packages": failed
        }
