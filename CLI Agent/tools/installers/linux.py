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

def install_tool_linux(tool_name: str, version: str = "latest") -> dict:
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
            subprocess.run(cmd, check=True)

        return {
            "status": "success",
            "message": f"{tool_name} installed successfully on {distro}"
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Installation failed for {tool_name} on {distro}",
            "details": str(e)
        }
