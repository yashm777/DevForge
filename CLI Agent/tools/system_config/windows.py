import os
import socket
import subprocess
import winreg
import re
import json

def check_env_variable(var_name):
    """
    Checks if an environment variable is set on Windows.
    """
    value = os.environ.get(var_name)
    if value:
        return {"status": "success", "variable": var_name, "value": value}
    else:
        return {"status": "error", "message": f"{var_name} is not set."}


def is_port_open(port):
    """
    Checks if a TCP port is currently in use on localhost.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        result = s.connect_ex(("127.0.0.1", port))
        if result == 0:
            return {"status": "in_use", "port": port}
        else:
            return {"status": "free", "port": port}


def is_service_running(service_name):
    """
    Checks if a Windows service is running using PowerShell.
    """
    try:
        cmd = [
            "powershell",
            "-Command",
            f"Get-Service -Name '{service_name}' | Select-Object -ExpandProperty Status"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        status = result.stdout.strip().lower()
        if status == "running":
            return {"status": "running", "service": service_name}
        else:
            return {"status": "not_running", "service": service_name}
    except subprocess.CalledProcessError:
        return {"status": "error", "message": f"Service '{service_name}' not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def set_env_variable(var_name, value, scope="user"):
    """
    Sets a persistent environment variable on Windows.
    
    Parameters:
    - var_name: str
    - value: str
    - scope: "user" or "system" (default is "user")
    """
    try:
        if scope == "user":
            reg_key = winreg.HKEY_CURRENT_USER
            subkey = r"Environment"
        elif scope == "system":
            reg_key = winreg.HKEY_LOCAL_MACHINE
            subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
        else:
            return {"status": "error", "message": "Invalid scope. Use 'user' or 'system'."}

        with winreg.OpenKey(reg_key, subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, var_name, 0, winreg.REG_SZ, value)

        return {"status": "success", "variable": var_name, "value": value}
    except PermissionError:
        return {"status": "error", "message": "Permission denied. Try running as administrator."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def append_to_path(new_path, scope="user"):
    """
    Appends a directory to the Windows PATH environment variable.
    Avoids duplicates and preserves existing entries.
    """
    try:
        if scope == "user":
            reg_key = winreg.HKEY_CURRENT_USER
            subkey = r"Environment"
        elif scope == "system":
            reg_key = winreg.HKEY_LOCAL_MACHINE
            subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
        else:
            return {"status": "error", "message": "Invalid scope. Use 'user' or 'system'."}

        with winreg.OpenKey(reg_key, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            current_path, _ = winreg.QueryValueEx(key, "Path")
            paths = [p for p in current_path.split(";") if p] if current_path else []

            if new_path in paths:
                return {"status": "info", "message": "Path already exists", "path": new_path}

            paths.append(new_path)
            updated_path = ";".join(str(p) for p in paths if p is not None)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, updated_path)

        print(f"Appending to PATH: {new_path}")



        return {"status": "success", "message": "Path added", "path": new_path}
    except PermissionError:
        return {"status": "error", "message": "Permission denied. Run as admin for system scope."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def remove_env_variable(var_name, scope="user"):
    """
    Removes a persistent environment variable on Windows.
    """
    import winreg
    try:
        if scope == "user":
            reg_key = winreg.HKEY_CURRENT_USER
            subkey = r"Environment"
        elif scope == "system":
            reg_key = winreg.HKEY_LOCAL_MACHINE
            subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
        else:
            return {"status": "error", "message": "Invalid scope. Use 'user' or 'system'."}

        with winreg.OpenKey(reg_key, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            winreg.DeleteValue(key, var_name)

        return {"status": "success", "message": f"{var_name} removed"}
    except FileNotFoundError:
        return {"status": "error", "message": f"{var_name} not found"}
    except PermissionError:
        return {"status": "error", "message": "Permission denied. Run as admin for system scope."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
def list_env_variables(scope="user"):
    """
    Lists all user-level (or system-level) environment variables.
    """
    import winreg
    try:
        if scope == "user":
            reg_key = winreg.HKEY_CURRENT_USER
            subkey = r"Environment"
        elif scope == "system":
            reg_key = winreg.HKEY_LOCAL_MACHINE
            subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
        else:
            return {"status": "error", "message": "Invalid scope"}

        variables = {}
        with winreg.OpenKey(reg_key, subkey) as key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, i)
                    variables[name] = value
                    i += 1
                except OSError:
                    break
        return {"status": "success", "variables": variables}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def remove_from_path(dir_to_remove, scope="user"):
    """
    Removes a directory from the PATH environment variable if it exists.
    """
    import winreg
    try:
        if scope == "user":
            reg_key = winreg.HKEY_CURRENT_USER
            subkey = r"Environment"
        elif scope == "system":
            reg_key = winreg.HKEY_LOCAL_MACHINE
            subkey = r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
        else:
            return {"status": "error", "message": "Invalid scope"}

        with winreg.OpenKey(reg_key, subkey, 0, winreg.KEY_ALL_ACCESS) as key:
            current_path, _ = winreg.QueryValueEx(key, "Path")
            normalized = lambda p: os.path.normpath(p.strip().lower())
            target = normalized(dir_to_remove)
            paths = [p for p in current_path.split(";") if normalized(p) != target]


            if dir_to_remove not in paths:
                return {"status": "info", "message": f"{dir_to_remove} not in PATH"}

            paths = [p for p in paths if p != dir_to_remove]
            updated_path = ";".join(paths)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, updated_path)

        return {"status": "success", "message": f"Removed {dir_to_remove} from PATH"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _find_pids_by_port_windows(port: int) -> list[int]:
    """
    Best-effort PID discovery for a TCP port on Windows using:
      1) PowerShell Get-NetTCPConnection (OwningProcess)
      2) netstat -ano -p TCP parsing
    """
    pids: list[int] = []
    # Try PowerShell Get-NetTCPConnection (Windows 10+)
    try:
        ps_cmd = [
            "powershell", "-NoProfile", "-Command",
            f"$c=Get-NetTCPConnection -LocalPort {int(port)} -State Listen -ErrorAction SilentlyContinue;"
            f"if($c){{($c | Select -ExpandProperty OwningProcess) -join \"`n\"}}"
        ]
        r = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout:
            for line in r.stdout.splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
    except Exception:
        pass
    # Fall back to netstat
    if not pids:
        try:
            r = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=7)
            if r.returncode == 0 and r.stdout:
                for line in r.stdout.splitlines():
                    if "LISTENING" in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            local_addr = parts[1]
                            pid_str = parts[-1]
                            # Matches 0.0.0.0:8000, 127.0.0.1:8000, [::]:8000, etc.
                            if local_addr.endswith(f":{port}") or f"]:{port}" in local_addr:
                                if pid_str.isdigit():
                                    pids.append(int(pid_str))
        except Exception:
            pass
    return sorted(set(pids))

def _ps_process_info(pid: int) -> dict:
    """
    Fetch basic process info (Name, CommandLine) via PowerShell CIM.
    Falls back to tasklist for Name when needed.
    """
    info = {"pid": pid}
    try:
        ps_cmd = [
            "powershell", "-NoProfile", "-Command",
            f"$p=Get-CimInstance Win32_Process -Filter \"ProcessId={pid}\";"
            f"if($p){{[PSCustomObject]@{{Name=$p.Name;CommandLine=$($p.CommandLine)}} | ConvertTo-Json -Compress}}"
        ]
        r = subprocess.run(ps_cmd, capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            try:
                obj = json.loads(r.stdout.strip())
                if isinstance(obj, dict):
                    if obj.get("Name"):
                        info["name"] = obj.get("Name", "")
                    if obj.get("CommandLine"):
                        info["cmd"] = obj.get("CommandLine", "")
            except Exception:
                pass
    except Exception:
        pass
    # Fallback: tasklist for name
    if "name" not in info or not info["name"]:
        try:
            r = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0 and r.stdout.strip() and "INFO:" not in r.stdout:
                # CSV: "Image Name","PID","Session Name","Session#","Mem Usage"
                first = r.stdout.splitlines()[0].strip().strip('"')
                name = first.split('","')[0].strip('"')
                if name:
                    info["name"] = name
        except Exception:
            pass
    return info

def get_processes_on_port(port: int):
    """
    Show all processes listening on the given TCP port (Windows).
    Returns:
      - {"status":"success","port":<port>,"processes":[{"pid":..., "name":..., "cmd":...}, ...]}
      - {"status":"not_found","port":<port>,"message":"..."} if none found
    """
    try:
        port = int(port)
        if port < 1 or port > 65535:
            return {"status": "error", "message": "Invalid port number."}
        pids = _find_pids_by_port_windows(port)
        if not pids:
            return {"status": "not_found", "port": port, "message": "No process found on this port."}
        processes = [_ps_process_info(pid) for pid in pids]
        return {"status": "success", "port": port, "processes": processes}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def kill_process_on_port(port: int, process_id: int = None, signal_name: str = "TERM"):
    """
    Kill process(es) listening on a TCP port (Windows).
    - port (required): TCP port to target.
    - process_id (optional): if provided, kill only this PID; otherwise kill all PIDs on the port.
    - signal_name: TERM (default) uses taskkill without /F; KILL uses /F.
    Skips killing current process unless explicitly targeted.
    """
    try:
        port = int(port)
        if port < 1 or port > 65535:
            return {"status": "error", "message": "Invalid port number."}
        pids = _find_pids_by_port_windows(port)
        if not pids:
            return {"status": "not_found", "port": port, "message": "No process found on this port."}

        # If PID specified, ensure it's actually on this port
        if process_id is not None:
            try:
                process_id = int(process_id)
            except ValueError:
                return {"status": "error", "message": "Invalid process_id."}
            if process_id not in pids:
                return {"status": "error", "port": port, "message": f"PID {process_id} is not listening on port {port}."}
            target_pids = [process_id]
        else:
            target_pids = list(pids)

        # Avoid killing ourselves unless explicitly requested
        self_pid = os.getpid()
        if process_id is None and self_pid in target_pids:
            target_pids = [pid for pid in target_pids if pid != self_pid]
            if not target_pids:
                return {"status": "warning", "port": port, "message": "Current process is listening on this port. Skipping self. Provide process_id to force."}

        # Map signal_name to taskkill flags
        force = str(signal_name).upper() in ("KILL", "SIGKILL", "FORCE")

        killed, failed = [], []
        for pid in target_pids:
            try:
                cmd = ["taskkill", "/PID", str(pid)]
                if force:
                    cmd.insert(1, "/F")
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode == 0:
                    killed.append(pid)
                else:
                    failed.append({"pid": pid, "error": (r.stderr or r.stdout or "").strip()})
            except Exception as e:
                failed.append({"pid": pid, "error": str(e)})

        if killed and not failed:
            return {"status": "success", "port": port, "killed_pids": killed, "signal": ("KILL" if force else "TERM")}
        if killed and failed:
            return {"status": "partial", "port": port, "killed_pids": killed, "failed": failed, "signal": ("KILL" if force else "TERM")}
        # Update: include PID(s) in the error message for clarity
        failed_pids = [f.get("pid") for f in failed if isinstance(f, dict) and f.get("pid") is not None]
        if not failed_pids:
            failed_pids = target_pids  # fallback to attempted targets
        return {
            "status": "error",
            "port": port,
            "message": f"Failed to kill PID(s) {failed_pids}. Try in admin mode."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
