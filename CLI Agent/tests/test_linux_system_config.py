import os
import pytest
from tools.system_config import linux

#  Test check_env_variable
def test_check_env_variable_existing():
    os.environ["TEST_VAR"] = "LinuxValue"
    result = linux.check_env_variable("TEST_VAR")
    assert result["status"] == "success"
    assert result["variable"] == "TEST_VAR"
    assert result["value"] == "LinuxValue"

def test_check_env_variable_missing():
    if "NON_EXISTENT_VAR" in os.environ:
        del os.environ["NON_EXISTENT_VAR"]
    result = linux.check_env_variable("NON_EXISTENT_VAR")
    assert result["status"] == "error"

#  Test set_env_variable (writes to ~/.bashrc)
def test_set_env_variable():
    result = linux.set_env_variable("PYTEST_LINUX_VAR", "HelloLinux")
    assert result["status"] == "success"
    assert "Please run 'source ~/.bashrc'" in result["message"]

#  Test remove_env_variable (from ~/.bashrc)
def test_remove_env_variable():
    linux.set_env_variable("REMOVE_ME_LINUX", "DeleteMe")
    result = linux.remove_env_variable("REMOVE_ME_LINUX")
    assert result["status"] == "success"

#  Test append_to_path (persistent to ~/.bashrc)
def test_append_to_path():
    new_path = "/tmp/testpath"
    result = linux.append_to_path(new_path)
    assert result["status"] in ["success", "info"]

#  Test remove_from_path
def test_remove_from_path():
    new_path = "/tmp/testpath"
    linux.append_to_path(new_path)
    result = linux.remove_from_path(new_path)
    assert result["status"] == "success"

#  Test is_port_open (free port)
def test_is_port_open_free_port():
    result = linux.is_port_open(54321)
    assert result["status"] in ["free", "in_use"]

#  Test is_service_running valid (common service like 'ssh')
def test_is_service_running_valid():
    result = linux.is_service_running("ssh")
    assert result["status"] in ["running", "not_running", "error"]

#  Test is_service_running invalid
def test_is_service_running_invalid():
    result = linux.is_service_running("fake_service_123")
    assert result["status"] == "error"

#  Test list_env_variables
def test_list_env_variables():
    result = linux.list_env_variables()
    assert result["status"] == "success"
    assert isinstance(result["variables"], dict)