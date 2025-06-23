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
            response = requests.post(self.mcp_url, json=payload, timeout=30)
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
    
    def generate_code(self, description: str):
        result = self._make_request("generate_code", {"description": description})
        if "result" in result and "code" in result["result"]:
            return result["result"]["code"]
        elif "error" in result:
            return f"[Error] {result['error']}"
        else:
            return "[Error] No code returned"
    
    def call_jsonrpc(self, method: str, params: dict):
        return self._make_request(method, params)
