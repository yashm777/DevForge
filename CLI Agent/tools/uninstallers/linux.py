import subprocess
import shutil
import logging
from tools.utils.name_resolver import resolve_tool_name
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
        elif pkg_manager == "dnf":
            result = subprocess.run(
                ["dnf", "list", "installed", pkg_name],
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
        elif manager == "dnf":
            cmd = ["dnf", "remove", "-y", tool_name]
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

def get_related_packages(alternatives: list[str]) -> list[str]:
    """
    Given a list of java binary paths from alternatives,
    extract related package names like openjdk-17-jdk.
    """
    packages = set()
    for alt in alternatives:
        parts = alt.split("/")
        for p in parts:
            if "jdk" in p or "java" in p:
                packages.add(p)
    return list(packages)

def get_java_alternatives() -> list[str]:
    """
    Detect installed Java versions using `update-alternatives`.
    Returns a list of Java binary paths or identifiers.
    """
    try:
        result = subprocess.run(
            ["update-alternatives", "--list", "java"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return [line.strip() for line in result.stdout.splitlines()]
    except Exception:
        pass
    return []


def uninstall_linux_tool(tool: str, version: str | None = None):
    success, failed = [], []

    distro = get_linux_distro()
    pkg_manager = get_available_package_manager()

    if not pkg_manager:
        return {"status": "error", "message": "No supported package manager found."}

    resolved = resolve_tool_name(tool, "linux", context="uninstall", version=version)
    pkg_name = resolved["name"]
    logger.info(f"Resolved uninstall package: {pkg_name}")

    if pkg_name in ["openjdk", "default-jdk", "jdk", "java", "openjdk-17-jdk", "openjdk-21-jdk"]:
        alternatives = get_java_alternatives()
        packages = get_related_packages(alternatives)

        if version:
            version_filtered = [pkg for pkg in packages if version.replace(" ", "") in pkg.replace("-", "")]
            combined_packages = list(set(version_filtered + [pkg_name]))
        else:
            combined_packages = list(set(packages + [pkg_name]))

        for pkg in combined_packages:
            if is_package_installed(pkg, pkg_manager):
                if run_uninstall_cmd(pkg, pkg_manager):
                    success.append(pkg)
                else:
                    failed.append(pkg)
            else:
                logger.info(f"{pkg} is not installed. Skipping.")
    else:
        related_packages = [pkg_name]
        if is_package_installed(pkg_name, pkg_manager):
            for pkg in related_packages:
                if run_uninstall_cmd(pkg, pkg_manager):
                    success.append(pkg)
                else:
                    failed.append(pkg)
        elif is_snap_available():
            # Try snap uninstall if not found in apt/dnf
            if is_package_installed(pkg_name, "snap"):
                if run_uninstall_cmd(pkg_name, "snap"):
                    success.append(pkg_name)
                else:
                    failed.append(pkg_name)
            else:
                logger.info(f"{pkg_name} is not installed via snap. Skipping.")
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