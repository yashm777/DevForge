import subprocess
import shutil

def check_sudo_access():
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def install_linux_tool(tool):
    if not check_sudo_access():
        return {
            "status": "error", 
            "message": "sudo access required for package installation. Please run: sudo -v"
        }

    try:
        if shutil.which("apt-get"):
            cmd = ["sudo", "apt-get", "update"]
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            cmd = ["sudo", "apt-get", "install", "-y", tool]

        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "install", "-y", tool]

        elif shutil.which("pacman"):
            cmd = ["sudo", "pacman", "-Sy", "--noconfirm", tool]

        elif shutil.which("apk"):
            cmd = ["sudo", "apk", "add", tool]

        else:
            return {"status": "error", "message": "No supported package manager found."}

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {
                "status": "success",
                "message": result.stdout.strip() or f"Installed {tool}"
            }
        else:
            return {
                "status": "error",
                "message": result.stderr.strip() or result.stdout.strip()
            }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Installation failed: {e.stderr.strip() if e.stderr else str(e)}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
