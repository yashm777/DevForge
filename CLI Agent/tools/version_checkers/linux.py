import subprocess
import logging
from tools.utils.os_utils import get_available_package_manager, is_tool_installed
from tools.utils.name_resolver import resolve_tool_name

logger = logging.getLogger(__name__)

class LinuxVersionChecker:
    def __init__(self):
        self.pkg_manager = get_available_package_manager()
        if self.pkg_manager == "unknown":
            raise EnvironmentError("No supported package manager found on this Linux system.")

    def check_tool_version(self, tool_name: str):
        # Resolve executable name for version check context
        resolved = resolve_tool_name(tool_name, "linux", context="version_check")
        executable = resolved["name"]

        # First check if the executable is in PATH
        if not is_tool_installed(executable):
            # Tool not installed according to PATH
            return {
                "tool": tool_name,
                "status": "not_installed",
                "message": f"'{tool_name}' is not installed on the system."
            }

        # Special handling for Java
        if tool_name.lower() == "java":
            return self._check_java_versions()

        # Generic version check command: try <executable> --version or -version
        version = self._run_version_command(executable)
        if version:
            return {
                "tool": tool_name,
                "status": "installed",
                "version": version.strip()
            }

        # If version detection failed but executable present
        return {
            "tool": tool_name,
            "status": "installed",
            "version": "Unknown version"
        }

    def _run_version_command(self, executable: str) -> str | None:
        # Try common flags for version info
        for flag in ["--version", "-version"]:
            try:
                result = subprocess.run([executable, flag], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
                # Some tools print version info on stderr (e.g. java)
                if result.returncode == 0 and result.stderr.strip():
                    return result.stderr.strip()
            except Exception as e:
                logger.debug(f"Error running version command on {executable} with {flag}: {e}")
        return None

def _check_java_versions(self):
    installed_versions = []
    active_version = None

    # 1. List Java-related packages via dpkg
    if self.pkg_manager == "apt":
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

    # 2. Detect active Java version using symlink
    java_path = None
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

    # Extract version info from the resolved path
    if active_path:
        # Example: /usr/lib/jvm/java-17-openjdk-amd64/bin/java → java-17-openjdk-amd64
        parts = active_path.split("/")
        for part in parts:
            if "java-" in part and ("jdk" in part or "jre" in part):
                active_version = part
                break

    # Compose output
    versions_output = []
    for pkg in installed_versions:
        if active_version and active_version in pkg:
            versions_output.append(f"{pkg} (active)")
        else:
            versions_output.append(pkg)

    # If active version detected but not in installed packages, include it separately
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

