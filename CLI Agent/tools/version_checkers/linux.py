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
        # For Java, check all installed JDK/JRE versions via package manager and java -version
        installed_versions = []
        active_version = None

        # Try to detect installed packages related to Java via package manager
        # Using apt/dpkg for example; for other package managers adapt accordingly

        if self.pkg_manager == "apt":
            try:
                result = subprocess.run(["dpkg", "-l"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().splitlines()
                    for line in lines:
                        if line.startswith("ii") and ("openjdk" in line or "default-jdk" in line or "jdk" in line or "jre" in line):
                            pkg_name = line.split()[1]
                            installed_versions.append(pkg_name)
            except Exception as e:
                logger.error(f"Error checking installed Java packages: {e}")

        # Run `java -version` to get active java version (usually stderr)
        active_version_str = None
        try:
            result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                active_version_str = result.stderr.strip().splitlines()[0]
        except Exception as e:
            logger.debug(f"Error running 'java -version': {e}")

        # Compose result list, mark active version with (active)
        java_versions_info = []
        for ver in installed_versions:
            if active_version_str and ver in active_version_str:
                java_versions_info.append(f"{ver} (active)")
                active_version = ver
            else:
                java_versions_info.append(ver)

        # If active version not matched from packages, still add active version from java -version output
        if active_version_str and active_version is None:
            java_versions_info.append(f"Active: {active_version_str}")

        if not java_versions_info:
            # If no packages detected, fallback to active version string if present
            if active_version_str:
                return {
                    "tool": "java",
                    "status": "installed",
                    "versions": [f"Active: {active_version_str}"]
                }
            else:
                return {
                    "tool": "java",
                    "status": "not_installed",
                    "message": "Java is not installed on this system."
                }

        return {
            "tool": "java",
            "status": "installed",
            "versions": java_versions_info
        }
