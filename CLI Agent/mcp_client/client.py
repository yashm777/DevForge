import requests
from typing import Optional, Dict, Any

class HTTPMCPClient:
    """HTTP-based MCP client for communicating with MCP server via REST API"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.mcp_url = f"{base_url}/mcp/"
    
    def _make_request(self, method: str, params: dict):
        payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": method,
            "params": params
        }
        try:
            response = requests.post(self.mcp_url, json=payload, timeout=100)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except requests.exceptions.ConnectionError:
            return {"error": "Cannot connect to MCP server. Please start the server first with: uv run python -m mcp_server.mcp_server"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    def tool_action(self, task: str, tool_name: str, version: str = "latest"):
        return self._make_request("tool_action_wrapper", {
            "task": task,
            "tool_name": tool_name,
            "version": version
        })    
    
    def get_server_info(self):
        return self._make_request("info://server", {})
    
    def get_server_logs(self, lines: int = 50):
        """Get server logs from the MCP server"""
        return self._make_request("get_logs", {"lines": lines})
    
    def generate_code(self, description: str):
        result = self._make_request("generate_code", {"description": description})
        # Handle the nested result structure
        if "result" in result:
            inner_result = result["result"]
            if "code" in inner_result:
                return inner_result["code"]
            elif "status" in inner_result and inner_result["status"] == "error":
                return f"[Error] {inner_result.get('message', 'Code generation failed')}"
        elif "error" in result:
            return f"[Error] {result['error']}"
        return "[Error] No code returned"
    
    def call_jsonrpc(self, method: str, params: dict):
        return self._make_request(method, params)

    def system_config(self, action: str, tool_name: str, value: Optional[str] = None):
            """
            Calls the MCP server for system configuration tasks.
            """
            params = {
                "task": "system_config",
                "tool_name": tool_name,
                "action": action
            }
            if value:
                params["value"] = value
            return self._make_request("tool_action_wrapper", params)
    
    def git_setup(self, action: str, repo_url: str = "", branch: str = "", username: str = "", email: str = "", dest_dir: str = ""):
        """
        Perform git-related actions via the MCP server.
        action: 'clone', 'switch_branch', or 'generate_ssh_key'
        """
        params = {
            "task": "git_setup",
            "action": action,
            "repo_url": repo_url,
            "branch": branch,
            "username": username,
            "email": email,
            "dest_dir": dest_dir
        }
        return self._make_request("tool_action_wrapper", params)
