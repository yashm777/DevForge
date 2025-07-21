import unittest
from unittest.mock import patch, MagicMock
from tools.git_configurator.linux import (
    is_git_installed,
    clone_repository,
    generate_ssh_key,
    switch_branch,
)
from pathlib import Path

class TestGitConfiguratorLinux(unittest.TestCase):

    @patch("subprocess.run")
    def test_is_git_installed_true(self, mock_run):
        mock_run.return_value.returncode = 0
        self.assertTrue(is_git_installed())

    @patch("subprocess.run")
    def test_is_git_installed_false(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        self.assertFalse(is_git_installed())

    @patch("builtins.input", return_value="https://github.com/example/repo.git")
    @patch("subprocess.run")
    def test_clone_repository_success(self, mock_run, mock_input):
        mock_run.return_value.returncode = 0
        clone_repository("https://github.com/example/repo.git", branch="main")
        mock_run.assert_called()

    @patch("getpass.getpass", return_value="testpassword")
    @patch("builtins.input", return_value="testuser")
    def test_generate_ssh_key(self, mock_input, mock_getpass):
        with patch("os.path.exists", return_value=False), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            generate_ssh_key("testuser", "test@example.com")
            self.assertTrue(mock_run.called)

    @patch("pathlib.Path.exists", return_value=True)
    @patch("subprocess.run")
    def test_switch_branch(self, mock_run, mock_exists):
       mock_run.return_value.returncode = 0
       switch_branch("/tmp", "main")
       self.assertTrue(mock_run.called)

if __name__ == "__main__":
    unittest.main()
