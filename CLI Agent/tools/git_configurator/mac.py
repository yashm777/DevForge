import subprocess
import os
import getpass
from pathlib import Path
import shutil
import stat
import logging

# Configure logging
logger = logging.getLogger("git_configurator")
logging.basicConfig(level=logging.INFO, format="%(message)s")

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
    config_scope = "--global" if global_config else "--local"
    if verbose:
        logger.info(f"Configuring Git credentials ({config_scope})...")
    subprocess.run(["git", "config", config_scope, "user.name", username], check=True)
    subprocess.run(["git", "config", config_scope, "user.email", email], check=True)

def generate_ssh_key(email: str, key_path: str = "~/.ssh/id_rsa", verbose: bool = True):
    """
    Generate a new SSH key if it doesn't already exist.
    """
    key_path = os.path.expanduser(key_path)
    ssh_dir = os.path.dirname(key_path)

    if not os.path.exists(key_path):
        if verbose:
            logger.info("Generating a new SSH key...")
        os.makedirs(ssh_dir, exist_ok=True)
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", email,
            "-f", key_path, "-N", ""
        ], check=True)
        # Set permissions
        os.chmod(ssh_dir, 0o700)
        os.chmod(key_path, 0o600)
        if verbose:
            logger.info(f"SSH key generated successfully at {key_path}.")
    else:
        if verbose:
            logger.info(f"SSH key already exists at: {key_path}")

    pub_key = key_path + ".pub"
    if os.path.exists(pub_key) and verbose:
        with open(pub_key, "r") as pubkey_file:
            pubkey = pubkey_file.read()
        logger.info("\nYour new SSH public key:\n")
        logger.info(pubkey)
        logger.info("\nCopy this key and add it to your GitHub SSH keys: https://github.com/settings/keys")

def clone_repository(repo_url: str, dest_dir: str = None, branch: str = None, verbose: bool = True):
    cmd = ["git", "clone"]
    if branch:
        cmd.extend(["-b", branch])
    cmd.append(repo_url)
    if dest_dir:
        cmd.append(dest_dir)
    if verbose:
        logger.info(f"Cloning repository from {repo_url}...")
    try:
        subprocess.run(cmd, check=True)
        if verbose:
            logger.info("Clone successful.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error cloning repository: {e}")
        raise

def switch_branch(repo_path: str, branch: str, verbose: bool = True):
    """
    Switch to an existing branch or create it if it doesn't exist.
    """
    repo_path = Path(repo_path).expanduser().resolve()
    if not (repo_path / ".git").exists():
        raise FileNotFoundError(f"{repo_path} is not a Git repository.")

    if verbose:
        logger.info(f"Switching to branch: {branch}")
    result = subprocess.run(["git", "rev-parse", "--verify", branch], cwd=repo_path, capture_output=True)
    if result.returncode != 0:
        if verbose:
            logger.info(f"Branch '{branch}' does not exist. Creating it...")
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
    global_config: bool = True,
):
    """
    Entry point to perform git-related tasks. Handles pre-checks and executes action.
    Actions supported: 'clone', 'switch_branch', 'generate_ssh_key'
    """
    ensure_git_installed()

    if action == "generate_ssh_key":
        if not email:
            email = input("Enter your GitHub email: ").strip()
        generate_ssh_key(email)
    elif action == "clone":
        if not repo_url:
            raise ValueError("Repository URL is required for cloning.")
        clone_repository(repo_url, dest_dir, branch)
    elif action == "switch_branch":
        if not dest_dir or not branch:
            raise ValueError("Both repo path and branch name are required.")
        if not username:
            username = input("Enter your GitHub username: ").strip()
        if not email:
            email = input("Enter your GitHub email: ").strip()
        configure_git_credentials(username, email, global_config=global_config)
        switch_branch(dest_dir, branch)
    else:
        raise ValueError(f"Unsupported action: {action}")

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