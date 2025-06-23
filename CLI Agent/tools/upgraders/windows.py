import subprocess

def handle_tool(tool, version="latest"):
    try:
        # winget upgrade <tool> --silent --accept-source-agreements --accept-package-agreements
        cmd = [
            "winget", "upgrade", tool,
            "--silent",
            "--accept-source-agreements",
            "--accept-package-agreements"
        ]
        if version != "latest":
            cmd += ["--version", version]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return {"status": "success", "message": f"Upgraded {tool} (Windows/winget)"}
        else:
            return {"status": "error", "message": result.stderr or result.stdout}
    except Exception as e:
        return {"status": "error", "message": str(e)} 