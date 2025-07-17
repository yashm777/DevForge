import subprocess
import logging
from tools.utils.os_utils import get_available_package_manager, is_tool_installed
from tools.utils.name_resolver import resolve_tool_name

logger = logging.getLogger(__name__)

def get_pkg_manager():
    pkg_manager = get_available_package_manager()
    if pkg_manager == "unknown":
        raise EnvironmentError("No supported package manager found on this Linux system.")
    return pkg_manager

def check_tool_version(tool_name: str, pkg_manager: str | None ):
    if pkg_manager is None:
        pkg_manager = get_pkg_manager()
    resolved = resolve_tool_name(tool_name, "linux", context="version_check")
    executable = resolved["name"]

    if not is_tool_installed(executable):
        return {
            "tool": tool_name,
            "status": "not_installed",
            "message": f"'{tool_name}' is not installed on the system."
        }

    if tool_name.lower() == "java":
        return check_java_versions(pkg_manager)

    version = run_version_command(executable)
    if version:
        return {
            "tool": tool_name,
            "status": "installed",
            "version": version.strip()
        }

    return {
        "tool": tool_name,
        "status": "installed",
        "version": "Unknown version"
    }

def run_version_command(executable: str) -> str | None:
    for flag in ["--version", "-version"]:
        try:
            result = subprocess.run([executable, flag], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            if result.returncode == 0 and result.stderr.strip():
                return result.stderr.strip()
        except Exception as e:
            logger.debug(f"Error running version command on {executable} with {flag}: {e}")
    return None

def check_java_versions(pkg_manager: str):
    installed_versions = []
    java_path = None
    active_version = None

    if pkg_manager == "apt":
        try:
            result = subprocess.run(["dpkg", "-l"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                for line in lines:
                    if line.startswith("ii") and any(term in line.lower() for term in ["openjdk", "default-jdk", "jdk", "jre"]):
                        pkg_name = line.split()[1]
                        installed_versions.append(pkg_name)
        except Exception as e:
            logger.error(f"Error checking installed Java packages: {e}")

    try:
        result = subprocess.run(["which", "java"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            java_path = result.stdout.strip()
    except Exception as e:
        logger.debug(f"Error running 'which java': {e}")

    active_path = None
    if java_path:
        try:
            result = subprocess.run(["readlink", "-f", java_path], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                active_path = result.stdout.strip()
        except Exception as e:
            logger.debug(f"Error resolving symlink for java: {e}")

    if active_path:
        parts = active_path.split("/")
        for part in parts:
            if "java-" in part and ("jdk" in part or "jre" in part):
                active_version = part
                break

    versions_output = []
    for pkg in installed_versions:
        if active_version and active_version in pkg:
            versions_output.append(f"{pkg} (active)")
        else:
            versions_output.append(pkg)

    if active_version and not any(active_version in pkg for pkg in installed_versions):
        versions_output.append(f"{active_version} (active but not from package list)")

    if not versions_output:
        return {
            "tool": "java",
            "status": "not_installed",
            "message": "No Java installations detected on the system."
        }

    return {
        "tool": "java",
        "status": "installed",
        "versions": versions_output
    }
