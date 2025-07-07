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