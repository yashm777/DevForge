import os
import subprocess
import socket
import re
import signal

def check_env_variable(var_name):
    """Check if an environment variable is set on Linux."""
    value = os.environ.get(var_name)
    if value:
        return {"status": "success", "variable": var_name, "value": value}
    else:
        return {"status": "error", "message": f"{var_name} is not set."}

def set_env_variable(var_name, value, scope="user"):
    """Set an environment variable persistently on Linux (adds to ~/.bashrc for user)."""
    try:
        bashrc_path = os.path.expanduser("~/.bashrc")
        export_line = f'export {var_name}="{value}"\n'

        # Remove existing line if present
        subprocess.run(["sed", "-i", f'/^{var_name}=/d', bashrc_path])

        # Append new export line
        with open(bashrc_path, "a") as f:
            f.write(export_line)

        return {"status": "success", "variable": var_name, "value": value, "message": "Please run 'source ~/.bashrc' or restart shell to apply changes"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def append_to_path(new_path, scope="user"):
    """Append a directory to the PATH persistently on Linux."""
    try:
        bashrc_path = os.path.expanduser("~/.bashrc")
        export_line = f'export PATH="$PATH:{new_path}"\n'

        # Only append if not already in PATH
        with open(bashrc_path, "r") as f:
            if new_path in f.read():
                return {"status": "info", "message": "Path already exists", "path": new_path}

        with open(bashrc_path, "a") as f:
            f.write(export_line)

        return {"status": "success", "message": "Path added", "path": new_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def remove_from_path(dir_to_remove, scope="user"):
    """Remove a directory from PATH persistently on Linux."""
    try:
        bashrc_path = os.path.expanduser("~/.bashrc")
        subprocess.run(["sed", "-i", f's|:{dir_to_remove}||g', bashrc_path])
        return {"status": "success", "message": f"Removed {dir_to_remove} from PATH"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def remove_env_variable(var_name, scope="user"):
    """Remove an environment variable from Linux persistently."""
    try:
        bashrc_path = os.path.expanduser("~/.bashrc")
        subprocess.run(["sed", "-i", f'/^{var_name}=.*/d', bashrc_path])
        return {"status": "success", "message": f"{var_name} removed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_env_variables():
    """List all environment variables on Linux."""
    try:
        env_vars = dict(os.environ)
        return {"status": "success", "variables": env_vars}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def is_port_open(port):
    """Check if a TCP port is in use on Linux."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("127.0.0.1", port))
            return {"status": "in_use" if result == 0 else "free", "port": port}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def is_service_running(service_name):
    """Check if a Linux service is running using systemctl."""
    try:
        result = subprocess.run(["systemctl", "is-active", service_name], capture_output=True, text=True)
        status = result.stdout.strip()
        if status == "active":
            return {"status": "running", "service": service_name}
        else:
            return {"status": "not_running", "service": service_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _find_pids_by_port(port: int):
    """
    Find PIDs listening on a TCP port using lsof/ss/fuser (best effort).
    Returns a sorted list of unique PIDs.
    """
    pids = []

    # Try lsof (preferred)
    try:
        r = subprocess.run(
            ["lsof", "-t", "-i", f"TCP:{port}", "-sTCP:LISTEN", "-n", "-P"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout:
            for line in r.stdout.splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
    except Exception:
        pass

    # Try ss if none found
    if not pids:
        try:
            r = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0 and r.stdout:
                for line in r.stdout.splitlines():
                    if f":{port} " in line or f":{port}\n" in line or line.strip().endswith(f":{port}"):
                        for m in re.finditer(r"pid=(\d+)", line):
                            pids.append(int(m.group(1)))
        except Exception:
            pass

    # Try fuser as a last resort
    if not pids:
        try:
            r = subprocess.run(["fuser", "-n", "tcp", str(port)], capture_output=True, text=True, timeout=5)
            out = (r.stdout or "") + (r.stderr or "")
            for tok in re.findall(r"\b(\d+)\b", out):
                try:
                    pids.append(int(tok))
                except ValueError:
                    pass
        except Exception:
            pass

    return sorted(set(pids))


def get_processes_on_port(port: int):
    """
    Show all processes listening on the given TCP port.
    Returns:
      - {"status":"success","port":<port>,"processes":[{"pid":..., "name":..., "cmd":...}, ...]}
      - {"status":"not_found","port":<port>,"message":"..."} if none found
    """
    try:
        port = int(port)
        if port < 1 or port > 65535:
            return {"status": "error", "message": "Invalid port number."}

        pids = _find_pids_by_port(port)
        if not pids:
            return {"status": "not_found", "port": port, "message": "No process found on this port."}

        processes = []
        for pid in pids:
            name = ""
            cmd = ""
            try:
                r = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True, timeout=3)
                if r.returncode == 0:
                    name = (r.stdout or "").strip()
            except Exception:
                pass
            try:
                r = subprocess.run(["ps", "-p", str(pid), "-o", "cmd="], capture_output=True, text=True, timeout=3)
                if r.returncode == 0:
                    cmd = (r.stdout or "").strip()
            except Exception:
                pass
            processes.append({"pid": pid, "name": name, "cmd": cmd})

        return {"status": "success", "port": port, "processes": processes}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def kill_process_on_port(port: int, process_id: int = None, signal_name: str = "TERM"):
    """
    Kill process(es) listening on a TCP port.
    - port (required): TCP port to target.
    - process_id (optional): if provided, kill only this PID; otherwise kill all PIDs on the port.
    - signal_name: TERM (default), KILL, INT, HUP.
    Skips killing the current process unless explicitly targeted via process_id.
    """
    try:
        port = int(port)
        if port < 1 or port > 65535:
            return {"status": "error", "message": "Invalid port number."}

        pids = _find_pids_by_port(port)
        if not pids:
            return {"status": "not_found", "port": port, "message": "No process found on this port."}

        # If a PID is specified, restrict to that PID (only if it matches the port)
        if process_id is not None:
            try:
                process_id = int(process_id)
            except ValueError:
                return {"status": "error", "message": "Invalid process_id."}
            if process_id not in pids:
                return {"status": "error", "port": port, "message": f"PID {process_id} is not listening on port {port}."}
            target_pids = [process_id]
        else:
            target_pids = pids

        # Avoid killing the current process unless explicitly requested
        self_pid = os.getpid()
        if process_id is None and self_pid in target_pids:
            target_pids = [pid for pid in target_pids if pid != self_pid]
            if not target_pids:
                return {"status": "warning", "port": port, "message": "Current process is listening on this port. Skipping self. Provide process_id to force."}

        sigmap = {"TERM": signal.SIGTERM, "KILL": signal.SIGKILL, "INT": signal.SIGINT, "HUP": signal.SIGHUP}
        sig = sigmap.get(signal_name.upper(), signal.SIGTERM)

        killed, failed = [], []
        for pid in target_pids:
            try:
                os.kill(pid, sig)
                killed.append(pid)
            except PermissionError:
                failed.append({"pid": pid, "error": "permission_denied"})
            except ProcessLookupError:
                continue
            except Exception as e:
                failed.append({"pid": pid, "error": str(e)})

        if killed and not failed:
            return {"status": "success", "port": port, "killed_pids": killed, "signal": signal_name.upper()}
        if killed and failed:
            return {"status": "partial", "port": port, "killed_pids": killed, "failed": failed, "signal": signal_name.upper()}
        return {"status": "error", "port": port, "message": "Failed to kill any process. Try with sudo."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

