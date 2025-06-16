import shutil
import subprocess

def handle_tool(tool_name: str, version: str = "latest") -> bool:
    if shutil.which("apt") is None:
        print("APT not found.")
        return False

    if tool_name == "nodejs":
        return subprocess.call(["sudo", "apt", "install", "-y", "nodejs"]) == 0
    elif tool_name == "docker":
        return subprocess.call(["sudo", "apt", "install", "-y", "docker.io"]) == 0
    else:
        print(f"Tool {tool_name} not supported.")
        return False
