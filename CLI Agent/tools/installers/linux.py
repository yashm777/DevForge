import os
import shutil
import subprocess
import logging
from typing import Optional

from tools.utils.os_utils import (
    get_os_type,
    get_available_package_manager,
    is_sudo_available,
    check_sudo_access,
    is_snap_available,
)
from tools.utils.name_resolver import resolve_tool_name
from llm_parser.parser import generate_smart_tool_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_APT_UPDATED = False


def _run(cmd: list[str], env: Optional[dict] = None) -> subprocess.CompletedProcess:
    logger.info("RUN: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def _apt_update_once() -> bool:
    global _APT_UPDATED
    if _APT_UPDATED:
        return True
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    r = _run(["sudo", "apt-get", "update"], env=env)
    if r.returncode == 0:
        _APT_UPDATED = True
        return True
    logger.error("apt-get update failed: %s", (r.stderr or r.stdout).strip())
    return False


def _ensure_apt_prereqs() -> bool:
    if get_available_package_manager() != "apt":
        return True
    if not _apt_update_once():
        return False
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    r = _run(["sudo", "apt-get", "install", "-y", "curl", "zip", "unzip", "ca-certificates"], env=env)
    if r.returncode != 0:
        logger.error("Failed installing apt prerequisites: %s", (r.stderr or r.stdout).strip())
        return False
    return True


def _ensure_snap_ready() -> bool:
    if is_snap_available():
        return True
    # Only Ubuntu/Debian path uses apt to install snapd
    if get_available_package_manager() != "apt":
        logger.error("snap not available and automatic setup is unsupported on this distro")
        return False
    if not _apt_update_once():
        return False
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")
    r = _run(["sudo", "apt-get", "install", "-y", "snapd"], env=env)
    if r.returncode != 0:
        logger.error("Failed to install snapd: %s", (r.stderr or r.stdout).strip())
        return False
    # Try to ensure snapd is enabled and running (ignore failures on non-systemd)
    _run(["sudo", "systemctl", "enable", "--now", "snapd"])
    # Symlink /snap if needed
    if not os.path.islink("/snap") and os.path.exists("/var/lib/snapd/snap"):
        try:
            _run(["sudo", "ln", "-s", "/var/lib/snapd/snap", "/snap"])
        except Exception:
            pass
    return True


def _sdkman_home() -> str:
    sudo_user = os.environ.get("SUDO_USER")
    return os.path.expanduser(f"~{sudo_user}") if sudo_user else os.path.expanduser("~")


def _sdkman_init_path() -> str:
    return os.path.join(_sdkman_home(), ".sdkman", "bin", "sdkman-init.sh")


def _ensure_sdkman_ready() -> bool:
    # Ensure curl exists on apt-based systems
    if get_available_package_manager() == "apt" and shutil.which("curl") is None:
        if not _ensure_apt_prereqs():
            return False

    init_path = _sdkman_init_path()
    if os.path.isfile(init_path):
        return True

    env = os.environ.copy()
    env["HOME"] = _sdkman_home()
    env["SDKMAN_DIR"] = os.path.join(env["HOME"], ".sdkman")
    env["SDKMAN_ASSUME_YES"] = "true"

    logger.info("Installing SDKMAN...")
    r = subprocess.run(["bash", "-lc", 'curl -s "https://get.sdkman.io" | bash'], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        logger.error("SDKMAN install failed: %s", (r.stderr or r.stdout).strip())
        return False

    return os.path.isfile(_sdkman_init_path())


def _apt_is_installed(pkg: str) -> bool:
    r = _run(["dpkg-query", "-W", "-f=${Status}", pkg])
    return r.returncode == 0 and "installed" in (r.stdout or "").lower()


def _snap_is_installed(snap: str) -> bool:
    r = _run(["snap", "list", snap])
    return r.returncode == 0


def _sdk_is_installed(candidate: str) -> bool:
    init_path = _sdkman_init_path()
    if not os.path.isfile(init_path):
        return False
    env = os.environ.copy()
    env["HOME"] = _sdkman_home()
    env["SDKMAN_DIR"] = os.path.join(env["HOME"], ".sdkman")
    check_cmd = f'source "{init_path}"; sdk current {candidate}'
    r = subprocess.run(["bash", "-lc", check_cmd], capture_output=True, text=True, env=env)
    combined = (r.stdout or "") + (r.stderr or "")
    # If candidate exists, SDKMAN prints something meaningful; "Using" indicates installed/in use
    return "Using" in combined


def _apt_install(pkg: str, version: str = "latest") -> dict:
    if get_available_package_manager() != "apt":
        return {"status": "error", "message": "apt is not available on this system"}
    if not _apt_update_once():
        return {"status": "error", "message": "apt update failed"}
    env = dict(os.environ, DEBIAN_FRONTEND="noninteractive")

    # Only attempt apt version pin if version looks like a real apt version string
    def _looks_like_apt_version(v: str) -> bool:
        # apt versions usually contain at least one of these
        return any(ch in v for ch in (":", "-", "~", "+"))

    if version and version != "latest" and _looks_like_apt_version(version):
        r = _run(["sudo", "apt-get", "install", "-y", f"{pkg}={version}"], env=env)
        if r.returncode != 0:
            r = _run(["sudo", "apt-get", "install", "-y", pkg], env=env)
    else:
        # Either latest or numeric alias like "17" -> rely on pkg name (e.g., openjdk-17-jdk) from resolver
        r = _run(["sudo", "apt-get", "install", "-y", pkg], env=env)

    if r.returncode == 0:
        return {"status": "success", "message": f"Installed '{pkg}' via apt"}
    # Treat 'is already the newest version' as success
    out = (r.stdout or "") + (r.stderr or "")
    if "is already the newest version" in out or "already installed" in out.lower():
        return {"status": "success", "message": f"'{pkg}' is already installed (apt)"}
    return {"status": "error", "message": (r.stderr or r.stdout or "").strip() or f"Failed installing '{pkg}' via apt"}


def _snap_install(snap: str, classic: bool = False) -> dict:
    if not _ensure_snap_ready():
        return {"status": "error", "message": "snap is not available and could not be installed"}
    cmd = ["sudo", "snap", "install", snap]
    if classic:
        cmd.append("--classic")
    r = _run(cmd)
    if r.returncode == 0:
        return {"status": "success", "message": f"Installed '{snap}' via snap"}
    out = (r.stdout or "") + (r.stderr or "")
    if "already installed" in out.lower():
        return {"status": "success", "message": f"'{snap}' is already installed (snap)"}
    return {"status": "error", "message": (r.stderr or r.stdout or "").strip() or f"Failed installing '{snap}' via snap"}


def _sdk_install(candidate: str, version: str = "latest") -> dict:
    if not _ensure_sdkman_ready():
        return {"status": "error", "message": "SDKMAN is not available and could not be installed"}
    env = os.environ.copy()
    env["HOME"] = _sdkman_home()
    env["SDKMAN_DIR"] = os.path.join(env["HOME"], ".sdkman")
    env["SDKMAN_ASSUME_YES"] = "true"
    init_path = _sdkman_init_path()
    cmd_str = f'source "{init_path}"; sdk install {candidate}' + (f" {version}" if version and version != "latest" else "")
    r = subprocess.run(["bash", "-lc", cmd_str], capture_output=True, text=True, env=env)
    if r.returncode == 0:
        return {"status": "success", "message": f"Installed '{candidate}' via SDKMAN"}
    out = (r.stderr or r.stdout or "").strip()
    if "is already installed" in out.lower() or "already installed" in out.lower():
        return {"status": "success", "message": f"'{candidate}' is already installed (SDKMAN)"}
    return {"status": "error", "message": out or f"Failed installing '{candidate}' via SDKMAN"}


def install_linux_tool(tool: str, version: str = "latest") -> dict:
    """
    Install developer tools on Ubuntu/Debian using resolver + apt/snap/SDKMAN.
    Returns: {"status": "success|error|ambiguous", "message": str, ...}
    """
    os_type = get_os_type().lower()
    if os_type not in ("ubuntu", "debian"):
        return {"status": "error", "message": f"Unsupported Linux distro '{os_type}'. Only Ubuntu/Debian supported."}

    if not is_sudo_available():
        return {"status": "error", "message": "sudo is not available. Please install sudo or run as root."}

    if not check_sudo_access():
        return {"status": "error", "message": "sudo access required. Run: `sudo -v` and try again."}

    # Resolve names and preferences via your resolver (single source of truth)
    resolved = resolve_tool_name(tool, os_type="linux", version=version, context="install") or {}
    resolved_tool = resolved.get("name", tool)
    manager = resolved.get("manager", "apt")
    sdk_candidate = resolved.get("sdk_candidate")
    apt_name = resolved.get("apt_name", resolved_tool)
    snap_name = resolved.get("snap_name", resolved_tool)
    classic_snap = resolved.get("classic_snap", False)
    fallback_msg = resolved.get("fallback")

    # Fast-path: detect already installed across ecosystems
    already_msgs = []
    try:
        if sdk_candidate and _sdk_is_installed(sdk_candidate):
            already_msgs.append(f"'{sdk_candidate}' (SDKMAN)")
        if _snap_is_installed(snap_name):
            already_msgs.append(f"'{snap_name}' (snap)")
        if _apt_is_installed(apt_name):
            already_msgs.append(f"'{apt_name}' (apt)")
        # Generic PATH check
        if shutil.which(resolved_tool) or shutil.which(tool):
            already_msgs.append(f"'{resolved_tool}' (path)")
    except Exception:
        pass

    if already_msgs:
        msg = f"{resolved_tool} is already installed: " + ", ".join(already_msgs)
        return {"status": "success", "message": msg}

    # Ensure apt prereqs early (curl for SDKMAN, etc.) on apt systems
    _ensure_apt_prereqs()

    def ok(m: str) -> dict:
        return {"status": "success", "message": f"{fallback_msg}\n{m}" if fallback_msg else m}

    # Preferred path based on resolver
    if manager == "sdkman" and sdk_candidate:
        res = _sdk_install(sdk_candidate, version)
        if res["status"] == "success":
            return ok(res["message"])
        # Fallbacks: apt -> snap
        res2 = _apt_install(apt_name, version)
        if res2["status"] == "success":
            return ok(res2["message"])
        res3 = _snap_install(snap_name, classic_snap)
        if res3["status"] == "success":
            return ok(res3["message"])
        url = generate_smart_tool_url(resolved_tool)
        return {"status": "error", "message": f"Installation failed via SDKMAN, apt and snap for '{resolved_tool}'. See {url}", "manual_url": url}

    if manager == "snap":
        res = _snap_install(snap_name, classic_snap)
        if res["status"] == "success":
            return ok(res["message"])
        # Fallbacks: apt -> SDKMAN
        res2 = _apt_install(apt_name, version)
        if res2["status"] == "success":
            return ok(res2["message"])
        if sdk_candidate:
            res3 = _sdk_install(sdk_candidate, version)
            if res3["status"] == "success":
                return ok(res3["message"])
        url = generate_smart_tool_url(resolved_tool)
        return {"status": "error", "message": f"Installation failed via snap, apt and SDKMAN for '{resolved_tool}'. See {url}", "manual_url": url}

    # Default manager == apt
    res = _apt_install(apt_name, version)
    if res["status"] == "success":
        return ok(res["message"])
    # Fallbacks: snap -> SDKMAN
    res2 = _snap_install(snap_name, classic_snap)
    if res2["status"] == "success":
        return ok(res2["message"])
    if sdk_candidate:
        res3 = _sdk_install(sdk_candidate, version)
        if res3["status"] == "success":
            return ok(res3["message"])

    url = generate_smart_tool_url(resolved_tool)
    return {"status": "error", "message": f"Installation failed for '{resolved_tool}'. See {url}", "manual_url": url}

