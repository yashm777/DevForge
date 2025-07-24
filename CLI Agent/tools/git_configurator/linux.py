import subprocess
import os
import getpass
from pathlib import Path


def is_git_installed() -> bool:
    """
    Check if Git is installed on the system.
    """
    try:
        result = subprocess.run(["which", "git"], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        # The 'which' command itself not found, treat as git not installed
        return False


def prompt_git_credentials() -> tuple[str, str]:
    """
    Prompt the user for GitHub username and password securely.
    """
    username = input("Enter your GitHub username: ").strip()
    password = getpass.getpass("Enter your GitHub password or PAT (hidden): ").strip()
    return username, password


def configure_git_credentials(username: str, email: str):
    """
    Configure Git with user credentials locally.
    """
    if not username or not isinstance(username, str):
        raise ValueError("A valid Git username must be provided.")
    if not email or not isinstance(email, str) or "@" not in email:
        raise ValueError("A valid Git email address must be provided.")
    subprocess.run(["git", "config", "--global", "user.name", username], check=True)
    subprocess.run(["git", "config", "--global", "user.email", email], check=True)


def generate_ssh_key(email: str, key_path: str = "~/.ssh/id_rsa"):
    """
    Generate a new SSH key if it doesn't already exist.
    """
    if not email or "@" not in email:
        raise ValueError("A valid email address is required to generate an SSH key.")
    key_path = os.path.expanduser(key_path)
    if not os.path.exists(key_path):
        print("Generating a new SSH key...")
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", email,
            "-f", key_path, "-N", ""
        ], check=True)
        print("SSH key generated successfully.")
    else:
        print("SSH key already exists at:", key_path)


def clone_repository(repo_url: str, dest_dir: str = None, branch: str = None):
    """
    Clone the given Git repository to the optional destination directory.
    """
    if not repo_url or not isinstance(repo_url, str) or not repo_url.startswith("http"):
        raise ValueError("A valid repository URL must be provided for cloning.")
    cmd = ["git", "clone", repo_url]
    if dest_dir:
        cmd.append(dest_dir)
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to clone repository: {e}")


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
        subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=False)
        subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True)
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
        raise EnvironmentError("Git is not installed on this system.")

    if not username:
        username = input("Enter your GitHub username: ").strip()
    if not email:
        email = input("Enter your GitHub email: ").strip()

    # Configure Git globally
    configure_git_credentials(username, email)

    if action == "generate_ssh_key":
        generate_ssh_key(email)
    elif action == "clone":
        if not repo_url:
            raise ValueError("Repository URL is required for cloning.")
        clone_repository(repo_url, dest_dir)
    elif action == "switch_branch":
        if not dest_dir or not branch:
            raise ValueError("Both repo path and branch name are required.")
        switch_branch(dest_dir, branch)
    else:
        raise ValueError(f"Unsupported action: {action}")
