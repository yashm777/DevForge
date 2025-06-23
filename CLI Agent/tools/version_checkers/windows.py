import subprocess

def handle_tool(tool, version=None):
    try:
        # winget list <tool>
        cmd = ["winget", "list", tool]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            # Try to extract version from output
            lines = result.stdout.splitlines()
            for line in lines:
                if tool.lower() in line.lower():
                    parts = line.split()
                    if len(parts) >= 3:
                        return {"status": "success", "message": f"{tool} version: {parts[2]} (Windows/winget)"}
            return {"status": "success", "message": f"{tool} not found or version not detected (Windows/winget)"}
        else:
            return {"status": "error", "message": result.stderr or result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)} 