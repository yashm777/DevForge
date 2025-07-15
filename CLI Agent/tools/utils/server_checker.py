import socket
import requests
import time

def is_server_running(host: str = "localhost", port: int = 8000) -> bool:
    """
    Check if the MCP server is running on the specified host and port.
    
    Args:
        host (str): Host to check (default: localhost)
        port (int): Port to check (default: 8000)
        
    Returns:
        bool: True if server is running, False otherwise
    """
    try:
        # First check if the port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result != 0:
            return False
            
        # Then check if the MCP endpoint responds
        response = requests.get(f"http://{host}:{port}/docs", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def wait_for_server(host: str = "localhost", port: int = 8000, timeout: int = 30) -> bool:
    """
    Wait for the server to become available.
    
    Args:
        host (str): Host to check (default: localhost)
        port (int): Port to check (default: 8000)
        timeout (int): Maximum time to wait in seconds (default: 30)
        
    Returns:
        bool: True if server becomes available within timeout, False otherwise
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if is_server_running(host, port):
            return True
        time.sleep(1)
    return False 