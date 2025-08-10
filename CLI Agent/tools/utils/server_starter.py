import subprocess
import sys
import time
from typing import Optional
from .server_checker import is_server_running, wait_for_server

def start_server_background(host: str = "localhost", port: int = 8000) -> Optional[subprocess.Popen]:
    """
    Start the MCP server in the background.

    Args:
        host (str): Host to bind to (default: localhost)
        port (int): Port to bind to (default: 8000)

    Returns:
        Optional[subprocess.Popen]: Process object if started successfully, None otherwise
    """
    try:
        # Check if server is already running
        if is_server_running(host, port):
            return None

        process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.mcp_server", "--host", host, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        if wait_for_server(host, port, timeout=30):
            return process

        # Startup failed; capture diagnostics
        try:
            out, err = process.communicate(timeout=5)
        except Exception:
            out, err = b"", b"(timeout collecting process output)"
        try:
            process.terminate()
        except Exception:
            pass
        print("MCP server failed to start (background). Stdout:\n" + out.decode(errors="ignore"))
        print("Stderr:\n" + err.decode(errors="ignore"))
        return None

    except Exception:
        return None

def ensure_server_running(host: str = "localhost", port: int = 8000, timeout: int = 60):
    """Ensure the MCP server is running, starting and polling until ready.

    Returns True if the server responds before timeout, else False (after
    printing diagnostics). Existing external callers remain unaffected.
    """
    try:
        if is_server_running(host, port):
            return True

        process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.mcp_server", "--host", host, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        if wait_for_server(host, port, timeout=timeout):
            return True

        # Collect diagnostics if not ready in time
        try:
            out, err = process.communicate(timeout=5)
        except Exception:
            out, err = b"", b"(timeout collecting process output)"
        print("MCP server failed to become ready within timeout. Stdout:\n" + out.decode(errors="ignore"))
        print("Stderr:\n" + err.decode(errors="ignore"))
        try:
            process.terminate()
        except Exception:
            pass
        return False
    except Exception as e:
        print(f"Exception while starting MCP server: {e}")
        return False
