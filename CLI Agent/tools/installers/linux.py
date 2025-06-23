import shutil
import subprocess
import logging
from tools.os_utils import get_linux_distro

logging.basicConfig(level=logging.INFO)

# Define install command map for supported distros
INSTALL_COMMANDS = {
    "ubuntu": lambda tool: [["sudo", "apt", "update"], ["sudo", "apt", "install", "-y", tool]],
    "debian": lambda tool: [["sudo", "apt", "update"], ["sudo", "apt", "install", "-y", tool]],
    "fedora": lambda tool: [["sudo", "dnf", "install", "-y", tool]],
    "centos": lambda tool: [["sudo", "dnf", "install", "-y", tool]],
    "rhel":   lambda tool: [["sudo", "dnf", "install", "-y", tool]],
    "arch":   lambda tool: [["sudo", "pacman", "-Sy", "--noconfirm", tool]],
    "manjaro": lambda tool: [["sudo", "pacman", "-Sy", "--noconfirm", tool]],
    "alpine": lambda tool: [["sudo", "apk", "update"], ["sudo", "apk", "add", tool]]
}

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    """Handle tool installation on Linux"""
    if shutil.which("sudo") is None:
        return {
            "status": "error",
            "message": "sudo not found. Please install sudo or run as root."
        }

    distro = get_linux_distro()

    commands_fn = INSTALL_COMMANDS.get(distro)
    if not commands_fn:
        return {
            "status": "error",
            "message": f"Unsupported Linux distribution: {distro}"
        }

    try:
        commands = commands_fn(tool_name)
        for cmd in commands:
            logging.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logging.info(f"Command output: {result.stdout}")

        return {
            "status": "success",
            "message": f"{tool_name} installed successfully on {distro}",
            "details": f"Distribution: {distro}, Version: {version}"
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Installation failed for {tool_name} on {distro}",
            "details": e.stderr if e.stderr else str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error during installation: {str(e)}"
        }

# Legacy function for backward compatibility
def install_tool_linux(tool_name: str, version: str = "latest") -> dict:
    return handle_tool(tool_name, version)
# This function is kept for backward compatibility with existing code that may call it directly.
# It simply forwards the call to the new `handle_tool` function.