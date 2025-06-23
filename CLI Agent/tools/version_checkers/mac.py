import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_tool(tool_name: str, version: str = "latest") -> dict:
    """
    Check the version of a tool on macOS.

    Args:
        tool_name (str): Name of the tool to check version for.
        version (str): Version parameter (not used for version check).

    Returns:
        dict: Status message and version information.
    """
    try:
        # Check if the tool is installed
        if shutil.which(tool_name) is None:
            return {
                "status": "error",
                "message": f"{tool_name} is not installed or not in PATH"
            }

        # Try different version command patterns
        version_commands = [
            [tool_name, "--version"],
            [tool_name, "-v"],
            [tool_name, "-V"],
            [tool_name, "version"]
        ]

        for cmd in version_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    version_output = result.stdout.strip()
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name}",
                        "version": version_output,
                        "command": " ".join(cmd)
                    }
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                continue

        # If no version command worked, try Homebrew for installed packages
        if shutil.which("brew"):
            try:
                # Check if it's a Homebrew formula
                brew_cmd = ["brew", "list", "--versions", tool_name]
                result = subprocess.run(brew_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    return {
                        "status": "success",
                        "message": f"Version information for {tool_name} (Homebrew)",
                        "version": result.stdout.strip(),
                        "source": "homebrew"
                    }
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass

        return {
            "status": "error",
            "message": f"Could not determine version for {tool_name}",
            "details": "Tool is installed but version command failed"
        }

    except Exception as e:
        logger.error(f"Error checking version for {tool_name}: {e}")
        return {
            "status": "error",
            "message": f"Error checking version for {tool_name}",
            "details": str(e)
        }

# Legacy function for backward compatibility
def version_tool_mac(tool_name: str, version: str = "latest") -> dict:
    return handle_tool(tool_name, version) 