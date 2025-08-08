import os
import re
import shutil
import subprocess
from typing import Optional, Tuple


def _parse_version_tuple(v: str) -> Optional[Tuple[int, ...]]:
    if not v:
        return None
    nums = re.findall(r"\d+", v)
    if not nums:
        return None
    try:
        return tuple(int(n) for n in nums[:4])
    except Exception:
        return None


def _compare_versions(a: str, b: str) -> Optional[int]:
    """Return -1 if a<b, 0 if equal, 1 if a>b; None if not comparable."""
    ta = _parse_version_tuple(a)
    tb = _parse_version_tuple(b)
    if ta is None or tb is None:
        return None
    # Pad to same length
    maxlen = max(len(ta), len(tb))
    ta += (0,) * (maxlen - len(ta))
    tb += (0,) * (maxlen - len(tb))
    if ta < tb:
        return -1
    if ta > tb:
        return 1
    return 0


def _run(cmd: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _get_installed_version(tool: str) -> Optional[str]:
    """Use existing version checker to get installed version (works for non-winget installs too)."""
    try:
        from tools.version_checkers.windows import check_version as _cv
        res = _cv(tool)
        if isinstance(res, dict) and res.get("status") == "success":
            v = res.get("version")
            if v:
                return v
    except Exception:
        pass
    return None


def _find_winget_id(tool: str) -> Optional[str]:
    """Try to determine a Winget package Id for the tool via 'winget list' then fallback to 'winget search'."""
    # Try list (if installed via winget)
    try:
        r = _run(["winget", "list", tool])
        if r.returncode == 0:
            for line in (r.stdout or "").splitlines():
                # Look for a plausible Id token containing a dot and not ending with a dot
                parts = line.split()
                for part in parts:
                    if "." in part and not part.endswith(".") and not part.startswith(".") and len(part) > 2:
                        return part
    except Exception:
        pass
    # Fallback: search
    try:
        r = _run(["winget", "search", tool])
        if r.returncode == 0:
            for line in (r.stdout or "").splitlines()[2:]:
                parts = line.split()
                for part in parts:
                    if "." in part and not part.endswith(".") and not part.startswith(".") and len(part) > 2:
                        return part
    except Exception:
        pass
    return None


def _get_available_version_from_id(pkg_id: str) -> Optional[str]:
    """Query 'winget show --id <id>' and parse the version field as the latest available."""
    try:
        r = _run(["winget", "show", "--id", pkg_id])
        if r.returncode == 0:
            text = (r.stdout or "") + "\n" + (r.stderr or "")
            # Lines like: Version: 1.103.0
            for line in text.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    if k.strip().lower() == "version":
                        v = v.strip()
                        if v:
                            return v
    except Exception:
        pass
    return None


def _upgrade_via_winget(tool: str, pkg_id: Optional[str], target_version: Optional[str]) -> Tuple[bool, str]:
    """Run winget upgrade with either name or id. Returns (ok, output)."""
    base = ["winget", "upgrade"]
    if pkg_id:
        base += ["--id", pkg_id, "--exact"]
    else:
        base += [tool]
    if target_version and target_version != "latest":
        base += ["--version", target_version]
    base += [
        "--silent",
        "--accept-source-agreements",
        "--accept-package-agreements",
    ]
    r = _run(base, timeout=180)
    ok = r.returncode == 0
    output = (r.stdout or "").strip() + ("\n" + (r.stderr or "").strip() if r.stderr else "")
    return ok, output


def handle_tool(tool, version: str = "latest"):
    # Ensure winget exists
    if not shutil.which("winget"):
        return {
            "status": "error",
            "message": "winget is not available on this system. Please install App Installer (winget)."
        }

    try:
        installed_version = _get_installed_version(tool)

        pkg_id = _find_winget_id(tool)
        available_version = _get_available_version_from_id(pkg_id) if pkg_id else None

        # If caller requested a specific version, prefer that as available target
        if version and version != "latest":
            available_version = version

        # If we have both versions and they are equal (or installed >= available), skip upgrade
        if installed_version and available_version:
            cmp = _compare_versions(installed_version, available_version)
            if cmp is not None and cmp >= 0:
                return {
                    "status": "success",
                    "message": f"{tool}: latest version is already installed ({installed_version}).",
                    "installed_version": installed_version,
                    "available_version": available_version,
                    "action": "none"
                }

        # Proceed to upgrade
        ok, output = _upgrade_via_winget(tool, pkg_id, available_version)
        if not ok:
            # If winget indicates no applicable update (often not winget-managed), attempt install fallback
            lowered = output.lower()
            no_update_markers = (
                "no applicable upgrade",
                "no applicable update",
                "no package found",
                "no installed package found",
                "no available upgrade",
            )
            if any(marker in lowered for marker in no_update_markers):
                # Only attempt install if we believe a newer version exists or specific version requested
                should_try_install = True
                if installed_version and available_version:
                    cmp = _compare_versions(installed_version, available_version)
                    should_try_install = (cmp is None) or (cmp < 0)

                if should_try_install:
                    ok_i, out_i = _install_via_winget(tool, pkg_id, available_version)
                    if ok_i:
                        new_version = _get_installed_version(tool) or available_version or installed_version
                        msg = f"Installed latest {tool} via winget (install fallback)"
                        if installed_version and new_version:
                            msg = f"Updated {tool} from {installed_version} to {new_version} via winget (install fallback)"
                        return {
                            "status": "success",
                            "message": msg,
                            "installed_version": installed_version,
                            "available_version": available_version,
                            "new_version": new_version,
                            "action": "installed",
                            "winget_id": pkg_id
                        }

                # Could not install or not needed
                msg = f"{tool}: no newer version available via winget."
                if installed_version:
                    msg += f" Installed: {installed_version}."
                if available_version:
                    msg += f" Available: {available_version}."
                return {
                    "status": "success",
                    "message": msg,
                    "installed_version": installed_version,
                    "available_version": available_version,
                    "action": "none"
                }
            return {"status": "error", "message": output or f"Failed to upgrade {tool} via winget."}

        # Re-check version after upgrade
        new_version = _get_installed_version(tool) or installed_version
        msg = f"Upgraded {tool}"
        if installed_version and new_version:
            msg += f" from {installed_version} to {new_version}"
        elif new_version:
            msg += f" to {new_version}"
        msg += " (Windows/winget)"

        return {
            "status": "success",
            "message": msg,
            "installed_version": installed_version,
            "available_version": available_version,
            "new_version": new_version,
            "action": "upgraded",
            "winget_id": pkg_id
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


def _install_via_winget(tool: str, pkg_id: Optional[str], target_version: Optional[str]) -> Tuple[bool, str]:
    """Run winget install with either name or id. Returns (ok, output)."""
    base = ["winget", "install"]
    if pkg_id:
        base += ["--id", pkg_id, "--exact"]
    else:
        base += [tool]
    if target_version and target_version != "latest":
        base += ["--version", target_version]
    base += [
        "--silent",
        "--accept-source-agreements",
        "--accept-package-agreements",
    ]
    r = _run(base, timeout=300)
    ok = r.returncode == 0
    output = (r.stdout or "").strip() + ("\n" + (r.stderr or "").strip() if r.stderr else "")
    return ok, output
