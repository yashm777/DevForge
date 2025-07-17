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


def detect_installed_java_packages() -> list:
    """
    Detect installed Java-related packages on Debian/Ubuntu using dpkg-query.
    Returns a list of package names.
    """
    try:
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${binary:Package}\n"],
            capture_output=True, text=True, check=True
        )
        installed = [line.strip() for line in result.stdout.splitlines()]
        java_pkgs = [pkg for pkg in installed if "openjdk" in pkg or "default-jdk" in pkg or "oracle-java" in pkg]
        logger.info(f"Detected installed Java packages: {java_pkgs}")
        return java_pkgs
    except Exception as e:
        logger.warning(f"Failed to detect installed Java packages: {e}")
        return []


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

    # Enhanced Java package detection: find both JDK and JRE packages installed
    if raw_tool.lower() == "java":
        # Additional JRE packages to detect and remove
        jre_packages = []
        try:
            if pkg_manager == "apt":
                # Query installed jre packages matching patterns
                dpkg_query_cmd = [
                    "dpkg-query", "-W", "-f=${Package}\n",
                    "openjdk-*-jre", "default-jre*"
                ]
                result = subprocess.run(dpkg_query_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    jre_packages = [pkg for pkg in result.stdout.splitlines() if pkg.strip()]
                    logger.info(f"Detected installed JRE packages: {jre_packages}")
            # You can add support for other package managers here if needed
        except Exception as e:
            logger.warning(f"Failed to query JRE packages: {e}")

        # Combine JDK and JRE packages for uninstall
        combined_packages = set(related_packages) | set(jre_packages)
        success = []
        failed = []

        for pkg in combined_packages:
            if run_uninstall_cmd(pkg, pkg_manager):
                success.append(pkg)
            else:
                failed.append(pkg)

        removed_paths = clean_java_jvm_dirs()
        clean_java_symlinks()

        extra_hint = (
            "\nNote: For complete removal, check if any Java versions remain with "
            "`dpkg --list | grep openjdk` and remove manually if needed."
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

    # Non-Java uninstall logic unchanged
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

