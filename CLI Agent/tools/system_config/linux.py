import os
import subprocess
import socket

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
