import subprocess
import os
import getpass
from pathlib import Path
import shutil
import stat
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
    Check if Git is installed on macOS using 'which'.
    """
    return shutil.which("git") is not None

def ensure_git_installed():
    if not is_git_installed():
        raise EnvironmentError(
            "Git is not installed on this macOS system.\n"
            "Install it using Homebrew:\n"
            "    brew install git"
        )

def prompt_git_credentials() -> tuple[str, str]:
    """
    Prompt the user for GitHub username and password/token securely.
    Note: For SSH-based setup, password/token is not required.
    """
    username = input("Enter your GitHub username: ").strip()
    password = getpass.getpass("Enter your GitHub password or PAT (input hidden, not required for SSH setup): ").strip()
    return username, password

def configure_git_credentials(username: str, email: str, global_config: bool = True, verbose: bool = True):
    """
    Configure Git with user credentials.
    Set `global_config=False` for local repository config only.
    """
    if not username or not isinstance(username, str):
        raise ValueError("A valid Git username must be provided.")
    if not email or not isinstance(email, str) or "@" not in email:
        raise ValueError("A valid Git email address must be provided.")
    
    config_scope = "--global" if global_config else "--local"
    if verbose:
        logging.info(f"Configuring Git credentials ({config_scope})...")
    
    # Check current config to avoid unnecessary changes
    current_name = subprocess.run(
        ["git", "config", config_scope, "--get", "user.name"],
        capture_output=True, text=True
    ).stdout.strip()
    current_email = subprocess.run(
        ["git", "config", config_scope, "--get", "user.email"],
        capture_output=True, text=True
    ).stdout.strip()

    if current_name != username:
        subprocess.run(["git", "config", config_scope, "user.name", username], check=True)
        if verbose:
            logging.info(f"Set git user.name to {username}")
    if current_email != email:
        subprocess.run(["git", "config", config_scope, "user.email", email], check=True)
        if verbose:
            logging.info(f"Set git user.email to {email}")

def generate_ssh_key(email: str, key_path: str = "~/.ssh/id_rsa", verbose: bool = True):
    """
    Generate a new SSH key if it doesn't already exist.
    Only generates the key, does not add it to GitHub.
    """
    if not email or "@" not in email:
        raise ValueError("A valid email address is required to generate an SSH key.")
    
    key_path = os.path.expanduser(key_path)
    ssh_dir = os.path.dirname(key_path)

    if not os.path.exists(key_path):
        if verbose:
            logging.info("Generating a new SSH key...")
        os.makedirs(ssh_dir, exist_ok=True)
        
        # Use proper input/output handling to avoid SIGPIPE issues
        result = subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", email,
            "-f", key_path, "-N", ""
        ], capture_output=True, text=True, check=True)
        
        # Set permissions
        os.chmod(ssh_dir, 0o700)
        os.chmod(key_path, 0o600)
        if verbose:
            logging.info(f"SSH key generated successfully at {key_path}.")
    else:
        if verbose:
            logging.info(f"SSH key already exists at: {key_path}")

    pub_key_path = key_path + ".pub"
    if not os.path.exists(pub_key_path):
        raise RuntimeError("Public key file not found after generation.")

    if os.path.exists(pub_key_path) and verbose:
        with open(pub_key_path, "r") as pubkey_file:
            pubkey = pubkey_file.read()
        logging.info("\nYour new SSH public key:\n")
        print(pubkey)
        logging.info("\nCopy this key and add it to your GitHub SSH keys: https://github.com/settings/keys")
    
    return f"SSH key generated at {key_path}"

def is_https_url(url: str) -> bool:
    """Check if the given URL is an HTTPS URL."""
    parsed = urlparse(url)
    return parsed.scheme == "https"


def is_ssh_url(url: str) -> bool:
    """Check if the given URL is a valid SSH GitHub URL."""
    return url.startswith("git@github.com:")


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
        # GitHub SSH test returns exit code 1 even on successful auth, so check the message content
        if "successfully authenticated" in output or "does not provide shell access" in output or "hi " in output:
            return {"status": "success", "message": "SSH key authentication successful! You're connected to GitHub."}
        elif "permission denied" in output:
            return {"status": "error", "message": "SSH key authentication failed. The key may not be added to GitHub or is incorrect."}
        else:
            # Show the actual output for debugging, but mark as warning since it's unclear
            actual_output = result.stdout.strip() or result.stderr.strip()
            return {"status": "warning", "message": f"Unclear SSH authentication result: {actual_output}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to test SSH authentication: {str(e)}"}


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
        return "SSH key added to your GitHub account via API."
    else:
        return f"Failed to add SSH key via API: {response.text}"


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
            return {"status": "success", "message": "SSH key added to your GitHub account via API."}
        else:
            manual_msg = (
                f"Failed to add SSH key via API: {response.text}\n"
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
        return f"Repository cloned to {dest_dir or 'current directory'}"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        logging.error("GIT CLONE ERROR: %s", error_msg)
        raise RuntimeError(
            f"Failed to clone repository: {error_msg}\n"
            "Check that your SSH key is authorized and the repository exists."
        )


def clone_repository(repo_url: str, dest_dir: str = None, branch: str = None, verbose: bool = True):
    """Legacy clone function - redirects to SSH clone for better security."""
    cmd = ["git", "clone"]
    if branch:
        cmd.extend(["-b", branch])
    cmd.append(repo_url)
    if dest_dir:
        cmd.append(dest_dir)
    if verbose:
        logging.info(f"Cloning repository from {repo_url}...")
    try:
        subprocess.run(cmd, check=True)
        if verbose:
            logging.info("Clone successful.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error cloning repository: {e}")
        raise

def switch_branch(repo_path: str, branch: str, verbose: bool = True):
    """
    Switch to an existing branch or create it if it doesn't exist.
    """
    repo_path = Path(repo_path).expanduser().resolve()
    if not (repo_path / ".git").exists():
        raise FileNotFoundError(f"{repo_path} is not a Git repository.")

    if verbose:
        logging.info(f"Switching to branch: {branch}")
    result = subprocess.run(["git", "rev-parse", "--verify", branch], cwd=repo_path, capture_output=True)
    if result.returncode != 0:
        if verbose:
            logging.info(f"Branch '{branch}' does not exist. Creating it...")
        subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=True)
    else:
        subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True)

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
    Actions supported: 'clone', 'generate_ssh_key', 'add_ssh_key', 'check_ssh_key_auth'
    """
    if not is_git_installed():
        return {"status": "error", "message": "Git is not installed on this macOS system."}

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

        elif action == "switch_branch":
            if not dest_dir or not branch:
                return {"status": "error", "message": "Both repo path and branch name are required."}
            if not username:
                return {"status": "error", "message": "GitHub username is required."}
            if not email:
                return {"status": "error", "message": "GitHub email is required."}
            configure_git_credentials(username, email, global_config=True)
            switch_branch(dest_dir, branch)
            return {"status": "success", "action": action, "details": {"message": f"Switched to branch {branch}", "branch": branch}}

        else:
            valid_actions = ['clone', 'generate_ssh_key', 'add_ssh_key', 'check_ssh_key_auth', 'switch_branch']
            return {"status": "error", "message": f"Unsupported action: {action}. Valid actions are: {', '.join(valid_actions)}"}
    except Exception as e:
        logging.error("Git setup error: %s", str(e))
        return {"status": "error", "action": action, "message": str(e)}

def setup_github_ssh_key(email: str, pat: str = None):
    """Setup GitHub SSH key with optional PAT for automatic addition."""
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


def setup_clone(repo_url: str, dest_dir: str = None, branch: str = None, verbose: bool = True):
    ensure_git_installed()
    if not repo_url:
        raise ValueError("Repository URL is required for cloning.")
    clone_repository(repo_url, dest_dir, branch, verbose=verbose)

def setup_switch_branch(dest_dir: str, branch: str, username: str = "", email: str = "", global_config: bool = True, verbose: bool = True):
    ensure_git_installed()
    if not dest_dir or not branch:
        raise ValueError("Both repo path and branch name are required.")
    if not username:
        username = input("Enter your GitHub username: ").strip()
    if not email:
        email = input("Enter your GitHub email: ").strip()
    configure_git_credentials(username, email, global_config=global_config, verbose=verbose)
    switch_branch(dest_dir, branch, verbose=verbose)

def setup_generate_ssh_key(email: str, verbose: bool = True):
    ensure_git_installed()
    if not email:
        email = input("Enter your GitHub email: ").strip()
    generate_ssh_key(email, verbose=verbose)