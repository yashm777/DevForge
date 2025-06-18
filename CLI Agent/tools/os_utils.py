import platform
import shutil

def get_os_type():
    """
    Detects the underlying operating system and returns it as a lowercase string.
    Returns:
        str: "linux", "darwin", or "windows"
    Raises:
        EnvironmentError: if OS is not supported
    """
    os_type = platform.system().lower()
    if os_type not in ("linux", "darwin", "windows"):
        raise EnvironmentError(f"Unsupported operating system: {os_type}")
    return os_type

def is_linux():
    return get_os_type() == "linux"

def is_mac():
    return get_os_type() == "darwin"

def is_windows():
    return get_os_type() == "windows"

def has_command(cmd):
    """
    Checks if a command is available on the system.
    Args:
        cmd (str): Command name (e.g., 'brew', 'apt', 'choco')
    Returns:
        bool: True if available, False otherwise
    """
    return shutil.which(cmd) is not None

def get_linux_distribution():
    """
    Returns the Linux distribution ID (e.g., 'ubuntu', 'fedora', 'arch') in lowercase.
    Returns:
        str or None: distro ID or None if not Linux or detection failed
    """
    if not is_linux():
        return None
    try:
        with open("/etc/os-release", "r") as f:
            for line in f:
                if line.startswith("ID="):
                    return line.strip().split("=")[1].strip('"').lower()
    except Exception:
        return None
