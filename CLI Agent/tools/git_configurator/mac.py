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

def configure_git_credentials(username: str, email: str, global_config: bool = True):
    """
    Configure Git with user credentials.
    Set `global_config=False` for local repository config only.
    """
    config_scope = "--global" if global_config else "--local"
    print(f"Configuring Git credentials ({config_scope})...")
    subprocess.run(["git", "config", config_scope, "user.name", username], check=True)
    subprocess.run(["git", "config", config_scope, "user.email", email], check=True)

def generate_ssh_key(email: str, key_path: str = "~/.ssh/id_rsa"):
    """
    Generate a new SSH key if it doesn't already exist.
    """
    key_path = os.path.expanduser(key_path)
    ssh_dir = os.path.dirname(key_path)

    if not os.path.exists(key_path):
        print("Generating a new SSH key...")
        os.makedirs(ssh_dir, exist_ok=True)
        subprocess.run([
            "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", email,
            "-f", key_path, "-N", ""
        ], check=True)
        print(f"SSH key generated successfully at {key_path}.")
    else:
        print("SSH key already exists at:", key_path)

    # Optional: Print public key location
    pub_key = key_path + ".pub"
    if os.path.exists(pub_key):
        print("Public key location:", pub_key)

def clone_repository(repo_url: str, dest_dir: str = None, branch: str = None):
    """
    Clone the given Git repository to the optional destination directory and optionally checkout a specific branch.
    """
    cmd = ["git", "clone"]
    if branch:
        cmd.extend(["-b", branch])
    cmd.append(repo_url)
    if dest_dir:
        cmd.append(dest_dir)

    print(f"Cloning repository from {repo_url}...")
    subprocess.run(cmd, check=True)
    print("Clone successful.")

def switch_branch(repo_path: str, branch: str):
    """
    Switch to an existing branch or create it if it doesn't exist.
    """
    repo_path = Path(repo_path).expanduser().resolve()
    if not (repo_path / ".git").exists():
        raise FileNotFoundError(f"{repo_path} is not a Git repository.")

    print(f"Switching to branch: {branch}")
    result = subprocess.run(["git", "rev-parse", "--verify", branch], cwd=repo_path, capture_output=True)
    if result.returncode != 0:
        print(f"Branch '{branch}' does not exist. Creating it...")
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
    if not is_git_installed():
        raise EnvironmentError("Git is not installed on this macOS system. Please install it using Homebrew.")

    if action in ["clone", "switch_branch", "generate_ssh_key"]:
        if not username:
            username = input("Enter your GitHub username: ").strip()
        if not email:
            email = input("Enter your GitHub email: ").strip()

        configure_git_credentials(username, email, global_config=global_config)

    if action == "generate_ssh_key":
        generate_ssh_key(email)
    elif action == "clone":
        if not repo_url:
            raise ValueError("Repository URL is required for cloning.")
        clone_repository(repo_url, dest_dir, branch)
    elif action == "switch_branch":
        if not dest_dir or not branch:
            raise ValueError("Both repo path and branch name are required.")
        switch_branch(dest_dir, branch)
    else:
        raise ValueError(f"Unsupported action: {action}")
