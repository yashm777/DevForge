import subprocess
import os
from pathlib import Path
import shutil
import platform
import logging
import requests

def is_git_installed() -> bool:
    return shutil.which("git") is not None

def is_ssh_installed() -> bool:
    return shutil.which("ssh") is not None and shutil.which("ssh-keygen") is not None

def get_ssh_dir() -> Path:
    return Path.home() / ".ssh"

def get_ssh_key_paths() -> tuple[Path, Path]:
    ssh_dir = get_ssh_dir()
    return ssh_dir / "id_rsa", ssh_dir / "id_rsa.pub"

def generate_ssh_key(email: str) -> dict:
    private_key, public_key = get_ssh_key_paths()
    ssh_dir = get_ssh_dir()

    if not ssh_dir.exists():
        ssh_dir.mkdir(parents=True)

    if private_key.exists() and public_key.exists():
        return {"status": "warning", "message": f"SSH key already exists at {private_key}"}

    try:
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", email,
            "-f", str(private_key), "-N", ""
        ], check=True)
        if not public_key.exists():
            return {"status": "error", "message": "Public key file not found after generation."}
        with open(public_key, "r") as f:
            pubkey = f.read()
        return {
            "status": "success",
            "message": f"SSH key generated at {private_key}",
            "public_key": pubkey
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate SSH key: {e}"}

def get_public_key() -> dict:
    _, public_key = get_ssh_key_paths()
    if public_key.exists():
        with open(public_key, "r") as f:
            return {"status": "success", "public_key": f.read()}
    else:
        return {"status": "error", "message": "Public key does not exist."}

def check_ssh_connection() -> dict:
    try:
        result = subprocess.run(["ssh", "-T", "git@github.com"], capture_output=True, text=True, timeout=15)
        if "successfully authenticated" in result.stdout or "You've successfully authenticated" in result.stdout:
            return {"status": "success", "message": "SSH connection to GitHub was successful."}
        elif "Permission denied" in result.stderr:
            return {"status": "error", "message": "SSH connection failed: Permission denied. Is your key added to GitHub?"}
        else:
            return {"status": "warning", "message": result.stderr or result.stdout}
    except Exception as e:
        return {"status": "error", "message": f"SSH connection check failed: {e}"}

def clone_repository(repo_url: str, target_dir: str = ".") -> dict:
    target_path = Path(target_dir).expanduser().resolve()
    try:
        subprocess.run(["git", "clone", repo_url], cwd=target_path, check=True, capture_output=True, text=True)
        return {"status": "success", "message": f"Repository cloned successfully to {target_path}"}
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": (
                f"Failed to clone repository.\n"
                f"Make sure your SSH key is added to GitHub (if using SSH).\n"
                f"Check the repo URL and your access rights.\n"
                f"Details: {e.stderr or e.stdout or str(e)}"
            )
        }

def add_ssh_key_to_github(pubkey: str, pat: str) -> str:
    """
    Add SSH public key to GitHub using the API and a Personal Access Token (PAT).
    """
    api_url = "https://api.github.com/user/keys"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "title": "DevForge CLI Key",
        "key": pubkey
    }
    response = requests.post(api_url, headers=headers, json=data)
    if response.status_code == 201:
        return "✅ SSH key added to your GitHub account via API."
    else:
        return f"❌ Failed to add SSH key via API: {response.text}"

def perform_git_setup(
    action: str,
    email: str = "",
    repo_url: str = "",
    branch: str = "",
    username: str = "",
    dest_dir: str = ".",
    pat: str = ""
) -> dict:
    if platform.system() != "Windows":
        return {"status": "error", "message": "This script is intended for Windows systems."}

    if not is_git_installed():
        return {"status": "error", "message": "Git is not installed. Please install Git for Windows and try again."}

    if not is_ssh_installed():
        return {"status": "error", "message": "ssh or ssh-keygen not found. Make sure Git Bash or OpenSSH is available."}

    if action == "generate_ssh_key":
        if not email or "@" not in email:
            return {"status": "error", "message": "A valid email is required to generate SSH key."}
        return generate_ssh_key(email)

    elif action == "get_public_key":
        return get_public_key()

    elif action == "check_ssh":
        return check_ssh_connection()

    elif action == "clone":
        if not repo_url:
            return {"status": "error", "message": "Repository URL is required for cloning."}
        return clone_repository(repo_url, dest_dir)

    elif action == "add_ssh_key":
        # Find public key
        _, public_key_path = get_ssh_key_paths()
        if not public_key_path.exists():
            return {"status": "error", "message": "SSH public key not found. Please generate it first."}
        with open(public_key_path, "r") as pubkey_file:
            pubkey = pubkey_file.read()
        if pat:
            result = add_ssh_key_to_github(pubkey, pat)
            return {"status": "success", "action": action, "details": {"message": result}}
        else:
            manual_msg = (
                "Manual steps to add your SSH key to GitHub:\n"
                "1. Run the following command to display your public key:\n"
                "   type %USERPROFILE%\\.ssh\\id_rsa.pub\n"
                "2. Copy the output.\n"
                "3. Go to https://github.com/settings/ssh/new\n"
                "4. Paste the key and save."
            )
            return {"status": "warning", "action": action, "details": {"message": manual_msg}}

    else:
        return {"status": "error", "message": f"Unsupported action: {action}"}

# Example usage for automation:
# result = perform_git_setup(action="generate_ssh_key", email="your_email@example.com")
# print(result)
