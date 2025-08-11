"""
Git setup utilities for Linux:
- Configure global Git username/email
- Generate SSH keypair (id_rsa)
- Show public key
- Add public key to GitHub via API (with PAT)
- Verify SSH auth to GitHub
- Clone repositories via SSH (non-interactive)
"""

import subprocess
import os
from pathlib import Path
import shutil
import logging
from urllib.parse import urlparse
import requests
import stat

# Setup logging across this module
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)


def is_git_installed() -> bool:
    """
    Check if Git is installed on the system.
    Uses shutil.which to detect git in PATH.
    """
    return shutil.which("git") is not None


def configure_git_credentials(username: str, email: str):
    """
    Configure Git with user credentials globally, only if not already set.
    Idempotent: updates only when values differ.
    """
    if not username or not isinstance(username, str):
        raise ValueError("A valid Git username must be provided.")
    if not email or not isinstance(email, str) or "@" not in email:
        raise ValueError("A valid Git email address must be provided.")

    # Read current global config (empty if unset)
    current_name = subprocess.run(
        ["git", "config", "--global", "--get", "user.name"],
        capture_output=True, text=True
    ).stdout.strip()
    current_email = subprocess.run(
        ["git", "config", "--global", "--get", "user.email"],
        capture_output=True, text=True
    ).stdout.strip()

    # Update only when needed
    if current_name != username:
        subprocess.run(["git", "config", "--global", "user.name", username], check=True)
        logging.info(f"Set global git user.name to {username}")
    if current_email != email:
        subprocess.run(["git", "config", "--global", "user.email", email], check=True)
        logging.info(f"Set global git user.email to {email}")


def generate_ssh_key(email: str, key_path: str = "~/.ssh/id_rsa"):
    """
    Generate a new SSH key if it doesn't already exist.
    Returns a dict with status/message and the public_key (string) on success.
    Note: does not print the full key; instructs user to run 'cat ~/.ssh/id_rsa.pub'.
    """
    if not email or "@" not in email:
        raise ValueError("A valid email address is required to generate an SSH key.")

    key_path = os.path.expanduser(key_path)
    ssh_dir = os.path.dirname(key_path)

    # Ensure ~/.ssh exists with secure perms
    if not os.path.exists(ssh_dir):
        os.makedirs(ssh_dir, mode=0o700)

    # If private key already exists, skip generation
    if not os.path.exists(key_path):
        try:
            # Generate RSA 4096 key without passphrase (-N "")
            result = subprocess.run([
                "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", email,
                "-f", key_path, "-N", ""
            ], capture_output=True, text=True, timeout=30)

            pub_key_path = key_path + ".pub"

            # Verify both private and public files exist
            if os.path.exists(key_path) and os.path.exists(pub_key_path):
                logging.info("SSH key generated successfully.")
                with open(pub_key_path, "r") as pubkey_file:
                    pubkey = pubkey_file.read()

                # Do not print full key. Give a clear hint instead.
                logging.info("To view your public key, run:  cat ~/.ssh/id_rsa.pub")

                # ssh-keygen sometimes returns non-zero with SIGPIPE; still OK if files exist
                if result.returncode != 0:
                    logging.warning(f"ssh-keygen returned non-zero exit code: {result.returncode}. Output: {result.stderr or result.stdout}")

                return {"status": "success", "message": f"SSH key generated at {key_path}", "public_key": pubkey}
            else:
                error_msg = result.stderr or result.stdout or "Unknown error during key generation"
                return {"status": "error", "message": f"Failed to generate SSH key: {error_msg}"}

        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "SSH key generation timed out"}
        except Exception as e:
            return {"status": "error", "message": f"Unexpected error during SSH key generation: {str(e)}"}
    else:
        logging.info(f"SSH key already exists at: {key_path}")
        return {"status": "warning", "message": f"SSH key already exists at {key_path}. Generation skipped."}


def get_public_key(key_path: str = "~/.ssh/id_rsa"):
    """
    Return the public SSH key as text if present.
    Otherwise return instructions to generate one.
    """
    pub_key_path = os.path.expanduser(key_path) + ".pub"
    if not os.path.exists(pub_key_path):
        return (
            "SSH public key not found.\n"
            "Generate one with: action=generate_ssh_key and provide your email, e.g.\n"
            "Example: git_setup action=generate_ssh_key email=you@example.com"
        )
    try:
        with open(pub_key_path, "r") as f:
            public_key = f.read().strip()
        if not public_key:
            return f"Public key file exists but is empty: {pub_key_path}"
        # Return the actual key contents so the CLI can display it directly
        msg = (
            f"Your SSH public key ({pub_key_path}):\n{public_key}\n\n"
            "Copy the above key and add it at: https://github.com/settings/ssh/new\n"
        )
        return msg
    except FileNotFoundError:
        return f"Public key file not found at {pub_key_path}. Please generate your SSH key."
    except PermissionError:
        return f"Permission denied when reading public key file: {pub_key_path}"
    except Exception as e:
        return f"Error reading public key: {e}"


def _is_github_duplicate_key_response(payload: dict) -> bool:
    """
    Detect 'key already exists/in use' from GitHub 422 payload.
    Inspects both 'message' and 'errors[].code/message'.
    """
    try:
        msg = (payload.get("message") or "").lower()
        errors = payload.get("errors") or []
        codes = {str(e.get("code", "")).lower() for e in errors if isinstance(e, dict)}
        texts = " ".join([str(e.get("message", "")).lower() for e in errors if isinstance(e, dict)])
        return (
            "already in use" in msg or
            "already exists" in msg or
            "key is already in use" in msg or
            "already in use" in texts or
            "already exists" in texts or
            "key_already_in_use" in codes or
            "already_exists" in codes
        )
    except Exception:
        return False


def add_ssh_key_to_github_or_manual(email: str, pat: str = None, key_path: str = "~/.ssh/id_rsa"):
    """
    Add SSH public key to GitHub using a Personal Access Token (PAT).
    - With PAT: POST to GitHub API; handle duplicates gracefully.
    - Without PAT: return manual steps message.
    """
    pub_key_path = os.path.expanduser(key_path) + ".pub"
    if not os.path.exists(pub_key_path):
        return {"status": "error", "message": "SSH public key not found. Please generate it first."}

    with open(pub_key_path, "r") as pubkey_file:
        pubkey = pubkey_file.read().strip()  # normalize single-line key

    if pat:
        # Call GitHub API to register the key
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

        # Created
        if response.status_code == 201:
            return {"status": "success", "message": "✅ SSH key added to your GitHub account via API."}

        # Duplicate or validation error; treat duplicates benignly
        elif response.status_code == 422:
            try:
                payload = response.json()
            except Exception:
                payload = {}
            if _is_github_duplicate_key_response(payload):
                return {"status": "warning", "message": "⚠️ This SSH key is already added to your GitHub account. Nothing to do."}
            # If the key already authenticates via SSH, it’s fine
            auth = check_ssh_key_auth()
            if auth.get("status") == "success":
                return {"status": "warning", "message": "⚠️ SSH key already authorized with GitHub. Nothing to do."}
            return {"status": "error", "message": "Validation failed while adding SSH key. Please verify the key and try again."}

        # Auth failure (bad PAT/scope)
        elif response.status_code == 401:
            return {"status": "error", "message": "Unauthorized. Check your PAT and required scopes (admin:public_key)."}

        # Other HTTP errors
        else:
            return {"status": "error", "message": f"Failed to add SSH key via API (HTTP {response.status_code})."}

    else:
        # No PAT: return manual instructions (do not print here)
        manual_msg = (
            "Personal Access Token was not provided.\n"
            "Manual steps to add your SSH key to GitHub:\n"
            "1. Run the following command to display your public key:\n"
            "   cat ~/.ssh/id_rsa.pub\n"
            "2. Copy the output.\n"
            "3. Go to https://github.com/settings/ssh/new\n"
            "4. Paste the key and save."
        )
        return {"status": "success", "message": manual_msg}


def is_https_url(url: str) -> bool:
    """Return True if URL is an HTTPS URL."""
    parsed = urlparse(url)
    return parsed.scheme == "https"


def is_ssh_url(url: str) -> bool:
    """
    Return True for SSH GitHub URLs (git@github.com:owner/repo.git).
    """
    return url.startswith("git@github.com:")


def _ensure_ssh_dir() -> str:
    """
    Ensure ~/.ssh exists with secure permissions (700).
    """
    d = os.path.expanduser("~/.ssh")
    os.makedirs(d, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except Exception:
        pass
    return d


def ensure_known_host(host: "str" = "github.com", port: int = 22):
    """
    Pre-seed known_hosts with GitHub host key to avoid interactive prompt.
    Idempotent: does nothing if an entry already exists.
    """
    _ensure_ssh_dir()
    kh = os.path.expanduser("~/.ssh/known_hosts")
    try:
        # Skip if we already have an entry for this host
        if os.path.exists(kh):
            with open(kh, "r", encoding="utf-8", errors="ignore") as f:
                if any(host in line for line in f):
                    return
        # Fetch host key and append to known_hosts
        cmd = ["ssh-keyscan", "-H"]
        if port and port != 22:
            cmd += ["-p", str(port)]
        cmd += [host]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0 and r.stdout:
            with open(kh, "a", encoding="utf-8") as f:
                f.write(r.stdout)
            try:
                os.chmod(kh, 0o600)  # secure perms for known_hosts
            except Exception:
                pass
        else:
            logging.warning(f"ssh-keyscan failed for {host}: {r.stderr or r.stdout}")
    except Exception as e:
        logging.warning(f"Could not preseed known_hosts for {host}: {e}")


def _ssh_auth(host: str, port: int) -> dict:
    # Single auth attempt to a host:port
    try:
        ensure_known_host(host, port)
        cmd = ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new"]
        if port and port != 22:
            cmd += ["-p", str(port)]
        target = f"git@{host}"
        r = subprocess.run(cmd + [target], capture_output=True, text=True, check=False, timeout=30)
        out = (r.stdout + r.stderr).strip()
        low = out.lower()
        if "successfully authenticated" in low or "does not provide shell access" in low or low.startswith("hi "):
            return {"status": "success", "message": "SSH auth OK", "host": host, "port": port}
        if "permission denied" in low:
            return {"status": "error", "message": out, "host": host, "port": port}
        return {"status": "warning", "message": out, "host": host, "port": port}
    except Exception as e:
        return {"status": "error", "message": str(e), "host": host, "port": port}


def check_ssh_key_auth() -> dict:
    """
    Check if the SSH key is authorized with GitHub, try 22 then fallback to 443.
    """
    key_path = os.path.expanduser("~/.ssh/id_rsa")
    pub_key_path = key_path + ".pub"
    if not os.path.exists(key_path) or not os.path.exists(pub_key_path):
        return {"status": "error", "message": "SSH key not found. Please generate your SSH key first."}

    # First try standard SSH (22)
    res22 = _ssh_auth("github.com", 22)
    if res22["status"] == "success":
        return res22

    # If network to 22 is blocked, try SSH over 443
    msg = (res22.get("message") or "").lower()
    network_block = any(tok in msg for tok in [
        "connection refused", "connection timed out", "timed out",
        "no route to host", "network is unreachable"
    ])
    if network_block:
        res443 = _ssh_auth("ssh.github.com", 443)
        return res443

    # Otherwise return the first result (likely permission/auth issue)
    return res22


def clone_repository_ssh(repo_url: str, dest_dir: str = None, branch: str = None):
    """
    Clone via SSH with fallback to port 443 when 22 is blocked.
    """
    logging.info(f"Requested clone for repo: {repo_url} into {dest_dir or 'current directory'}")
    if not is_ssh_url(repo_url):
        logging.error(f"Unsupported repository URL format: {repo_url!r}")
        raise RuntimeError("Only SSH GitHub links (git@github.com:...) are supported for cloning.")

    key_path = os.path.expanduser("~/.ssh/id_rsa")
    pub_key_path = key_path + ".pub"
    if not os.path.exists(key_path) or not os.path.exists(pub_key_path):
        raise RuntimeError("SSH key not found. Please generate your SSH key before cloning.")

    # Auth check (tries 22 then 443)
    auth = check_ssh_key_auth()
    if auth["status"] != "success":
        manual_msg = (
            "If port 22 is blocked, try SSH over 443:\n"
            "  ssh -T -p 443 git@ssh.github.com\n"
            "Or add to ~/.ssh/config:\n"
            "  Host github.com\n"
            "    HostName ssh.github.com\n"
            "    Port 443\n"
        )
        raise RuntimeError(f"SSH auth failed: {auth.get('message','')}\n{manual_msg}")

    # Build git clone command
    cmd = ["git", "clone", repo_url]
    if dest_dir:
        cmd.append(dest_dir)

    env = os.environ.copy()
    # Always non-interactive; switch to 443 host/port when needed
    base_ssh = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
    if auth.get("port") == 443:
        # Force github.com URL to connect to ssh.github.com:443
        env["GIT_SSH_COMMAND"] = f"{base_ssh} -o HostName=ssh.github.com -p 443"
    else:
        env["GIT_SSH_COMMAND"] = base_ssh

    try:
        logging.info(f"Cloning repository {repo_url} ...")
        subprocess.run(cmd, check=True, capture_output=True, text=True, env=env)
        logging.info(f"Repository cloned to {dest_dir or 'current directory'}.")
        return f"Repository cloned to {dest_dir or 'current directory'}"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        logging.error("GIT CLONE ERROR: %s", error_msg)
        raise RuntimeError(
            f"Failed to clone repository: {error_msg}\n"
            "Check SSH auth and that the repository exists."
        )


def perform_git_setup(
    action: str,
    repo_url: str = "",
    branch: str = "",
    username: str = "",
    email: str = "",
    dest_dir: str = "",
    pat: str = "",
):
    """
    Entry point to perform git-related tasks with simple JSON responses.
    Actions:
      - 'generate_ssh_key' (requires email)
      - 'get_public_key'
      - 'add_ssh_key' (optionally PAT; returns manual steps if missing)
      - 'check_ssh_key_auth'/'check_ssh'
      - 'clone' (SSH URLs only)
    """
    if not is_git_installed():
        return {"status": "error", "message": "Git is not installed on this system."}

    try:
        # Dispatch by action and normalize the response shape
        if action == "generate_ssh_key":
            if not email:
                return {"status": "error", "message": "Email is required to generate SSH key."}
            result = generate_ssh_key(email)
            result["action"] = action
            result["details"] = {"email": email}
            return result

        elif action == "get_public_key":
            # Return a message that includes the key content for direct display
            msg = get_public_key()
            return {"status": "success", "action": action, "message": msg}

        elif action == "clone":
            if not repo_url:
                return {"status": "error", "message": "Repository URL is required for cloning."}
            msg = clone_repository_ssh(repo_url, dest_dir, branch)
            return {"status": "success", "action": action, "details": {"message": msg, "repo_url": repo_url, "branch": branch}}

        elif action == "add_ssh_key":
            # Read existing public key; require it to exist
            key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
            if not os.path.exists(key_path):
                return {"status": "error", "message": "SSH public key not found. Please generate it first."}
            with open(key_path, "r") as pubkey_file:
                pubkey = pubkey_file.read()

            if pat:
                # Add via API (handles duplicates gracefully)
                result_msg = add_ssh_key_to_github(pubkey, pat)
                status = "success"
                if "already exists" in result_msg.lower():
                    status = "warning"
                return {"status": status, "action": action, "details": {"message": result_msg}}
            else:
                # No PAT → return manual instructions in the response
                manual_msg = (
                    "Personal Access Token was not provided. Manual steps to add your SSH key to GitHub:\n"
                    "1. Run the following command to display your public key:\n"
                    "   cat ~/.ssh/id_rsa.pub\n"
                    "2. Copy the output.\n"
                    "3. Go to https://github.com/settings/ssh/new\n"
                    "4. Paste the key and save."
                )
                return {"status": "warning", "action": action, "details": {"message": manual_msg}}

        elif action == "check_ssh_key_auth":
            # Interactive-free auth check (BatchMode, accept-new)
            result = check_ssh_key_auth()
            return {"status": result.get("status", "error"), "action": action, "details": result}

        elif action == "check_ssh":
            # Alias of check_ssh_key_auth
            result = check_ssh_key_auth()
            return {"status": result.get("status", "error"), "action": action, "details": result}

        else:
            valid_actions = ['clone', 'generate_ssh_key', 'get_public_key', 'add_ssh_key', 'check_ssh_key_auth', 'check_ssh']
            return {"status": "error", "message": f"Unsupported action: {action}. Valid actions are: {', '.join(valid_actions)}"}
    except Exception as e:
        logging.error("Git setup error: %s", str(e))
        return {"status": "error", "action": action, "message": str(e)}


def add_ssh_key_to_github(pubkey: str, pat: str) -> str:
    """
    Add SSH public key to GitHub using the API and a Personal Access Token (PAT).
    Returns a concise human-readable message (not a JSON dict).
    """
    api_url = "https://api.github.com/user/keys"
    headers = {
        "Authorization": f"token {pat}",
        "Accept": "application/vnd.github+json"
    }
    data = {
        "title": "DevForge CLI Key",
        "key": pubkey.strip()  # normalize single-line key
    }
    response = requests.post(api_url, headers=headers, json=data)

    # Map common response codes to readable messages
    if response.status_code == 201:
        return "✅ SSH key added to your GitHub account via API."
    elif response.status_code == 422:
        # Handle duplicate/validation cleanly
        try:
            payload = response.json()
        except Exception:
            payload = {}
        if _is_github_duplicate_key_response(payload):
            return "⚠️ SSH key already exists on your GitHub account. Nothing to do."
        # If it already authenticates, treat as benign
        auth = check_ssh_key_auth()
        if auth.get("status") == "success":
            return "⚠️ SSH key already authorized with GitHub. Nothing to do."
        return "❌ Validation failed while adding SSH key."
    elif response.status_code == 401:
        return "❌ Unauthorized. Check your PAT and required scopes (admin:public_key)."
    else:
        return f"❌ Failed to add SSH key via API (HTTP {response.status_code})."


def setup_github_ssh_key(email: str, pat: str = None):
    """
    Convenience helper for interactive usage:
    - With PAT: attempts API add and prints the result string.
    - Without PAT: prints manual steps (no prompt).
    """
    key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
    if not os.path.exists(key_path):
        raise RuntimeError("SSH public key not found. Please generate it first.")

    with open(key_path, "r") as pubkey_file:
        pubkey = pubkey_file.read()

    if pat:
        result = add_ssh_key_to_github(pubkey, pat)
        print(result)
    else:
        # Print concise manual steps (no input() prompt)
        manual_msg = (
            "Personal Access Token was not provided. Manual steps to add your SSH key to GitHub:\n"
            "1. Run the following command to display your public key:\n"
            "   cat ~/.ssh/id_rsa.pub\n"
            "2. Go to https://github.com/settings/ssh/new\n"
            "3. Paste the key and save.\n"
        )
        print(manual_msg)
