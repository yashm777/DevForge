import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO)

def check_version_linux(tool_name: str) -> dict:
    if shutil.which(tool_name) is None:
        return {
            "status": "error",
            "message": f"{tool_name} is not installed."
        }

    try:
        version_cmd = [tool_name, "--version"]
        result = subprocess.run(version_cmd, capture_output=True, text=True, check=True)

        return {
            "status": "success",
            "message": f"{tool_name} is installed.",
            "version": result.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "message": f"Failed to retrieve version for {tool_name}.",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
