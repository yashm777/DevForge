import subprocess
import shutil

def check_sudo_access():
    try:
        result = subprocess.run(["sudo", "-n", "true"], capture_output=True, text=True, timeout=5)
        return result.returncode == 0
    except:
        return False

def uninstall_linux_tool(tool):
    if not check_sudo_access():
        return {
            "status": "error", 
            "message": "sudo access required for package removal. Please run: sudo -v"
        }
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
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Uninstalled {tool}"}
        else:
            return {"status": "error", "message": result.stderr.strip() or result.stdout.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
