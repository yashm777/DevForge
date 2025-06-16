import shutil
import subprocess

def handle_tool(tool_name: str, version: str = "latest") -> bool:
    if shutil.which("brew") is None:
        print("Homebrew not found. Please install Homebrew first.")
        return False

    if tool_name == "nodejs":
        return subprocess.call(["brew", "install", "node"]) == 0

    elif tool_name == "docker":
        # Docker is usually installed as a GUI app via --cask
        return subprocess.call(["brew", "install", "--cask", "docker"]) == 0

    else:
        print(f"Tool '{tool_name}' not supported on macOS.")
        return False
