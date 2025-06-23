import subprocess

def handle_tool(tool, version=None):
    try:
        # winget uninstall <tool> --silent --accept-source-agreements
        cmd = [
            "winget", "uninstall", tool,
            "--silent",
            "--accept-source-agreements"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": f"Uninstalled {tool} (Windows/winget)"}
        else:
            return {"status": "error", "message": result.stderr or result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)} 