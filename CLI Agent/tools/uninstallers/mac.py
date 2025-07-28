import subprocess

def uninstall_mac_tool(tool):
    try:
        cmd = ["brew", "uninstall", tool]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Uninstalled {tool}"}
        else:
            return {"status": "error", "message": result.stderr.strip() or result.stdout.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
