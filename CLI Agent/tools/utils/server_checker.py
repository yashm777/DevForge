import socket
import requests
import time

HEALTH_PATH = "/health"  # fast readiness endpoint

def is_server_running(host: str = "localhost", port: int = 8000) -> bool:
    """Optimistic readiness check using a lightweight /health probe first.

    Falls back to /docs only if /health is missing (older server version) to
    remain backward compatible.
    """
    try:
        # Check TCP connectivity first
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.6)
            if sock.connect_ex((host, port)) != 0:
                return False

        # Fast path: health endpoint
        try:
            resp = requests.get(f"http://{host}:{port}{HEALTH_PATH}", timeout=1.2)
            if resp.status_code == 200:
                return True
        except Exception:
            # Ignore; try legacy docs path next
            pass

        # Legacy fallback (/docs can take longer; allow a bit more time)
        try:
            resp = requests.get(f"http://{host}:{port}/docs", timeout=2.5)
            return resp.status_code == 200
        except Exception:
            return False
    except Exception:
        return False

def wait_for_server(host: str = "localhost", port: int = 8000, timeout: int = 60) -> bool:
    """Poll for server readiness with progressive backoff within total timeout."""
    start = time.time()
    attempt = 0
    delay = 0.35  # quick initial checks
    while time.time() - start < timeout:
        if is_server_running(host, port):
            return True
        time.sleep(delay)
        attempt += 1
        # Gradually increase delay up to 2s to reduce spin
        if delay < 2:
            delay = min(2, delay * 1.5)
    return False
