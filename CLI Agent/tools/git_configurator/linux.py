import subprocess
import os
from pathlib import Path
import shutil
import logging
from urllib.parse import urlparse
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)


def is_git_installed() -> bool:
    """
    Check if Git is installed on the system.
    """
    return shutil.which("git") is not None


def configure_git_credentials(username: str, email: str):
    """
    Configure Git with user credentials locally, only if not already set.
    """
    if not username or not isinstance(username, str):
        raise ValueError("A valid Git username must be provided.")
    if not email or not isinstance(email, str) or "@" not in email:
        raise ValueError("A valid Git email address must be provided.")

    # Check current global config
    current_name = subprocess.run(
        ["git", "config", "--global", "--get", "user.name"],
        capture_output=True, text=True
    ).stdout.strip()
    current_email = subprocess.run(
        ["git", "config", "--global", "--get", "user.email"],
        capture_output=True, text=True
    ).stdout.strip()

    if current_name != username:
        subprocess.run(["git", "config", "--global", "user.name", username], check=True)
        logging.info(f"Set global git user.name to {username}")
    if current_email != email:
        subprocess.run(["git", "config", "--global", "user.email", email], check=True)
        logging.info(f"Set global git user.email to {email}")


def generate_ssh_key(email: str, key_path: str = "~/.ssh/id_rsa"):
    """
    Generate a new SSH key if it doesn't already exist.
    Only generates the key, does not add it to GitHub.
    """
    if not email or "@" not in email:
        raise ValueError("A valid email address is required to generate an SSH key.")
    key_path = os.path.expanduser(key_path)
    if not os.path.exists(key_path):
        logging.info("Generating a new SSH key...")
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", email,
            "-f", key_path, "-N", ""
        ], check=True)
        logging.info("SSH key generated successfully.")
    else:
        logging.info(f"SSH key already exists at: {key_path}")

    pub_key_path = key_path + ".pub"
    if not os.path.exists(pub_key_path):
        raise RuntimeError("Public key file not found after generation.")

    with open(pub_key_path, "r") as pubkey_file:
        pubkey = pubkey_file.read()
    logging.info("\nYour new SSH public key:\n")
    print(pubkey)
    return f"SSH key generated at {key_path}"


def add_ssh_key_to_github_or_manual(email: str, pat: str = None, key_path: str = "~/.ssh/id_rsa"):
    """
    Add SSH public key to GitHub using the API and a Personal Access Token (PAT).
    If PAT is not provided, return manual steps to add the key.
    """
    pub_key_path = os.path.expanduser(key_path) + ".pub"
    if not os.path.exists(pub_key_path):
        return {"status": "error", "message": "SSH public key not found. Please generate it first."}
    with open(pub_key_path, "r") as pubkey_file:
        pubkey = pubkey_file.read()
    if pat:
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
            return {"status": "success", "message": "✅ SSH key added to your GitHub account via API."}
        else:
            manual_msg = (
                f"❌ Failed to add SSH key via API: {response.text}\n"
                "Manual steps to add your SSH key to GitHub:\n"
                "1. Copy the public key below:\n"
                f"{pubkey}\n"
                "2. Go to https://github.com/settings/ssh/new\n"
                "3. Paste the key and save."
            )
            return {"status": "warning", "message": manual_msg}
    else:
        manual_msg = (
            "Manual steps to add your SSH key to GitHub:\n"
            "1. Copy the public key below:\n"
            f"{pubkey}\n"
            "2. Go to https://github.com/settings/ssh/new\n"
            "3. Paste the key and save."
        )
        return {"status": "success", "message": manual_msg}


def is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https"


def is_ssh_url(url: str) -> bool:
    """
    Check if the given URL is a valid SSH GitHub URL.
    """
    return url.startswith("git@github.com:")


def clone_repository_ssh(repo_url: str, dest_dir: str = None, branch: str = None):
    """
    Clone a GitHub repository using SSH.
    Checks for SSH key existence and authorization before cloning.
    Only SSH links are supported.
    """
    logging.info(f"Requested clone for repo: {repo_url} into {dest_dir or 'current directory'}")

    if not is_ssh_url(repo_url):
        logging.error(f"Unsupported repository URL format: {repo_url!r}")
        raise RuntimeError(
            "Only SSH GitHub links (git@github.com:...) are supported for cloning. "
            "Please provide a valid SSH URL."
        )

    key_path = os.path.expanduser("~/.ssh/id_rsa")
    pub_key_path = key_path + ".pub"
    if not os.path.exists(key_path) or not os.path.exists(pub_key_path):
        logging.error("SSH key not found. Please generate your SSH key first.")
        raise RuntimeError("SSH key not found. Please generate your SSH key before cloning.")

    # Check SSH authentication
    auth_result = check_ssh_key_auth()
    if auth_result["status"] != "success":
        logging.error(f"SSH authentication failed: {auth_result['message']}")
        manual_msg = (
            "Manual steps to add your SSH key to GitHub:\n"
            "1. Run the following command to display your public key:\n"
            "   cat ~/.ssh/id_rsa.pub\n"
            "2. Copy the output.\n"
            "3. Go to https://github.com/settings/ssh/new\n"
            "4. Paste the key and save."
        )
        raise RuntimeError(
            f"SSH key is not authorized with GitHub. {auth_result['message']}\n{manual_msg}"
        )

    # Proceed with cloning
    cmd = ["git", "clone", repo_url]
    if dest_dir:
        cmd.append(dest_dir)
    try:
        logging.info(f"Cloning repository {repo_url} ...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"Repository cloned to {dest_dir or 'current directory'}.")
        if branch:
            switch_branch(dest_dir or ".", branch)
        return f"Repository cloned to {dest_dir or 'current directory'}"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        logging.error("GIT CLONE ERROR: %s", error_msg)
        raise RuntimeError(
            f"Failed to clone repository: {error_msg}\n"
            "Check that your SSH key is authorized and the repository exists."
        )


def switch_branch(repo_path: str, branch: str):
    """
    Switch to an existing branch or create it if it doesn't exist.
    """
    if not repo_path or not branch:
        raise ValueError("Both repository path and branch name are required.")
    repo_path = Path(repo_path).expanduser().resolve()
    if not (repo_path / ".git").exists():
        raise Exception(f"{repo_path} is not a Git repository.")
    try:
        result = subprocess.run(
            ["git", "checkout", branch], cwd=repo_path,
            check=False, capture_output=True, text=True
        )
        if result.returncode != 0:
            subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=True)
        logging.info(f"Switched to branch '{branch}' in {repo_path}")
        return f"Switched to branch '{branch}' in {repo_path}"
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to switch branch: {e}")


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
    Entry point to perform git-related tasks. Handles pre-checks and executes action.
    Actions supported: 'clone', 'switch_branch', 'generate_ssh_key', 'add_ssh_key', 'check_ssh_key_auth'
    """
    if not is_git_installed():
        return {"status": "error", "message": "Git is not installed on this system."}

    try:
        if action == "generate_ssh_key":
            if not email:
                return {"status": "error", "message": "Email is required to generate SSH key."}
            msg = generate_ssh_key(email)
            return {"status": "success", "action": action, "details": {"message": msg, "email": email}}

        elif action == "clone":
            if not repo_url:
                return {"status": "error", "message": "Repository URL is required for cloning."}
            msg = clone_repository_ssh(repo_url, dest_dir, branch)
            return {"status": "success", "action": action, "details": {"message": msg, "repo_url": repo_url, "branch": branch}}

        elif action == "switch_branch":
            if not dest_dir or not branch:
                return {"status": "error", "message": "Both repo path and branch name are required."}
            configure_git_credentials(username, email)
            msg = switch_branch(dest_dir, branch)
            return {"status": "success", "action": action, "details": {"message": msg, "repo_path": dest_dir, "branch": branch}}

        elif action == "add_ssh_key":
            key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
            if not os.path.exists(key_path):
                return {"status": "error", "message": "SSH public key not found. Please generate it first."}
            with open(key_path, "r") as pubkey_file:
                pubkey = pubkey_file.read()
            if pat:
                result = add_ssh_key_to_github(pubkey, pat)
                return {"status": "success", "action": action, "details": {"message": result}}
            else:
                manual_msg = (
                "Manual steps to add your SSH key to GitHub:\n"
                "1. Run the following command to display your public key:\n"
                "   cat ~/.ssh/id_rsa.pub\n"
                "2. Copy the output.\n"
                "3. Go to https://github.com/settings/ssh/new\n"
                "4. Paste the key and save."
                )
                return {"status": "success", "action": action, "details": {"message": manual_msg}}

        elif action == "check_ssh_key_auth":
            result = check_ssh_key_auth()
            return {"status": result.get("status", "error"), "action": action, "details": result}

        else:
            valid_actions = ['clone', 'switch_branch', 'generate_ssh_key', 'add_ssh_key', 'check_ssh_key_auth']
            return {"status": "error", "message": f"Unsupported action: {action}. Valid actions are: {', '.join(valid_actions)}"}
    except Exception as e:
        logging.error("Git setup error: %s", str(e))
        return {"status": "error", "action": action, "message": str(e)}


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


def setup_github_ssh_key(email: str, pat: str = None):
    key_path = os.path.expanduser("~/.ssh/id_rsa.pub")
    if not os.path.exists(key_path):
        raise RuntimeError("SSH public key not found. Please generate it first.")
    with open(key_path, "r") as pubkey_file:
        pubkey = pubkey_file.read()
    if pat:
        result = add_ssh_key_to_github(pubkey, pat)
        print(result)
    else:
        print("\nManual steps to add your SSH key to GitHub:")
        print("1. Copy the public key below:")
        print(pubkey)
        print("2. Go to https://github.com/settings/ssh/new")
        print("3. Paste the key and save.")
        input("\nPress Enter after you have added the SSH key to your GitHub account...")


def check_ssh_key_auth() -> dict:
    """
    Check if the SSH key is authorized with GitHub.
    Returns a dict with status and message.
    """
    key_path = os.path.expanduser("~/.ssh/id_rsa")
    pub_key_path = key_path + ".pub"
    if not os.path.exists(key_path) or not os.path.exists(pub_key_path):
        return {"status": "error", "message": "SSH key not found. Please generate your SSH key first."}
    try:
        result = subprocess.run(
            ["ssh", "-T", "git@github.com"],
            capture_output=True, text=True, check=False 
        )
        output = (result.stdout + result.stderr).lower()
        # Treat "successfully authenticated" or "does not provide shell access" as success
        if "successfully authenticated" in output or "does not provide shell access" in output or "hi " in output:
            return {"status": "success", "message": "SSH key is correctly configured and connected to GitHub!"}
        else:
            return {"status": "warning", "message": result.stdout.strip() or result.stderr.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
