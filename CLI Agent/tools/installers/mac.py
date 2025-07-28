import subprocess
import shutil

def install_mac_tool(tool, version="latest"):
    if not shutil.which("brew"):
        try:
            install_brew_cmd = [
                "/bin/bash", "-c", 
                "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            ]
            brew_result = subprocess.run(install_brew_cmd, capture_output=True, text=True, timeout=300)
            if brew_result.returncode != 0:
                return {
                    "status": "error", 
                    "message": f"Failed to install Homebrew: {brew_result.stderr.strip() or brew_result.stdout.strip()}"
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    if version != "latest" and tool in ["python", "node", "java", "go", "php"]:
        cmd = ["brew", "install", f"{tool}@{version}"]
    else:
        cmd = ["brew", "install", tool]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Installed {tool}"}
        else:
            return {"status": "error", "message": result.stderr.strip() or result.stdout.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

