import os
import pytest
from tools.system_config import windows

# Test check_env_variable
def test_check_env_variable_existing():
    os.environ["TEST_VAR"] = "TestValue"
    result = windows.check_env_variable("TEST_VAR")
    assert result["status"] == "success"
    assert result["variable"] == "TEST_VAR"
    assert result["value"] == "TestValue"

def test_check_env_variable_missing():
    if "NON_EXISTENT_VAR" in os.environ:
        del os.environ["NON_EXISTENT_VAR"]
    result = windows.check_env_variable("NON_EXISTENT_VAR")
    assert result["status"] == "error"

# Test set_env_variable
def test_set_env_variable():
    result = windows.set_env_variable("PYTEST_VAR", "HelloWorld")
    assert result["status"] == "success"
    assert result["variable"] == "PYTEST_VAR"
    assert result["value"] == "HelloWorld"

# Test remove_env_variable
def test_remove_env_variable():
    windows.set_env_variable("REMOVE_ME_VAR", "DeleteThis")
    result = windows.remove_env_variable("REMOVE_ME_VAR")
    assert result["status"] == "success"

#  Test append_to_path
def test_append_to_path():
    new_path = "C:\\TestPath"
    result = windows.append_to_path(new_path)
    assert result["status"] in ["success", "info"]

def test_remove_from_path():
    new_path = "C:\\TestPath"
    windows.append_to_path(new_path)
    result = windows.remove_from_path(new_path)
    assert result["status"] in ["success", "info"]

#  Test is_port_open (for common port like 80 or a random port)
def test_is_port_open_free_port():
    result = windows.is_port_open(54321)  # unlikely to be used
    assert result["status"] in ["free", "in_use"]

#  Test is_service_running
def test_is_service_running_valid():
    # Windows Update service (wuauserv) usually exists
    result = windows.is_service_running("wuauserv")
    assert result["status"] in ["running", "not_running"]

def test_is_service_running_invalid():
    result = windows.is_service_running("fake123service")
    assert result["status"] == "error"

# Test list_env_variables
def test_list_env_variables():
    result = windows.list_env_variables()
    assert result["status"] == "success"
    assert isinstance(result["variables"], dict)