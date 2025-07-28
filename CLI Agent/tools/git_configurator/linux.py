import subprocess
import os
from pathlib import Path
import shutil
import getpass


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
    if current_email != email:
        subprocess.run(["git", "config", "--global", "user.email", email], check=True)


def generate_ssh_key(email: str, key_path: str = "~/.ssh/id_rsa"):
    """
    Generate a new SSH key if it doesn't already exist.
    """
    if not ensure_ssh_keygen_installed():
        raise RuntimeError("ssh-keygen is not installed and could not be installed automatically. Please install it manually with 'sudo apt install openssh-client'.")

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
        pub_key_path = key_path + ".pub"
        if os.path.exists(pub_key_path):
            with open(pub_key_path, "r") as pubkey_file:
                pubkey = pubkey_file.read()
            print("\nYour new SSH public key:\n")
            print(pubkey)
            print("\nCopy this key and add it to your GitHub SSH keys: https://github.com/settings/keys")
        return f"SSH key generated at {key_path}"
    else:
        print("SSH key already exists at:", key_path)
        return f"SSH key already exists at {key_path}"


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
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if branch:
            switch_branch(dest_dir or ".", branch)
        return f"Repository cloned to {dest_dir or 'current directory'}"
    except subprocess.CalledProcessError as e:
        print("GIT CLONE ERROR:", e.stderr or e.stdout)
        raise RuntimeError(f"Failed to clone repository: {e.stderr or e.stdout}")


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
        result = subprocess.run(["git", "checkout", branch], cwd=repo_path, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            subprocess.run(["git", "checkout", "-b", branch], cwd=repo_path, check=True)
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


def ensure_ssh_keygen_installed():
    """
    Ensure ssh-keygen is installed. If not, try to install it (Ubuntu/Debian only).
    """
    if shutil.which("ssh-keygen") is not None:
        return True
    try:
        print("ssh-keygen not found. Attempting to install openssh-client...")
        subprocess.run(
            ["sudo", "apt-get", "update"], check=True
        )
        subprocess.run(
            ["sudo", "apt-get", "install", "-y", "openssh-client"], check=True
        )
        return shutil.which("ssh-keygen") is not None
    except Exception as e:
        print(f"Failed to install openssh-client: {e}")
        return False