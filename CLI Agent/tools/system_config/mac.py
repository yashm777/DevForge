import os
import subprocess
import socket
import plistlib
import json

def check_env_variable(var_name):
    """Enhanced check that looks in both current process and shell profile."""
    # First check current process
    value = os.environ.get(var_name)
    if value:
        return {"status": "success", "variable": var_name, "value": value}
    
    # If not found, check shell profile
    shell = detect_user_shell()
    profile_path = get_shell_profile_path(shell)
    
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            content = f.read()
            # Look for export lines
            import re
            pattern = f'export\\s+{var_name}=["\'](.*?)["\']'
            match = re.search(pattern, content)
            if match:
                return {
                    "status": "success", 
                    "variable": var_name, 
                    "value": match.group(1),
                    "source": "shell_profile",
                    "note": "Variable is set in shell profile but not active in current process"
                }
    
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
    """Check if a Mac service (launchd) is running - user services only."""
    try:
        # Only check user services to avoid sudo prompts during demo
        result = subprocess.run(
            ["launchctl", "list", service_name],
            capture_output=True,
            text=True,
            timeout=10  # Add timeout
        )
        
        if result.returncode == 0:
            return {
                "status": "running", 
                "service": service_name, 
                "scope": "user",
                "message": f"Service {service_name} is running (user scope)"
            }
        else:
            return {
                "status": "not_running", 
                "service": service_name,
                "message": f"Service {service_name} is not running or not found"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "status": "error", 
            "message": f"Service check for {service_name} timed out"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Failed to check service {service_name}: {str(e)}"
        }

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
            text=True,
            timeout=30
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
            text=True,
            timeout=30
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
        result = subprocess.run(["brew", "--version"], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            return {
                "status": "installed",
                "version": version_line,
                "path": subprocess.run(["which", "brew"], capture_output=True, text=True, timeout=30).stdout.strip()
            }
        else:
            return {"status": "not_installed", "message": "Homebrew is not installed"}
            
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Homebrew check timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_java_info():
    """Get Java installation information on Mac."""
    try:
        # First try to get Java version directly
        version_result = subprocess.run(["java", "-version"], capture_output=True, text=True, timeout=30)
        
        if version_result.returncode == 0:
            version_info = version_result.stderr if version_result.stderr else version_result.stdout
            
            # Try to get Java home from java_home command
            java_home_result = subprocess.run(["/usr/libexec/java_home"], capture_output=True, text=True, timeout=30)
            
            if java_home_result.returncode == 0:
                java_home = java_home_result.stdout.strip()
            else:
                # If java_home fails, try to detect Homebrew Java
                which_result = subprocess.run(["which", "java"], capture_output=True, text=True, timeout=30)
                if which_result.returncode == 0:
                    java_path = which_result.stdout.strip()
                    # For Homebrew Java, derive JAVA_HOME from the java binary path
                    if "/opt/homebrew/" in java_path:
                        # Extract JAVA_HOME from Homebrew path
                        java_home = java_path.replace("/bin/java", "")
                    else:
                        java_home = "Unknown (non-standard installation)"
                else:
                    java_home = "Unknown"
            
            return {
                "status": "installed",
                "java_home": java_home,
                "version_info": version_info.split('\n')[0] if version_info else "Unknown",
                "java_path": subprocess.run(["which", "java"], capture_output=True, text=True, timeout=30).stdout.strip()
            }
        else:
            return {"status": "not_installed", "message": "Java is not installed or not found"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

def set_java_home(java_path=None):
    """Set JAVA_HOME environment variable on Mac."""
    try:
        if not java_path:
            # Try to auto-detect Java home using our improved detection
            java_info = get_java_info()
            if java_info.get("status") == "installed":
                java_path = java_info.get("java_home")
                if java_path and java_path != "Unknown" and "non-standard" not in java_path:
                    return set_env_variable("JAVA_HOME", java_path)
                else:
                    return {"status": "error", "message": "Could not determine a valid JAVA_HOME path"}
            else:
                return {"status": "error", "message": "Java is not installed"}
        
        return set_env_variable("JAVA_HOME", java_path)
        
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_xcode_tools():
    """Check if Xcode command line tools are installed."""
    try:
        result = subprocess.run(["xcode-select", "-p"], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return {
                "status": "installed",
                "path": result.stdout.strip(),
                "message": "Xcode command line tools are installed"
            }
        else:
            return {"status": "not_installed", "message": "Xcode command line tools are not installed"}
    
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Xcode tools check timed out"}        
    except Exception as e:
        return {"status": "error", "message": str(e)}

def _find_pids_by_port(port: int):
    """
    Find process IDs using a specific port on Mac.
    
    Args:
        port: Port number to check
        
    Returns:
        List of process IDs using the port
    """
    pids = []
    
    # Method 1: Use lsof (preferred on Mac)
    try:
        result = subprocess.run(
            ["lsof", "-t", "-i", f"TCP:{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.splitlines():
                if line.strip().isdigit():
                    pids.append(int(line.strip()))
    except Exception:
        pass
    
    # Method 2: Use netstat as fallback (Mac-compatible)
    if not pids:
        try:
            result = subprocess.run(
                ["netstat", "-an", "-p", "tcp"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                for line in lines:
                    if f":{port}" in line and "LISTEN" in line:
                        # Parse netstat output to find PID
                        parts = line.split()
                        if len(parts) >= 7:
                            # On Mac, PID is typically in the last column
                            pid_part = parts[-1]
                            if pid_part.isdigit():
                                pids.append(int(pid_part))
        except Exception:
            pass
    
    # Method 3: Use ps and grep as last resort
    if not pids:
        try:
            result = subprocess.run(
                ["ps", "aux"], 
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                for line in lines:
                    if f":{port}" in line:
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].isdigit():
                            pids.append(int(parts[1]))
        except Exception:
            pass
    
    return sorted(set(pids))

def get_processes_on_port(port: int):
    """
    Get detailed information about processes using a specific port on Mac.
    
    Args:
        port: Port number to check
        
    Returns:
        Dictionary with process information
    """
    try:
        pids = _find_pids_by_port(port)
        
        if not pids:
            return {
                "status": "free",
                "port": port,
                "message": f"Port {port} is not in use by any processes",
                "processes": []
            }
        
        processes = []
        
        for pid in pids:
            try:
                # Get process details using ps
                result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "pid,ppid,user,comm,args"],
                    capture_output=True, text=True, timeout=5
                )
                
                if result.returncode == 0 and result.stdout:
                    lines = result.stdout.splitlines()
                    if len(lines) > 1:  # Skip header line
                        process_line = lines[1]
                        parts = process_line.split(None, 4)  # Split into max 5 parts
                        
                        if len(parts) >= 5:
                            process_info = {
                                "pid": int(parts[0]),
                                "ppid": int(parts[1]) if parts[1].isdigit() else "Unknown",
                                "user": parts[2],
                                "command": parts[3],
                                "full_command": parts[4] if len(parts) > 4 else parts[3]
                            }
                        else:
                            process_info = {
                                "pid": pid,
                                "ppid": "Unknown",
                                "user": "Unknown",
                                "command": "Unknown",
                                "full_command": "Unknown"
                            }
                        
                        # Try to get additional info using lsof
                        try:
                            lsof_result = subprocess.run(
                                ["lsof", "-p", str(pid), "-i", f"TCP:{port}"],
                                capture_output=True, text=True, timeout=5
                            )
                            if lsof_result.returncode == 0 and lsof_result.stdout:
                                lsof_lines = lsof_result.stdout.splitlines()
                                if len(lsof_lines) > 1:  # Skip header
                                    lsof_parts = lsof_lines[1].split()
                                    if len(lsof_parts) >= 9:
                                        process_info["local_address"] = lsof_parts[8]
                                        process_info["state"] = lsof_parts[5] if len(lsof_parts) > 5 else "Unknown"
                        except Exception:
                            process_info["local_address"] = "Unknown"
                            process_info["state"] = "Unknown"
                        
                        processes.append(process_info)
                
            except Exception as e:
                # If we can't get detailed info, add basic info
                processes.append({
                    "pid": pid,
                    "ppid": "Unknown",
                    "user": "Unknown",
                    "command": "Unknown",
                    "full_command": "Unknown",
                    "local_address": "Unknown",
                    "state": "Unknown",
                    "error": str(e)
                })
        
        return {
            "status": "in_use",
            "port": port,
            "message": f"Port {port} is in use by {len(processes)} process(es)",
            "processes": processes,
            "count": len(processes)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "port": port,
            "message": f"Failed to get process information for port {port}: {str(e)}",
            "processes": []
        }

def switch_java_version(version):
    """
    Switch to a specific Java version by updating shell configuration.
    
    Args:
        version: Java version to switch to (e.g., "21", "11", "17")
        
    Returns:
        Dictionary with status and message
    """
    try:
        # Detect shell and profile path
        shell = detect_user_shell()
        profile_path = get_shell_profile_path(shell)
        
        # Find the exact Java installation path
        java_home = None
        
        # Try to get the exact path from Homebrew
        try:
            result = subprocess.run(
                ["brew", "--prefix", f"openjdk@{version}"], 
                capture_output=True, 
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                brew_prefix = result.stdout.strip()
                java_home = f"{brew_prefix}/libexec/openjdk.jdk/Contents/Home"
        except Exception:
            pass
        
        # Fallback: find the version directory
        if not java_home:
            import glob
            version_dirs = glob.glob(f"/opt/homebrew/Cellar/openjdk@{version}/*/")
            if version_dirs:
                # Use the first (likely only) version directory
                version_dir = version_dirs[0].rstrip('/')
                java_home = f"{version_dir}/libexec/openjdk.jdk/Contents/Home"
            else:
                return {
                    "status": "error",
                    "message": f"Could not find installation directory for Java {version}. Make sure Java {version} is installed via Homebrew."
                }
        
        # Verify the Java home directory exists
        if not os.path.exists(java_home):
            return {
                "status": "error",
                "message": f"Java {version} directory not found at {java_home}. Please reinstall Java {version}."
            }
        
        # Update shell configuration
        java_bin = f"{java_home}/bin"
        
        # Read current profile content
        current_content = ""
        if os.path.exists(profile_path):
            with open(profile_path, "r") as f:
                current_content = f.read()
        
        # Comment out old Java configurations
        lines = current_content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.startswith('export JAVA_HOME=') and 'openjdk' in line:
                updated_lines.append(f"# Java {version} (old) - {line}")
            elif line.startswith('export PATH=') and 'openjdk' in line and '/bin:' in line:
                updated_lines.append(f"# Java {version} (old) - {line}")
            else:
                updated_lines.append(line)
        
        # Add new Java configuration
        updated_lines.extend([
            "",
            f"# Java {version} (current)",
            f'export JAVA_HOME="{java_home}"',
            f'export PATH="{java_bin}:$PATH"'
        ])
        
        # Write updated configuration
        with open(profile_path, "w") as f:
            f.write('\n'.join(updated_lines))
        
        return {
            "status": "success",
            "message": f"Successfully switched to Java {version}. Run 'source {profile_path}' to apply changes.",
            "java_home": java_home,
            "java_bin": java_bin,
            "profile_updated": profile_path
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Failed to switch Java version: {str(e)}"
        }
