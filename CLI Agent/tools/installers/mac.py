import shutil
import subprocess

def install_tool_mac(tool_name: str, version: str = "latest") -> bool:
    if shutil.which("brew") is None:
        print("Homebrew not found. Attempting to install...")
        return False  # You can trigger an auto-installer here

    # For GUI tools, --cask is often needed, but we’ll guess based on common tools
    is_cask = tool_name.lower() in {"docker", "visual-studio-code", "google-chrome"}

    if is_cask:
        command = ["brew", "install", "--cask", tool_name]
    else:
        command = ["brew", "install", tool_name]

    # Optionally handle version if needed (Homebrew rarely supports specific versions)
    return subprocess.call(command) == 0
