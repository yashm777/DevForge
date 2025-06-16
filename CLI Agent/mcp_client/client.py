import subprocess
import json
import uuid
import threading
import time
from typing import Optional, Dict, Any

class MCPClient:
    def __init__(self, server_cmd: list, retries: int = 3, timeout: float = 10.0):
        self.server_cmd = server_cmd
        self.retries = retries
        self.timeout = timeout
        self.responses = {}
        self.lock = threading.Lock()
        self.process = None
        self.reader_thread = None

    def start(self):
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
        for attempt in range(1, self.retries + 1):
            response = self._send_request(method, params)
            if response and response.get("status") != "error":
                return response
            time.sleep(0.5 * attempt)  # exponential backoff
        return {"status": "error", "message": f"All retries failed for method: {method}"}

    def tool_action(self, task: str, tool_name: str, version: str = "latest") -> dict:
        return self.call("tool_action_wrapper", {
            "task": task,
            "tool_name": tool_name,
            "version": version
        })

    def get_server_info(self) -> dict:
        return self.call("info://server", {})

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

if __name__ == "__main__":
    # Update with the correct path to your MCP server script
    mcp_client = MCPClient(["python", "your_mcp_server.py"])
    try:
        mcp_client.start()
        print("Fetching server info...")
        info = mcp_client.get_server_info()
        print(json.dumps(info, indent=2))

        print("\nInstalling Docker...")
        result = mcp_client.tool_action("install", "docker")
        print(json.dumps(result, indent=2))

    finally:
        mcp_client.stop()
