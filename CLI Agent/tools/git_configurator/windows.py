import subprocess
import os
from pathlib import Path
import shutil
import platform
import logging
import requests

# Git setup helpers for Windows: key gen, show public key, SSH check, clone, add key to GitHub.

def is_git_installed() -> bool:
    # Check if git.exe is on PATH
    return shutil.which("git") is not None

def is_ssh_installed() -> bool:
    # Check if OpenSSH tools (ssh, ssh-keygen) are on PATH
    return shutil.which("ssh") is not None and shutil.which("ssh-keygen") is not None

def get_ssh_dir() -> Path:
    # User's ~/.ssh directory
    return Path.home() / ".ssh"

def get_ssh_key_paths() -> tuple[Path, Path]:
    # Default RSA key pair paths (id_rsa, id_rsa.pub)
    ssh_dir = get_ssh_dir()
    return ssh_dir / "id_rsa", ssh_dir / "id_rsa.pub"

def _ensure_known_host(host: str, port: int = 22) -> None:
    # Pre-seed known_hosts; ignore if ssh-keyscan missing
    try:
        if shutil.which("ssh-keyscan") is None:
            return
        ssh_dir = get_ssh_dir()
        ssh_dir.mkdir(parents=True, exist_ok=True)
        known_hosts = ssh_dir / "known_hosts"
        cmd = ["ssh-keyscan", "-H"]
        if port and port != 22:
            cmd += ["-p", str(port)]
        cmd += [host]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout:
            with open(known_hosts, "a", encoding="utf-8") as f:
                f.write(r.stdout)
    except Exception:
        pass  # best effort only

def _ssh_auth(host: str, port: int) -> dict:
    # Non-interactive auth probe for a host:port
    try:
        _ensure_known_host(host, port)
        cmd = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
        if port and port != 22:
            cmd += ["-p", str(port)]
        target = f"git@{host}"
        r = subprocess.run(cmd + [target], capture_output=True, text=True, timeout=30)
        out = (r.stdout or "") + (r.stderr or "")
        low = out.lower()
        if "successfully authenticated" in low or "does not provide shell access" in low or low.startswith("hi "):
            return {"status": "success", "message": "SSH auth OK", "host": host, "port": port}
        if "permission denied" in low:
            return {"status": "error", "message": out.strip(), "host": host, "port": port}
        return {"status": "warning", "message": out.strip(), "host": host, "port": port}
    except Exception as e:
        return {"status": "error", "message": str(e), "host": host, "port": port}

def _is_network_block(msg: str) -> bool:
    # Detect common network blocks
    m = (msg or "").lower()
    return any(t in m for t in ["connection refused", "connection timed out", "timed out", "no route to host", "network is unreachable"])

def generate_ssh_key(email: str) -> dict:
    # Create RSA 4096 key if not already present
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
    # Return the public key; also put it in details.message so CLI prints the raw key text
    _, public_key = get_ssh_key_paths()
    if public_key.exists():
        with open(public_key, "r") as f:
            pubkey = f.read()
        return {
            "status": "success",
            "action": "get_public_key",
            "details": {"message": pubkey},  # CLI reads and prints this directly
            "public_key": pubkey
        }
    else:
        return {"status": "error", "message": "Public key does not exist."}

def check_ssh_connection() -> dict:
    # Try 22, then fallback to 443 (ssh.github.com)
    try:
        res22 = _ssh_auth("github.com", 22)
        if res22["status"] == "success":
            return {"status": "success", "message": "SSH to GitHub OK on 22.", "host": "github.com", "port": 22}

        # Fallback to 443 only on network issues
        if _is_network_block(res22.get("message", "")):
            res443 = _ssh_auth("ssh.github.com", 443)
            if res443["status"] == "success":
                return {"status": "success", "message": "SSH to GitHub OK on 443.", "host": "ssh.github.com", "port": 443}
            return {"status": res443["status"], "message": res443.get("message", ""), "host": "ssh.github.com", "port": 443}

        # Likely auth problem (key not added)
        return {"status": res22["status"], "message": res22.get("message", ""), "host": "github.com", "port": 22}
    except Exception as e:
        return {"status": "error", "message": f"SSH connection check failed: {e}"}

def clone_repository(repo_url: str, target_dir: str = ".") -> dict:
    # git clone with SSH 443 fallback support (via GIT_SSH_COMMAND)
    target_path = Path(target_dir).expanduser().resolve()

    # Probe auth/port to choose SSH route
    auth = check_ssh_connection()
    if auth.get("status") == "error":
        # Provide manual hint when blocked
        hint = ""
        if _is_network_block(auth.get("message", "")):
            hint = (
                "\nPort 22 may be blocked. Try SSH over 443:\n"
                "  ssh -T -p 443 git@ssh.github.com\n"
                "Or use ~/.ssh/config:\n"
                "  Host github.com\n"
                "    HostName ssh.github.com\n"
                "    Port 443\n"
            )
        return {"status": "error", "message": f"SSH check failed: {auth.get('message','')}{hint}"}

    # Build non-interactive SSH command
    base_ssh = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
    env = os.environ.copy()
    if auth.get("port") == 443:
        # Force github.com URL to connect via ssh.github.com:443
        env["GIT_SSH_COMMAND"] = f"{base_ssh} -o HostName=ssh.github.com -p 443"
    else:
        env["GIT_SSH_COMMAND"] = base_ssh

    try:
        subprocess.run(["git", "clone", repo_url], cwd=target_path, check=True, capture_output=True, text=True, env=env)
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
    # POST /user/keys with PAT to add the public key to GitHub
    api_url = "https://api.github.com/user/keys"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github+json"
    }
    data = {"title": "DevForge CLI Key", "key": pubkey}
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
    # Windows-only dispatcher for git setup tasks
    if platform.system() != "Windows":
        return {"status": "error", "message": "This script is intended for Windows systems."}

    # Pre-flight checks
    if not is_git_installed():
        return {"status": "error", "message": "Git is not installed. Please install Git for Windows and try again."}
    if not is_ssh_installed():
        return {"status": "error", "message": "ssh or ssh-keygen not found. Make sure Git Bash or OpenSSH is available."}

    # Route actions
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
        # Read local public key and optionally add to GitHub via PAT
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
                "You did not provide a GitHub Personal Access Token (PAT), so the key cannot be added automatically.\n"
                "Here are the manual steps to add your SSH key to GitHub:\n"
                "1. Run the following command to display your public key:\n"
                "   (CMD)      type %USERPROFILE%\\.ssh\\id_rsa.pub\n"
                "   (PowerShell) Get-Content $env:USERPROFILE\\.ssh\\id_rsa.pub\n"
                "2. Copy the output.\n"
                "3. Go to https://github.com/settings/ssh/new\n"
                "4. Paste the key and save."
            )
            return {"status": "warning", "action": action, "details": {"message": manual_msg}}

    else:
        return {"status": "error", "message": f"Unsupported action: {action}"}

# Example:
# result = perform_git_setup(action="generate_ssh_key", email="your_email@example.com")
# print(result)
