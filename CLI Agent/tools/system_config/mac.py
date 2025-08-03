import os
import subprocess
import socket
import plistlib
import json

def check_env_variable(var_name):
    """Check if an environment variable is set on Mac."""
    value = os.environ.get(var_name)
    if value:
        return {"status": "success", "variable": var_name, "value": value}
    else:
        return {"status": "error", "message": f"{var_name} is not set."}

def set_env_variable(var_name, value, scope="user"):
    """Set an environment variable persistently on Mac (adds to shell profile)."""
    try:
        # Detect the user's shell
        shell = detect_user_shell()
        profile_path = get_shell_profile_path(shell)
        
        export_line = f'export {var_name}="{value}"\n'

        # Remove existing line if present
        if os.path.exists(profile_path):
            subprocess.run(["sed", "-i", "", f'/^export {var_name}=/d', profile_path], check=False)

        # Append new export line
        with open(profile_path, "a") as f:
            f.write(export_line)

        return {
            "status": "success", 
            "variable": var_name, 
            "value": value, 
            "message": f"Please run 'source {profile_path}' or restart your terminal to apply changes"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

def append_to_path(new_path, scope="user"):
    """Append a directory to the PATH persistently on Mac."""
    try:
        shell = detect_user_shell()
        profile_path = get_shell_profile_path(shell)
        export_line = f'export PATH="$PATH:{new_path}"\n'

        # Only append if not already in PATH
        if os.path.exists(profile_path):
            with open(profile_path, "r") as f:
                if new_path in f.read():
                    return {"status": "info", "message": "Path already exists", "path": new_path}

        with open(profile_path, "a") as f:
            f.write(export_line)

        return {"status": "success", "message": "Path added", "path": new_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def remove_from_path(dir_to_remove, scope="user"):
    """Remove a directory from PATH persistently on Mac."""
    try:
        shell = detect_user_shell()
        profile_path = get_shell_profile_path(shell)
        
        if os.path.exists(profile_path):
            subprocess.run(["sed", "-i", "", f's|:{dir_to_remove}||g', profile_path], check=False)
            subprocess.run(["sed", "-i", "", f's|{dir_to_remove}:||g', profile_path], check=False)
        
        return {"status": "success", "message": f"Removed {dir_to_remove} from PATH"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def remove_env_variable(var_name, scope="user"):
    """Remove an environment variable from Mac persistently."""
    try:
        shell = detect_user_shell()
        profile_path = get_shell_profile_path(shell)
        
        if os.path.exists(profile_path):
            subprocess.run(["sed", "-i", "", f'/^export {var_name}=.*/d', profile_path], check=False)
        
        return {"status": "success", "message": f"{var_name} removed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def list_env_variables():
    """List all environment variables on Mac."""
    try:
        env_vars = dict(os.environ)
        return {"status": "success", "variables": env_vars}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def is_port_open(port):
    """Check if a TCP port is in use on Mac."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("127.0.0.1", port))
            return {"status": "in_use" if result == 0 else "free", "port": port}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def is_service_running(service_name):
    """Check if a Mac service (launchd) is running."""
    try:
        # Check if it's a user service
        result = subprocess.run(
            ["launchctl", "list", service_name], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            return {"status": "running", "service": service_name, "scope": "user"}
        
        # Check if it's a system service
        result = subprocess.run(
            ["sudo", "launchctl", "list", service_name], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            return {"status": "running", "service": service_name, "scope": "system"}
        
        return {"status": "not_running", "service": service_name}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def detect_user_shell():
    """Detect the user's current shell."""
    try:
        # First try to get from SHELL environment variable
        shell = os.environ.get('SHELL', '')
        if shell:
            return os.path.basename(shell)
        
        # Fallback to checking user's default shell
        result = subprocess.run(
            ["dscl", ".", "-read", f"/Users/{os.getenv('USER')}", "UserShell"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            shell_line = result.stdout.strip()
            if "UserShell:" in shell_line:
                shell_path = shell_line.split("UserShell:")[1].strip()
                return os.path.basename(shell_path)
        
        # Default fallback
        return "zsh"
    except Exception:
        return "zsh"

def get_shell_profile_path(shell):
    """Get the appropriate profile file path for the given shell."""
    home = os.path.expanduser("~")
    
    shell_profiles = {
        "zsh": os.path.join(home, ".zshrc"),
        "bash": os.path.join(home, ".bash_profile"),
        "fish": os.path.join(home, ".config/fish/config.fish"),
        "tcsh": os.path.join(home, ".tcshrc"),
        "csh": os.path.join(home, ".cshrc")
    }
    
    return shell_profiles.get(shell, os.path.join(home, ".zshrc"))

def get_system_info():
    """Get Mac system information."""
    try:
        result = subprocess.run(
            ["system_profiler", "SPSoftwareDataType", "-json"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            software_info = data.get("SPSoftwareDataType", [{}])[0]
            
            return {
                "status": "success",
                "system_info": {
                    "os_version": software_info.get("os_version", "Unknown"),
                    "kernel_version": software_info.get("kernel_version", "Unknown"),
                    "system_version": software_info.get("system_version", "Unknown"),
                    "user_name": software_info.get("user_name", "Unknown"),
                    "computer_name": software_info.get("local_host_name", "Unknown")
                }
            }
        else:
            return {"status": "error", "message": "Could not retrieve system info"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_homebrew():
    """Check if Homebrew is installed and get its status."""
    try:
        result = subprocess.run(["brew", "--version"], capture_output=True, text=True)
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            return {
                "status": "installed",
                "version": version_line,
                "path": subprocess.run(["which", "brew"], capture_output=True, text=True).stdout.strip()
            }
        else:
            return {"status": "not_installed", "message": "Homebrew is not installed"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_java_info():
    """Get Java installation information on Mac."""
    try:
        # Check for Java using java_home
        result = subprocess.run(["/usr/libexec/java_home"], capture_output=True, text=True)
        
        if result.returncode == 0:
            java_home = result.stdout.strip()
            
            # Get Java version
            version_result = subprocess.run(["java", "-version"], capture_output=True, text=True)
            version_info = version_result.stderr if version_result.stderr else "Unknown"
            
            return {
                "status": "installed",
                "java_home": java_home,
                "version_info": version_info.split('\n')[0] if version_info != "Unknown" else "Unknown"
            }
        else:
            return {"status": "not_installed", "message": "Java is not installed or not found"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def set_java_home(java_path=None):
    """Set JAVA_HOME environment variable on Mac."""
    try:
        if not java_path:
            # Try to auto-detect Java home
            result = subprocess.run(["/usr/libexec/java_home"], capture_output=True, text=True)
            if result.returncode == 0:
                java_path = result.stdout.strip()
            else:
                return {"status": "error", "message": "Could not auto-detect Java home"}
        
        return set_env_variable("JAVA_HOME", java_path)
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_xcode_tools():
    """Check if Xcode command line tools are installed."""
    try:
        result = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True)
        
        if result.returncode == 0:
            return {
                "status": "installed",
                "path": result.stdout.strip(),
                "message": "Xcode command line tools are installed"
            }
        else:
            return {"status": "not_installed", "message": "Xcode command line tools are not installed"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
