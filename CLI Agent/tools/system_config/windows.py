import os
import socket
import subprocess
import winreg

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

