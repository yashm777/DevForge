import shutil
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def upgrade_tool_mac(tool_name: str) -> dict:
    if shutil.which("brew") is None:
        logger.error("Homebrew not found. Upgrade cannot proceed.")
        return {"status": "error", "message": "Homebrew not found. Please install Homebrew."}

    try:
        logger.info(f"Running command: brew upgrade {tool_name}")
        result = subprocess.run(["brew", "upgrade", tool_name], capture_output=True, text=True, check=True)

        logger.info(f"Upgrade successful: {tool_name}")
        return {
            "status": "success",
            "message": f"{tool_name} upgraded successfully.",
            "details": result.stdout.strip()
        }

    except subprocess.CalledProcessError as e:
        logger.error(f"Upgrade failed: {e.stderr.strip()}")
        return {
            "status": "error",
            "message": f"Failed to upgrade {tool_name}.",
            "details": e.stderr.strip() if e.stderr else "No additional error details."
        }
