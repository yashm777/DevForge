import unittest
from unittest.mock import patch, call
from tools.git_configurator.mac import (
    is_git_installed,
    clone_repository,
    generate_ssh_key,
    switch_branch,
    configure_git_credentials,
    perform_git_setup,
)
import subprocess
from pathlib import Path

class TestGitConfiguratorMac(unittest.TestCase):
    # Test if is_git_installed returns True when git is found
    @patch("subprocess.run")
    def test_is_git_installed_true(self, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(is_git_installed())
        mock_run.assert_called_with(["which", "git"], capture_output=True, text=True)

    # Test if is_git_installed returns False when git is not found
    @patch("subprocess.run")
    def test_is_git_installed_false(self, mock_run):
        mock_run.return_value.returncode = 1
        self.assertFalse(is_git_installed())

    # Test cloning a repository with a specific branch and destination directory
    @patch("subprocess.run")
    def test_clone_repository_with_branch_and_dest(self, mock_run):
        clone_repository("https://github.com/example/repo.git", dest_dir="repo", branch="main")
        mock_run.assert_called_with(
            ["git", "clone", "-b", "main", "https://github.com/example/repo.git", "repo"], check=True
        )

    # Test cloning a repository with minimal arguments
    @patch("subprocess.run")
    def test_clone_repository_minimal(self, mock_run):
        clone_repository("https://github.com/example/repo.git")
        mock_run.assert_called_with(["git", "clone", "https://github.com/example/repo.git"], check=True)
    
    # Test generate_ssh_key skips key generation if key already exists
    @patch("os.path.exists", side_effect=[True, True])
    @patch("subprocess.run")
    def test_generate_ssh_key_skips_if_exists(self, mock_run, _):
        key_path = Path.home() / ".ssh" / "test_id_rsa"
        generate_ssh_key("test@example.com", str(key_path))
        mock_run.assert_not_called()

    # Test generate_ssh_key creates a new key if it does not exist
    @patch("os.path.exists", return_value=False)
    @patch("os.makedirs")
    @patch("subprocess.run")
    def test_generate_ssh_key_creates_key(self, mock_run, mock_makedirs, _):
        key_path = Path.home() / ".ssh" / "test_id_rsa"
        generate_ssh_key("test@example.com", key_path=str(key_path))
        mock_makedirs.assert_called()
        mock_run.assert_called_with(
            [
                "ssh-keygen", "-t", "rsa", "-b", "4096", "-C", "test@example.com",
                "-f", str(key_path), "-N", ""
                ],
            check=True
            )

    # Test configuring git credentials globally
    @patch("subprocess.run")
    def test_configure_git_credentials_global(self, mock_run):
        configure_git_credentials("Nishal", "nishal@example.com", global_config=True)
        expected_calls = [
            call(["git", "config", "--global", "user.name", "Nishal"], check=True),
            call(["git", "config", "--global", "user.email", "nishal@example.com"], check=True)
        ]
        mock_run.assert_has_calls(expected_calls, any_order=False)

    # Test perform_git_setup for cloning when git is installed
    @patch("subprocess.run")
    @patch("tools.git_configurator.mac.is_git_installed", return_value=True)
    @patch("builtins.input", side_effect=["Nishal", "nishal@example.com"])
    def test_perform_git_setup_clone(self, _, __, mock_run):
        perform_git_setup(
            action="clone",
            repo_url="https://github.com/example/repo.git",
            branch="main",
            dest_dir="repo"
        )
        self.assertTrue(mock_run.called)
        self.assertTrue(any("clone" in str(c.args[0]) for c in mock_run.call_args_list))

    # Test perform_git_setup raises error if git is not installed
    @patch("tools.git_configurator.mac.is_git_installed", return_value=False)
    def test_perform_git_setup_git_not_installed(self, _):
        with self.assertRaises(EnvironmentError):
            perform_git_setup(action="clone", repo_url="x")

    # Test switch_branch raises FileNotFoundError for invalid repo path
    def test_switch_branch_invalid_repo(self):
        with self.assertRaises(FileNotFoundError):
            switch_branch("/invalid/path", "newbranch")

    # Test switch_branch creates a new branch if it does not exist
    @patch("subprocess.run")
    @patch("tools.git_configurator.mac.Path.exists", side_effect=[True, False])
    def test_switch_branch_create_if_not_exist(self, _, mock_run):
        switch_branch("some/repo", "newbranch")
        self.assertIn(
            call(["git", "checkout", "-b", "newbranch"], cwd=unittest.mock.ANY, check=True),
            mock_run.mock_calls
        )

    # Test switch_branch checks out an existing branch
    @patch("subprocess.run")
    @patch("tools.git_configurator.mac.Path.exists", side_effect=[True, True])
    def test_switch_branch_existing_branch(self, _, mock_run):
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(args=[], returncode=0),
        ]
        switch_branch("repo", "main")
        mock_run.assert_any_call(["git", "checkout", "main"], cwd=unittest.mock.ANY, check=True)
