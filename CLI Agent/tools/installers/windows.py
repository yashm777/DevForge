import subprocess

def install_windows_tool(tool, version="latest"):
    cmd = [
        "winget", "install", tool,
        "--silent", "--accept-source-agreements", "--accept-package-agreements"
    ]
    if version != "latest":
        cmd += ["--version", version]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            return {"status": "success", "message": result.stdout.strip() or f"Installed {tool}"}
        else:
            return {"status": "error", "message": output.strip()}
    except Exception as e:
        return {"status": "error", "message": str(e)}
