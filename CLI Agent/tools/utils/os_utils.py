import platform
import distro
import shutil

def get_os_type() -> str:
    """
    Return a simplified OS name: 'windows', 'mac', or 'linux'
    """
    os_name = platform.system().lower()
    if os_name == "windows":
        return "windows"
    elif os_name == "darwin":
        return "mac"
    elif os_name == "linux":
        return "linux"
    else:
        return "unknown"

def get_linux_distro() -> str:
    """
    Detect the specific Linux distribution using `distro` library.
    Returns simplified names like 'ubuntu', 'fedora', etc.
    """
    id_like = distro.id().lower()
    if "ubuntu" in id_like or "debian" in id_like:
        return "ubuntu"
    elif "fedora" in id_like or "rhel" in id_like or "centos" in id_like:
        return "fedora"
    elif "arch" in id_like:
        return "arch"
    elif "alpine" in id_like:
        return "alpine"
    else:
        return id_like

def get_available_package_manager() -> str:
    """
    Detect the available package manager based on OS or distro.
    Returns one of: 'apt', 'dnf', 'pacman', 'apk', 'winget', 'brew', or 'unknown'.
    """
    os_type = get_os_type()

    if os_type == "linux":
        if shutil.which("apt"):
            return "apt"
        elif shutil.which("dnf"):
            return "dnf"
        elif shutil.which("pacman"):
            return "pacman"
        elif shutil.which("apk"):
            return "apk"
        else:
            return "unknown"

    elif os_type == "mac":
        return "brew" if shutil.which("brew") else "unknown"

    elif os_type == "windows":
        return "winget" if shutil.which("winget") else "unknown"

    return "unknown"

def is_sudo_available() -> bool:
    """
    Check if the system supports sudo (non-interactive).
    """
    return shutil.which("sudo") is not None

def is_snap_available() -> bool:
    """
    Check if 'snap' package manager is installed and available on the system.
    """
    return shutil.which("snap") is not None

def check_sudo_access() -> bool:
    """
    Check if the current user has sudo privileges without a password prompt.
    """
    import subprocess
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False

import subprocess
import shutil
import logging

def ensure_package_manager_installed(manager: str) -> bool:
    if shutil.which(manager):
        logging.info(f"Package manager '{manager}' is already installed.")
        return True

    logging.info(f"Package manager '{manager}' is missing. Attempting to install...")

    os_type = get_os_type()

    try:
        if os_type == "linux":
            if manager == "snap":
                # Example for snap on Ubuntu/Debian
                subprocess.run(["sudo", "apt-get", "update"], check=True)
                result = subprocess.run(["sudo", "apt-get", "install", "-y", "snapd"], check=False)
                if result.returncode == 0:
                    logging.info("snapd installed successfully.")
                    return True
                else:
                    logging.error("Failed to install snapd.")
                    return False
            # Add other package managers here as needed
            else:
                logging.error(f"Automatic installation for '{manager}' not implemented.")
                return False
        else:
            logging.error(f"Unsupported OS for installing package manager: {os_type}")
            return False
    except Exception as e:
        logging.error(f"Exception during package manager install: {e}")
        return False


def is_tool_installed(tool: str) -> bool:
    """
    Check if the given tool/command is available in the system PATH.
    """
    return shutil.which(tool) is not None

def run_commands(command_list: list[list[str]]) -> subprocess.CompletedProcess | None:
    """
    Runs a list of shell commands one after the other.
    Returns the final subprocess.CompletedProcess if successful,
    or the one that failed. Returns None if all fail silently.
    """
    for cmd in command_list:
        try:
            logging.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logging.warning(f"Command failed: {' '.join(cmd)}\nError: {result.stderr.strip()}")
                return result
        except Exception as e:
            logging.error(f"Error while running command {' '.join(cmd)}: {e}")
            return None
    return result  # return last success/failure result

def get_related_packages(tool_name: str, pkg_manager: str) -> list[str]:
    """
    Returns a list of package names related to the given tool by querying installed packages.
    Useful for tools like Java which have multiple components (jdk, jre, headless, etc.)
    """
    tool_name = tool_name.lower()
    keywords = []

    if tool_name == "java":
        keywords = ["openjdk", "default-jdk", "default-jre", "jdk", "jre"]
    elif tool_name in ("c++", "cpp", "g++"):
        keywords = ["g++"]
    else:
        keywords = [tool_name]

    try:
        if pkg_manager == "apt" and shutil.which("dpkg"):
            result = subprocess.run(
                ["dpkg", "-l"], capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.strip().splitlines()
            installed_packages = [
                line.split()[1]
                for line in lines
                if line.startswith("ii") and any(k in line for k in keywords)
            ]
            return installed_packages

        elif pkg_manager == "dnf":
            result = subprocess.run(
                ["dnf", "list", "installed"], capture_output=True, text=True, timeout=5
            )
            return [
                line.split()[0]
                for line in result.stdout.splitlines()
                if any(k in line for k in keywords)
            ]

        elif pkg_manager == "pacman":
            result = subprocess.run(
                ["pacman", "-Q"], capture_output=True, text=True, timeout=5
            )
            return [
                line.split()[0]
                for line in result.stdout.splitlines()
                if any(k in line for k in keywords)
            ]

        elif pkg_manager == "apk":
            result = subprocess.run(
                ["apk", "info"], capture_output=True, text=True, timeout=5
            )
            return [
                line.strip()
                for line in result.stdout.splitlines()
                if any(k in line for k in keywords)
            ]

        else:
            logging.warning(f"No implementation for package listing with: {pkg_manager}")

    except Exception as e:
        logging.error(f"Failed to list packages for '{tool_name}': {e}")

    return []
