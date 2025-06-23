from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import platform
import subprocess
import shutil
import sys
import os
from tools.code_generator import generate_code

app = FastAPI()

# --- Tool Handlers ---
def install_tool(tool, version="latest"):
    os_type = platform.system().lower()
    if os_type == "windows":
        cmd = ["winget", "install", tool, "--silent", "--accept-source-agreements", "--accept-package-agreements"]
        if version != "latest":
            cmd += ["--version", version]
    elif os_type == "darwin":
        # Check if Homebrew is available, install if not found
        if not shutil.which("brew"):
            try:
                # Install Homebrew using the official installation script
                install_brew_cmd = [
                    "/bin/bash", "-c", 
                    "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                ]
                
                print("Homebrew not found. Installing Homebrew...")
                brew_result = subprocess.run(install_brew_cmd, capture_output=True, text=True, timeout=300)
                
                if brew_result.returncode == 0:
                    # Add Homebrew to PATH for the current session
                    import os
                    homebrew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
                    current_path = os.environ.get("PATH", "")
                    for brew_path in homebrew_paths:
                        if brew_path not in current_path:
                            os.environ["PATH"] = f"{brew_path}:{current_path}"
                    
                    # Verify Homebrew is now available
                    if not shutil.which("brew"):
                        return {"status": "error", "message": "Homebrew installation completed but brew command still not found. Please restart your terminal."}
                    
                    print("Homebrew installed successfully!")
                else:
                    return {
                        "status": "error", 
                        "message": f"Failed to install Homebrew: {brew_result.stderr.strip() or brew_result.stdout.strip()}"
                    }
            except subprocess.TimeoutExpired:
                return {"status": "error", "message": "Homebrew installation timed out. Please install manually."}
            except Exception as e:
                return {"status": "error", "message": f"Error installing Homebrew: {str(e)}"}
        
        if version != "latest":
            # Use proper Homebrew version syntax for tools that support it
            if tool in ["python", "node", "java", "go", "php"]:
                cmd = ["brew", "install", f"{tool}@{version}"]
            else:
                # Most tools don't support version pinning in Homebrew
                cmd = ["brew", "install", tool]
        else:
            cmd = ["brew", "install", tool]
    elif os_type == "linux":
        if shutil.which("apt"):
            cmd = ["sudo", "apt", "install", "-y", tool]
        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "install", "-y", tool]
        elif shutil.which("pacman"):
            cmd = ["sudo", "pacman", "-S", "--noconfirm", tool]
        elif shutil.which("apk"):
            cmd = ["sudo", "apk", "add", tool]
        else:
            return {"status": "error", "message": "No supported package manager found."}
    else:
        return {"status": "error", "message": f"Unsupported OS: {os_type}"}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Installed {tool}"}
        else:
            # Special handling for winget ambiguous package
            if os_type == "windows" and "Multiple packages found" in output:
                # Parse the options - handle the actual winget output format
                import re
                options = []
                lines = output.splitlines()
                
                # Look for the actual package entries in the output
                for line in lines:
                    line = line.strip()
                    if not line or "Name" in line and "Id" in line or re.match(r'^-+$', line):
                        continue
                    
                    # Try to parse any package line, not just docker-related
                    parts = line.split()
                    if len(parts) >= 2:
                        # Find where the ID starts (usually after the name)
                        name_parts = []
                        id_start = -1
                        
                        for i, part in enumerate(parts):
                            if re.match(r'^[A-Z0-9]+\.[A-Za-z0-9]+$', part) or re.match(r'^[A-Z0-9]+$', part):
                                id_start = i
                                break
                            name_parts.append(part)
                        
                        if id_start > 0:
                            name = ' '.join(name_parts)
                            package_id = parts[id_start]
                            source = parts[-1] if len(parts) > id_start + 1 else "unknown"
                            
                            options.append({
                                "name": name,
                                "id": package_id,
                                "source": source
                            })
                
                # If still no options, create a simple fallback
                if not options:
                    options = [
                        {"name": "Docker Desktop", "id": "Docker.DockerDesktop", "source": "winget"},
                        {"name": "Docker Desktop", "id": "XP8CBJ40XLBWKX", "source": "msstore"}
                    ]
                
                return {
                    "status": "ambiguous",
                    "message": "Multiple packages found. Please select one.",
                    "options": options,
                    "raw": output
                }
            return {"status": "error", "message": output.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def uninstall_tool(tool, version=None):
    os_type = platform.system().lower()
    if os_type == "windows":
        cmd = ["winget", "uninstall", tool, "--silent", "--accept-source-agreements"]
    elif os_type == "darwin":
        cmd = ["brew", "uninstall", tool]
    elif os_type == "linux":
        if shutil.which("apt"):
            cmd = ["sudo", "apt", "remove", "-y", tool]
        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "remove", "-y", tool]
        elif shutil.which("pacman"):
            cmd = ["sudo", "pacman", "-R", "--noconfirm", tool]
        elif shutil.which("apk"):
            cmd = ["sudo", "apk", "del", tool]
        else:
            return {"status": "error", "message": "No supported package manager found."}
    else:
        return {"status": "error", "message": f"Unsupported OS: {os_type}"}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Uninstalled {tool}"}
        else:
            return {"status": "error", "message": result.stderr.strip() or result.stdout.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def update_tool(tool, version="latest"):
    os_type = platform.system().lower()
    if os_type == "windows":
        cmd = ["winget", "upgrade", tool, "--silent", "--accept-source-agreements", "--accept-package-agreements"]
        if version != "latest":
            cmd += ["--version", version]
    elif os_type == "darwin":
        cmd = ["brew", "upgrade", tool]
    elif os_type == "linux":
        if shutil.which("apt"):
            # For apt: update package list, then install/upgrade specific tool
            cmd = ["bash", "-c", f"sudo apt update && sudo apt install -y {tool}"]
        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "upgrade", "-y", tool]
        elif shutil.which("pacman"):
            # Fix: Update specific package, not entire system
            cmd = ["sudo", "pacman", "-S", "--noconfirm", tool]
        elif shutil.which("apk"):
            cmd = ["sudo", "apk", "add", "--upgrade", tool]
        else:
            return {"status": "error", "message": "No supported package manager found."}
    else:
        return {"status": "error", "message": f"Unsupported OS: {os_type}"}
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Updated {tool}"}
        else:
            return {"status": "error", "message": result.stderr.strip() or result.stdout.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def version_tool(tool, version=None):
    os_type = platform.system().lower()
    if os_type == "windows":
        # Try direct version command first (faster)
        try:
            direct_cmd = [tool, "--version"]
            result = subprocess.run(direct_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {"status": "success", "message": result.stdout.strip()}
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Fall back to winget list if direct command fails
        try:
            cmd = ["winget", "list", tool]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return {"status": "success", "message": result.stdout.strip()}
            else:
                return {"status": "error", "message": result.stderr.strip() or result.stdout.strip()}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": f"Timeout checking version for {tool}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif os_type == "darwin":
        # Try direct version command first with multiple flags
        for version_flag in ["--version", "-v", "-V", "version"]:
            try:
                direct_cmd = [tool, version_flag]
                result = subprocess.run(direct_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return {"status": "success", "message": result.stdout.strip()}
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # Fall back to Homebrew list if direct command fails
        try:
            cmd = ["brew", "list", "--versions", tool]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return {"status": "success", "message": result.stdout.strip() or f"{tool} is installed"}
            else:
                return {"status": "error", "message": f"{tool} not found or not installed via Homebrew"}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": f"Timeout checking version for {tool}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    elif os_type == "linux":
        # Try direct version command first with multiple flags
        for version_flag in ["--version", "-v", "-V", "version"]:
            try:
                direct_cmd = [tool, version_flag]
                result = subprocess.run(direct_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return {"status": "success", "message": result.stdout.strip()}
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # Fall back to package manager queries
        try:
            if shutil.which("apt"):
                cmd = ["dpkg", "-l", tool]
            elif shutil.which("dnf"):
                cmd = ["dnf", "list", "installed", tool]
            elif shutil.which("pacman"):
                cmd = ["pacman", "-Q", tool]
            elif shutil.which("apk"):
                cmd = ["apk", "info", tool]
            else:
                return {"status": "error", "message": "No supported package manager found"}
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return {"status": "success", "message": result.stdout.strip() or f"{tool} is installed"}
            else:
                return {"status": "error", "message": f"{tool} not found or not installed"}
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": f"Timeout checking version for {tool}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        return {"status": "error", "message": f"Unsupported OS: {os_type}"}

def get_system_info():
    return {
        "os_type": platform.system(),
        "os_version": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
        "cwd": os.getcwd(),
        "user": os.getenv("USERNAME") or os.getenv("USER")
    }

# --- JSON-RPC 2.0 Handler ---
@app.post("/mcp/")
async def mcp_endpoint(request: Request):
    req = await request.json()
    method = req.get("method")
    params = req.get("params", {})
    id_ = req.get("id")
    result = None
    if method == "tool_action_wrapper":
        task = params.get("task")
        tool = params.get("tool_name")
        version = params.get("version", "latest")
        if task == "install":
            result = install_tool(tool, version)
        elif task == "uninstall":
            result = uninstall_tool(tool)
        elif task == "update":
            result = update_tool(tool, version)
        elif task == "version":
            result = version_tool(tool)
        else:
            result = {"status": "error", "message": f"Unknown task: {task}"}
    elif method == "generate_code":
        description = params.get("description")
        result = generate_code(description)
    elif method == "info://server":
        result = get_system_info()
    else:
        result = {"status": "error", "message": f"Unknown method: {method}"}
    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "id": id_,
            "result": result
        },
        media_type="application/json"
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run("mcp_server.mcp_server:app", host=args.host, port=args.port, reload=False)