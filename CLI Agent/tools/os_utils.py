# os_utils.py - For detecting OS type and checking command availability. This module is used by the tool_installer.py module.
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
