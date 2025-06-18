import platform
import shutil
import logging

def get_os_type():
    """
    Detects the underlying operating system and returns it as a lowercase string.
    Only supports Mac and Linux.
    Returns:
        str: "linux" or "darwin"
    Raises:
        EnvironmentError: if OS is not supported (Windows or unknown)
    """
    os_type = platform.system().lower()
    if os_type == "windows":
        raise EnvironmentError("Windows is not supported. Only Mac and Linux are supported.")
    elif os_type not in ("linux", "darwin"):
        raise EnvironmentError(f"Unsupported operating system: {os_type}. Only Mac and Linux are supported.")
    return os_type

def is_linux():
    return get_os_type() == "linux"

def is_mac():
    return get_os_type() == "darwin"

def has_command(cmd):
    """
    Checks if a command is available on the system.
    Args:
        cmd (str): Command name (e.g., 'brew', 'apt')
    Returns:
        bool: True if available, False otherwise
    """
    return shutil.which(cmd) is not None

def get_linux_distro():
    """Returns the Linux distro ID (e.g., ubuntu, debian, arch, fedora, etc)."""
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.strip().split("=")[1].strip('"').lower()
    except Exception as e:
        logging.warning(f"Could not read /etc/os-release: {e}")
    return "unknown"