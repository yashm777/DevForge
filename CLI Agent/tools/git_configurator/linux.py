import subprocess
import os
from pathlib import Path
import shutil
import getpass
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


def prompt_git_credentials() -> tuple[str, str]:
    """
    Prompt the user for GitHub username and password/token securely.
    """
    username = input("Enter your GitHub username: ").strip()
    password = getpass.getpass("Enter your GitHub password or PAT (input hidden): ").strip()
    return username, password


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
    After generation, offer to add the public key to GitHub via API if PAT is provided,
    otherwise instruct the user to add it manually, then confirm and verify the key.
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

    # Ask if user has a GitHub PAT
    print("\nDo you have a GitHub Personal Access Token (PAT) with 'admin:public_key' scope?")
    pat = input("If yes, paste it here (leave blank if not): ").strip()

    if pat:
        # Try to add the key via GitHub API
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
            print("✅ SSH key added to your GitHub account via API.")
        else:
            print(f"❌ Failed to add SSH key via API: {response.text}")
            print("Please add the key manually as described below.")
            pat = ""  # fallback to manual
    if not pat:
        print("\nManual steps to add your SSH key to GitHub:")
        print("1. Copy the above public key.")
        print("2. Go to https://github.com/settings/ssh/new")
        print("3. Paste the key and save.")
        input("\nPress Enter after you have added the SSH key to your GitHub account...")

    # Verify SSH connection to GitHub
    try:
        logging.info("Verifying SSH key connection to GitHub...")
        result = subprocess.run(
            ["ssh", "-T", "git@github.com"],
            capture_output=True, text=True, check=True
        )
        output = result.stdout.lower() + result.stderr.lower()
        if "successfully authenticated" in output or "hi " in output:
            logging.info("✅ SSH key is correctly configured and connected to GitHub!")
            print("✅ SSH key is correctly configured and connected to GitHub!")
        else:
            logging.warning("SSH key verification output:\n%s", result.stdout.strip() or result.stderr.strip())
            print("⚠️ SSH key verification output:\n", result.stdout.strip() or result.stderr.strip())
    except subprocess.CalledProcessError as e:
        logging.error("SSH key verification failed. Details:\n%s", e.stderr or e.stdout)
        print("❌ SSH key verification failed. Details:\n", e.stderr or e.stdout)

    return f"SSH key generated at {key_path}"


def is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https"


def clone_repository(repo_url: str, dest_dir: str = None, branch: str = None):
    """
    Clone the given Git repository to the optional destination directory.
    Handles HTTPS and SSH cloning.
    For HTTPS cloning, prompts for username and token.
    For SSH cloning, on authentication failure, informs the user to add SSH key.
    """
    if not repo_url or not isinstance(repo_url, str):
        raise ValueError("A valid repository URL must be provided for cloning.")

    if is_https_url(repo_url):
        # HTTPS clone requires username and PAT/token
        username = input("Enter your GitHub username: ").strip()
        token = getpass.getpass("Enter your GitHub personal access token (input hidden): ").strip()
        auth_repo_url = repo_url.replace("https://", f"https://{username}:{token}@")
        cmd = ["git", "clone", auth_repo_url]
    else:
        # SSH clone
        cmd = ["git", "clone", repo_url]

    if dest_dir:
        cmd.append(dest_dir)

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logging.info(f"Repository cloned to {dest_dir or 'current directory'}.")
        if branch:
            switch_branch(dest_dir or ".", branch)
        return f"Repository cloned to {dest_dir or 'current directory'}"
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        if not is_https_url(repo_url) and ("permission denied (publickey)" in error_msg.lower() or "access denied" in error_msg.lower()):
            logging.error("SSH authentication failed. Please add your SSH public key to GitHub to clone private repos.")
        logging.error("GIT CLONE ERROR: %s", error_msg)
        raise RuntimeError(f"Failed to clone repository: {error_msg}")


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
):
    """
    Entry point to perform git-related tasks. Handles pre-checks and executes action.
    Actions supported: 'clone', 'switch_branch', 'generate_ssh_key'
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
            # Optionally support branch cloning
            msg = clone_repository(repo_url, dest_dir, branch) if branch else clone_repository(repo_url, dest_dir)
            return {"status": "success", "action": action, "details": {"message": msg, "repo_url": repo_url, "branch": branch}}

        elif action == "switch_branch":
            if not dest_dir or not branch:
                return {"status": "error", "message": "Both repo path and branch name are required."}
            # Optionally prompt for credentials if needed
            if not username or not email:
                username, email = prompt_git_credentials()
            configure_git_credentials(username, email)
            msg = switch_branch(dest_dir, branch)
            return {"status": "success", "action": action, "details": {"message": msg, "repo_path": dest_dir, "branch": branch}}

        else:
            valid_actions = ['clone', 'switch_branch', 'generate_ssh_key']
            return {"status": "error", "message": f"Unsupported action: {action}. Valid actions are: {', '.join(valid_actions)}"}
    except Exception as e:
        return {"status": "error", "action": action, "message": str(e)}
