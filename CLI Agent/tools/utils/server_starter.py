import subprocess
import sys
import time
import threading
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
            
        # Start the server in background
        process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.mcp_server", "--host", host, "--port", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        
        # Wait a bit for the server to start
        time.sleep(2)
        
        # Check if server is now running
        if is_server_running(host, port):
            return process
        else:
            # If server didn't start, try to terminate the process
            try:
                process.terminate()
                process.wait(timeout=20)
            except:
                pass
            return None
            
    except Exception:
        return None

def ensure_server_running(host: str = "localhost", port: int = 8000, timeout: int = 60):
    """
    Ensure the MCP server is running, starting it if necessary.

    Returns:
        (bool, str|None): (True, None) if running, (False, error_message) if failed
    """
    try:
        if is_server_running(host, port):
            return True, None

        # Start the server in background
        process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.mcp_server", "--host", host, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )

        time.sleep(2)

        if is_server_running(host, port):
            return True, None
        else:
            try:
                out, err = process.communicate(timeout=5)
                error_message = f"[MCP Server stdout]:\n{out.decode(errors='ignore')}\n[MCP Server stderr]:\n{err.decode(errors='ignore')}"
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                error_message = f"Error terminating MCP server process: {e}"
            return False, error_message

    except Exception as e:
        return False, f"Exception while starting MCP server: {e}"
