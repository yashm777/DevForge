import subprocess
import os
import getpass
from pathlib import Path

def is_git_installed() -> bool:
    """
    Check if Git is installed on macOS using 'which'.
    """
    result = subprocess.run(["which", "git"], capture_output=True, text=True)
    return result.returncode == 0

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
    subprocess.run(["git", "config", "--global", "user.name", username], check=True)
    subprocess.run(["git", "config", "--global", "user.email", email], check=True)

def generate_ssh_key(email: str, key_path: str = "~/.ssh/id_rsa"):
    """
    Generate a new SSH key if it doesn't already exist.
    """
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

def clone_repository(repo_url: str, dest_dir: str = None):
    """
    Clone the given Git repository to the optional destination directory.
    """
    cmd = ["git", "clone", repo_url]
    if dest_dir:
        cmd.append(dest_dir)
    subprocess.run(cmd, check=True)

def switch_branch(repo_path: str, branch: str):
    """
    Switch to an existing branch or create it if it doesn't exist.
    """
    repo_path = Path(repo_path).expanduser().resolve()
    if not (repo_path / ".git").exists():
        raise Exception(f"{repo_path} is not a Git repository.")

    subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=False)
    subprocess.run(["git", "checkout", branch], cwd=repo_path, check=True)

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
        raise EnvironmentError("Git is not installed on this macOS system. Please install it using Homebrew.")

    if not username:
        username = input("Enter your GitHub username: ").strip()
    if not email:
        email = input("Enter your GitHub email: ").strip()

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
