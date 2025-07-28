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
                process.wait(timeout=5)
            except:
                pass
            return None
            
    except Exception:
        return None

def ensure_server_running(host: str = "localhost", port: int = 8000, timeout: int = 30) -> bool:
    """
    Ensure the MCP server is running, starting it if necessary.
    
    Args:
        host (str): Host to bind to (default: localhost)
        port (int): Port to bind to (default: 8000)
        timeout (int): Maximum time to wait for server to start (default: 30)
        
    Returns:
        bool: True if server is running, False otherwise
    """
    try:
        # Check if server is already running
        if is_server_running(host, port):
            return True

        # Start the server in background
        process = subprocess.Popen(
            [sys.executable, "-m", "mcp_server.mcp_server", "--host", host, "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )

        # Wait a bit for the server to start
        time.sleep(2)

        # Check if server is now running
        if is_server_running(host, port):
            return True
        else:
            # If server didn't start, print error output
            try:
                out, err = process.communicate(timeout=5)
                print("[MCP Server stdout]:", out.decode(errors="ignore"))
                print("[MCP Server stderr]:", err.decode(errors="ignore"))
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                print(f"Error terminating MCP server process: {e}")
            return False

    except Exception as e:
        print(f"Exception while starting MCP server: {e}")
        return False
