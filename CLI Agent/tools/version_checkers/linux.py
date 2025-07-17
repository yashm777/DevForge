import shutil
import subprocess
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_executable(tool_name: str) -> str:
    tool_aliases = {
        "python": ["python3", "python"],
        "pip": ["pip3", "pip"],
        "node": ["node", "nodejs"],
        "java": ["java", "javac"],
    }
    
    possible_names = tool_aliases.get(tool_name, [tool_name])
    
    for name in possible_names:
        executable_path = shutil.which(name)
        if executable_path:
            return executable_path
    
    common_paths = [
        "/usr/local/bin",
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
        os.path.expanduser("~/.local/bin"),
    ]
    
    for path in common_paths:
        for name in possible_names:
            full_path = os.path.join(path, name)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                return full_path
                
    return None


def get_java_versions():
    java_info = {"installed_versions": [], "active_version": None}
    
    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True, text=True, timeout=10, check=True,
            stderr=subprocess.STDOUT
        )
        java_info["active_version"] = result.stdout.strip().split("\n")[0]
    except Exception as e:
        logger.warning(f"Failed to get active java version: {e}")
    
    try:
        result = subprocess.run(
            ["update-alternatives", "--list", "java"],
            capture_output=True, text=True, timeout=10, check=True
        )
        lines = result.stdout.strip().splitlines()
        java_info["installed_versions"] = lines
    except Exception:
        java_info["installed_versions"] = []
    
    return java_info


def check_version(tool_name: str, version: str = "latest") -> dict:
    executable_path = find_executable(tool_name)
    if executable_path:
        try:
            version_commands = [
                [executable_path, "--version"],
                [executable_path, "-v"],
                [executable_path, "-V"],
                [executable_path, "version"],
            ]
            for cmd in version_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=True)
                    output = result.stdout.strip() or result.stderr.strip()
                    if output:
                        return {
                            "status": "success",
                            "message": f"Version information for {tool_name}",
                            "version": output,
                            "command": " ".join(cmd),
                        }
                except subprocess.CalledProcessError:
                    continue
        except Exception as e:
            logger.warning(f"Error running version commands for {tool_name}: {e}")
    
    # Special case for java
    if tool_name.lower() == "java":
        java_versions = get_java_versions()
        if java_versions["installed_versions"] or java_versions["active_version"]:
            return {
                "status": "success",
                "message": "Java version details",
                "active_version": java_versions["active_version"],
                "installed_versions": java_versions["installed_versions"],
            }
    
    # Package manager queries
    try:
        # Debian/Ubuntu and derivatives
        if shutil.which("dpkg"):
            result = subprocess.run(
                ["dpkg", "-l", tool_name],
                capture_output=True, text=True, timeout=10, check=True
            )
            lines = result.stdout.strip().splitlines()
            for line in lines:
                if line.startswith("ii"):
                    parts = line.split()
                    if len(parts) >= 3:
                        return {
                            "status": "success",
                            "message": f"Version info from dpkg for {tool_name}",
                            "version": parts[2],
                            "source": "dpkg"
                        }
        
        # RPM-based distros
        if shutil.which("rpm"):
            result = subprocess.run(
                ["rpm", "-q", tool_name],
                capture_output=True, text=True, timeout=10, check=True
            )
            output = result.stdout.strip()
            if output and "not installed" not in output.lower():
                return {
                    "status": "success",
                    "message": f"Version info from rpm for {tool_name}",
                    "version": output,
                    "source": "rpm"
                }

        # Snap packages
        if shutil.which("snap"):
            result = subprocess.run(
                ["snap", "list", tool_name],
                capture_output=True, text=True, timeout=10, check=True
            )
            lines = result.stdout.strip().splitlines()
            if len(lines) >= 2:
                version_line = lines[1].split()
                if len(version_line) >= 2:
                    return {
                        "status": "success",
                        "message": f"Version info from snap for {tool_name}",
                        "version": version_line[1],
                        "source": "snap"
                    }

        # Pacman (Arch Linux)
        if shutil.which("pacman"):
            result = subprocess.run(
                ["pacman", "-Qi", tool_name],
                capture_output=True, text=True, timeout=10, check=True
            )
            lines = result.stdout.strip().splitlines()
            for line in lines:
                if line.lower().startswith("version"):
                    _, ver = line.split(":", 1)
                    return {
                        "status": "success",
                        "message": f"Version info from pacman for {tool_name}",
                        "version": ver.strip(),
                        "source": "pacman"
                    }

        # Flatpak packages
        if shutil.which("flatpak"):
            result = subprocess.run(
                ["flatpak", "info", tool_name],
                capture_output=True, text=True, timeout=10, check=True
            )
            lines = result.stdout.strip().splitlines()
            for line in lines:
                if line.lower().startswith("version"):
                    _, ver = line.split(":", 1)
                    return {
                        "status": "success",
                        "message": f"Version info from flatpak for {tool_name}",
                        "version": ver.strip(),
                        "source": "flatpak"
                    }

    except Exception as e:
        logger.warning(f"Package manager query failed: {e}")
    
    return {
        "status": "error",
        "message": f"{tool_name} is not installed, not in PATH, or version could not be determined."
    }
