import subprocess
import json
import uuid
import threading
import time
import requests
import os
import openai
from typing import Optional, Dict, Any

class MCPClient:
    def __init__(self, server_url: str = "http://localhost:8000/mcp/", retries: int = 3, timeout: float = 10.0):
        self.server_url = server_url
        self.retries = retries
        self.timeout = timeout
        self.session = requests.Session()

    def _send_request(self, method: str, params: dict) -> Optional[Dict[str, Any]]:
        """Send HTTP request to MCP server"""
        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",  # Ensure JSON-RPC 2.0 compliance
            "id": request_id,
            "method": method,
            "params": params
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = self.session.post(
                self.server_url,
                json=payload,
                timeout=self.timeout,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "message": f"Failed to send request: {e}"}

    def call(self, method: str, params: dict) -> dict:
        """Call MCP method with retries"""
        for attempt in range(1, self.retries + 1):
            response = self._send_request(method, params)
            if response:
                # Check if it's a valid JSON-RPC response
                if "result" in response or "error" in response:
                    return response
                # Also accept responses with direct status field for backward compatibility
                elif response.get("status") != "error":
                    return response
            time.sleep(0.5 * attempt)  # exponential backoff
        return {"status": "error", "message": f"All retries failed for method: {method}"}

    def tool_action(self, task: str, tool_name: str, version: str = "latest") -> dict:
        """Perform tool action via MCP server"""
        return self.call("tool_action_wrapper", {
            "task": task,
            "tool_name": tool_name,
            "version": version
        })

    def get_server_info(self) -> dict:
        """Get server information"""
        return self.call("info://server", {})

    def get_system_setup(self) -> dict:
        """Get system setup information"""
        return self.call("get_system_setup", {})

    def is_server_running(self) -> bool:
        """Check if MCP server is running"""
        try:
            response = self.session.get(self.server_url.replace("/mcp", "/health"), timeout=5)
            return response.status_code == 200
        except:
            return False

    def start(self):
        """Start the client (no-op for HTTP client)"""
        pass

    def stop(self):
        """Stop the client (no-op for HTTP client)"""
        self.session.close()

    def ask_question(self, question: str) -> str:
        # Call the MCP server for system info
        info = self.get_server_info()
        if info.get('status') == 'error':
            return f"[Error] Could not retrieve system info: {info.get('message')}\nQuestion asked: {question}"
        user_system = info.get('user_system', info)
        lines = [f"System Information:"]
        for k, v in user_system.items():
            lines.append(f"- {k}: {v}")
        lines.append(f"Question asked: {question}")
        return "\n".join(lines)

    def generate_code(self, description: str) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return "[Error] OPENAI_API_KEY not set. Cannot generate code."
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful coding assistant. Generate only code, no explanation."},
                    {"role": "user", "content": f"Write code for: {description}"}
                ],
                max_tokens=512,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Error] Code generation failed: {e}"

    def call_jsonrpc(self, method: str, params: dict) -> dict:
        """Send an arbitrary JSON-RPC request (for LLM parser integration)"""
        return self.call(method, params)

class MCPClientLegacy:
    """Legacy MCP client for subprocess-based communication"""
    def __init__(self, server_cmd: list, retries: int = 3, timeout: float = 10.0):
        self.server_cmd = server_cmd
        self.retries = retries
        self.timeout = timeout
        self.responses = {}
        self.lock = threading.Lock()
        self.process = None
        self.reader_thread = None

    def start(self):
        """Start the MCP server process"""
        self.process = subprocess.Popen(
            self.server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        self.reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self.reader_thread.start()

    def _read_stdout(self):
        """Read stdout from the MCP server process"""
        for line in self.process.stdout:
            try:
                response = json.loads(line.strip())
                response_id = response.get("id")
                if response_id:
                    with self.lock:
                        self.responses[response_id] = response
            except json.JSONDecodeError:
                continue

    def _send_request(self, method: str, params: dict) -> Optional[Dict[str, Any]]:
        """Send request to MCP server via subprocess"""
        request_id = str(uuid.uuid4())
        payload = {
            "id": request_id,
            "method": method,
            "params": params
        }

        if not self.process or self.process.stdin.closed:
            raise RuntimeError("MCP server process is not running or has been closed.")

        try:
            self.process.stdin.write(json.dumps(payload) + '\n')
            self.process.stdin.flush()
        except Exception as e:
            return {"status": "error", "message": f"Failed to send request: {e}"}

        # Wait for response with timeout
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            with self.lock:
                if request_id in self.responses:
                    return self.responses.pop(request_id)
            time.sleep(0.1)

        return {"status": "error", "message": "Request timed out."}

    def call(self, method: str, params: dict) -> dict:
        """Call MCP method with retries"""
        for attempt in range(1, self.retries + 1):
            response = self._send_request(method, params)
            if response:
                # Check if it's a valid JSON-RPC response
                if "result" in response or "error" in response:
                    return response
                # Also accept responses with direct status field for backward compatibility
                elif response.get("status") != "error":
                    return response
            time.sleep(0.5 * attempt)  # exponential backoff
        return {"status": "error", "message": f"All retries failed for method: {method}"}

    def tool_action(self, task: str, tool_name: str, version: str = "latest") -> dict:
        """Perform tool action via MCP server"""
        return self.call("tool_action_wrapper", {
            "task": task,
            "tool_name": tool_name,
            "version": version
        })

    def get_server_info(self) -> dict:
        """Get server information"""
        return self.call("info://server", {})

    def stop(self):
        """Stop the MCP server process"""
        if self.process:
            self.process.terminate()
            self.process.wait()

def create_mcp_client(use_http: bool = True) -> MCPClient:
    """Create MCP client with appropriate transport"""
    if use_http:
        return MCPClient("http://localhost:8000/mcp/")
    else:
        return MCPClientLegacy(["python", "-m", "mcp_server.mcp_server"])

if __name__ == "__main__":
    # Test the MCP client
    client = create_mcp_client(use_http=True)
    
    try:
        print("Testing MCP client...")
        
        # Check if server is running
        if client.is_server_running():
            print("✓ MCP server is running")
            
            # Get server info
            info = client.get_server_info()
            print("Server info:", json.dumps(info, indent=2))
            
            # Test tool action
            result = client.tool_action("version", "python")
            print("Tool action result:", json.dumps(result, indent=2))
        else:
            print("✗ MCP server is not running")
            
    except Exception as e:
        print(f"Error testing MCP client: {e}")
    finally:
        client.stop()
