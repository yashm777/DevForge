import pytest
import requests
import time

MCP_SERVER_URL = "http://localhost:8000/mcp/"

@pytest.fixture(scope="session", autouse=True)
def wait_for_server():
    # Wait for the MCP server to be up before running tests
    for _ in range(10):
        try:
            resp = requests.post(MCP_SERVER_URL, json={"method": "info://server", "params": {}, "id": 1})
            if resp.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    pytest.fail("MCP server did not start in time.")

def test_git_clone_missing_repo_url():
    payload = {
        "method": "tool_action_wrapper",
        "params": {
            "task": "git_setup",
            "action": "clone"
            # repo_url is missing
        },
        "id": 2
    }
    resp = requests.post(MCP_SERVER_URL, json=payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["status"] == "error"
    assert "repo_url" in data["message"]

def test_git_generate_ssh_key_missing_email():
    payload = {
        "method": "tool_action_wrapper",
        "params": {
            "task": "git_setup",
            "action": "generate_ssh_key"
            # email is missing
        },
        "id": 3
    }
    resp = requests.post(MCP_SERVER_URL, json=payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["status"] == "error"
    assert "email" in data["message"]

def test_git_clone_with_repo_url():
    # This test uses a public repo and a temp directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        payload = {
            "method": "tool_action_wrapper",
            "params": {
                "task": "git_setup",
                "action": "clone",
                "repo_url": "https://github.com/git/git.git",
                "dest_dir": tmpdir
            },
            "id": 4
        }
        resp = requests.post(MCP_SERVER_URL, json=payload)
        assert resp.status_code == 200
        data = resp.json()["result"]
        assert data["status"] == "success"
        assert "cloned" in data["details"]["message"].lower()

def test_git_generate_ssh_key_success():
    # Use a dummy email for testing
    payload = {
        "method": "tool_action_wrapper",
        "params": {
            "task": "git_setup",
            "action": "generate_ssh_key",
            "email": "test-integration@example.com"
        },
        "id": 5
    }
    resp = requests.post(MCP_SERVER_URL, json=payload)
    assert resp.status_code == 200
    data = resp.json()["result"]
    assert data["status"] == "success"
    assert "ssh key" in data["details"]["message"].lower()