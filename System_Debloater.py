import ctypes
import json
import os
import re
import subprocess
import sys
from datetime import datetime

# =========================
# Config
# =========================

APP_NAME = "System Debloater"
STATE_DIR = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "WinTools", "SystemDebloater")
STATE_FILE = os.path.join(STATE_DIR, "state.json")

SERVICES = {
    "RetailDemo": "Retail demo mode",
    "MapsBroker": "Offline maps service",
    "lfsvc": "Geolocation service",
    "RemoteRegistry": "Remote Registry",
    "Fax": "Fax service",
    "WMPNetworkSvc": "Media sharing",
    "WerSvc": "Error reporting",
    "SEMgrSvc": "Payments / NFC",
    "PhoneSvc": "Phone integration",
    "WalletService": "Wallet service",
}

REG_TARGETS = [
    # (path, name, type, desired_value, label)
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableWindowsConsumerFeatures", "REG_DWORD", 1, "Consumer Experience"),
    (r"HKCU\Software\Microsoft\GameBar", "AllowAutoGameMode", "REG_DWORD", 0, "Xbox Game Bar"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", "REG_DWORD", 0, "Game DVR"),
]

# =========================
# Runtime buckets
# =========================

applied = []
already = []
restored = []
failed = []
audit = []

# =========================
# Core helpers
# =========================

def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False

def msgbox(text: str, title: str = APP_NAME, flags: int = 0) -> int:
    return ctypes.windll.user32.MessageBoxW(0, text, title, flags)

def run(cmd: str):
    """Run command and return (ok, stdout)."""
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    return (p.returncode == 0), (p.stdout or "")

def ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)

def load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"version": 1, "created": datetime.utcnow().isoformat() + "Z", "services": {}, "registry": {}}

def save_state(state):
    ensure_state_dir()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

# =========================
# Service helpers
# =========================

def service_exists(name: str) -> bool:
    ok, _ = run(f"sc query {name}")
    return ok

def get_service_start_type(name: str):
    """
    Returns one of: 'AUTO_START', 'DEMAND_START', 'DISABLED', 'BOOT_START', 'SYSTEM_START'
    or None if not found / cannot query.
    """
    ok, out = run(f"sc qc {name}")
    if not ok:
        return None
    for line in out.splitlines():
        if "START_TYPE" in line:
            # line example: START_TYPE         : 4   DISABLED
            parts = line.split()
            if parts:
                return parts[-1].strip()
    return None

def set_service_start_type(name: str, target: str) -> bool:
    """
    sc config expects: start= auto | demand | disabled
    """
    mapping = {
        "AUTO_START": "auto",
        "DEMAND_START": "demand",
        "DISABLED": "disabled",
    }
    sc_val = mapping.get(target)
    if not sc_val:
        return False
    ok, _ = run(f"sc config {name} start= {sc_val}")
    return ok

def disable_service(name: str, label: str, state, mode: str):
    if not service_exists(name):
        already.append(f"{label} (service not present)")
        return

    current = get_service_start_type(name)
    if current is None:
        failed.append(f"{label} (unable to query)")
        return

    if current == "DISABLED":
        already.append(label)
        return

    if mode == "audit":
        audit.append(label)
        return

    # Record original state once, so restore is accurate
    if name not in state["services"]:
        state["services"][name] = {"label": label, "original_start_type": current}

    # Stop it (ignore errors if already stopped)
    run(f"sc stop {name}")

    if set_service_start_type(name, "DISABLED"):
        applied.append(label)
    else:
        failed.append(label)

def restore_service(name: str, label: str, state, mode: str):
    if not service_exists(name):
        already.append(f"{label} (service not present)")
        return

    entry = state["services"].get(name)
    if not entry:
        already.append(f"{label} (not changed by this tool)")
        return

    original = entry.get("original_start_type")
    if original not in ("AUTO_START", "DEMAND_START", "DISABLED"):
        failed.append(f"{label} (unknown original state)")
        return

    current = get_service_start_type(name)
    if current is None:
        failed.append(f"{label} (unable to query)")
        return

    if current == original:
        already.append(label)
        return

    if mode == "audit":
        audit.append(f"{label} (would restore to {original})")
        return

    if set_service_start_type(name, original):
        restored.append(label)
    else:
        failed.append(label)

# =========================
# Registry helpers
# =========================

def reg_query_value(path: str, name: str):
    ok, out = run(f'reg query "{path}" /v "{name}"')
    if not ok:
        return None  # not present
    # Typical output: <name>  <type>  <value>
    # We'll parse last token as value, but handle hex for DWORD.
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    for ln in lines:
        if re.search(rf"\b{name}\b", ln, re.IGNORECASE):
            parts = ln.split()
            if len(parts) >= 3:
                rtype = parts[-2]
                rval = parts[-1]
                return {"type": rtype, "raw": rval}
    return None

def dword_matches(raw: str, desired_int: int) -> bool:
    # reg query returns DWORD as 0x1, 0x0, etc
    try:
        if raw.lower().startswith("0x"):
            return int(raw, 16) == desired_int
        return int(raw) == desired_int
    except Exception:
        return False

def ensure_reg(path: str, name: str, rtype: str, desired_value, label: str, state, mode: str):
    cur = reg_query_value(path, name)

    # Determine if already at desired value
    if cur:
        if rtype.upper() == "REG_DWORD" and cur["type"].upper() == "REG_DWORD":
            if dword_matches(cur["raw"], int(desired_value)):
                already.append(label)
                return
        else:
            # Non-DWORD: simple string compare
            if str(desired_value) == str(cur["raw"]):
                already.append(label)
                return

    if mode == "audit":
        audit.append(label)
        return

    # Record original state once
    key = f"{path}\\{name}"
    if key not in state["registry"]:
        state["registry"][key] = {"label": label, "path": path, "name": name, "original": cur}

    ok, _ = run(f'reg add "{path}" /v "{name}" /t {rtype} /d {desired_value} /f')
    if ok:
        applied.append(label)
    else:
        failed.append(label)

def restore_reg(path: str, name: str, label: str, state, mode: str):
    key = f"{path}\\{name}"
    entry = state["registry"].get(key)
    if not entry:
        already.append(f"{label} (not changed by this tool)")
        return

    original = entry.get("original")  # None means it did not exist before
    cur = reg_query_value(path, name)

    # If original was None, restore means delete value if present
    if original is None:
        if cur is None:
            already.append(label)
            return
        if mode == "audit":
            audit.append(f"{label} (would delete)")
            return
        ok, _ = run(f'reg delete "{path}" /v "{name}" /f')
        if ok:
            restored.append(label)
        else:
            failed.append(label)
        return

    # Otherwise restore original value
    if cur and original and cur["type"].upper() == original["type"].upper() and cur["raw"].lower() == original["raw"].lower():
        already.append(label)
        return

    if mode == "audit":
        audit.append(f"{label} (would restore)")
        return

    ok, _ = run(f'reg add "{path}" /v "{name}" /t {original["type"]} /d {original["raw"]} /f')
    if ok:
        restored.append(label)
    else:
        failed.append(label)

# =========================
# UI + Main
# =========================

def build_summary(mode: str) -> str:
    lines = []
    lines.append(f"{APP_NAME} - {mode.upper()} نتیجه\n")

    if applied:
        lines.append("✔ Applied (changed this run):")
        lines.extend([f"• {x}" for x in applied])
        lines.append("")

    if restored:
        lines.append("↩ Restored (changed this run):")
        lines.extend([f"• {x}" for x in restored])
        lines.append("")

    if already:
        lines.append("➖ Already compliant / no change needed:")
        lines.extend([f"• {x}" for x in already])
        lines.append("")

    if audit:
        lines.append("🔍 Would change (audit mode):")
        lines.extend([f"• {x}" for x in audit])
        lines.append("")

    if failed:
        lines.append("✖ Failed:")
        lines.extend([f"• {x}" for x in failed])
        lines.append("")

    lines.append("Reboot recommended.")
    return "\n".join(lines).strip()

def main():
    if not is_admin():
        msgbox(
            "This tool must be run as Administrator.\n\n"
            "Right-click the EXE or script and choose:\n"
            "'Run as administrator'",
            "Administrator Required",
            0x10
        )
        sys.exit(1)

    choice = msgbox(
        "SAFE WINDOWS SYSTEM DEBLOATER\n\n"
        "YES  → Apply safe debloat\n"
        "NO   → Restore (only what this tool changed)\n"
        "CANCEL → Audit mode (no changes)\n\n"
        "This tool does not delete system files.",
        APP_NAME,
        0x23
    )

    # YES=6, NO=7, CANCEL=2
    if choice == 2:
        mode = "audit"
    elif choice == 6:
        mode = "apply"
    elif choice == 7:
        mode = "restore"
    else:
        sys.exit(0)

    state = load_state()

    if mode in ("apply", "audit"):
        for svc, label in SERVICES.items():
            disable_service(svc, label, state, mode)

        for path, name, rtype, desired, label in REG_TARGETS:
            ensure_reg(path, name, rtype, desired, label, state, mode)

        if mode == "apply":
            state["last_apply"] = datetime.utcnow().isoformat() + "Z"
            save_state(state)

    if mode in ("restore", "audit"):
        # Restore only what we changed
        for svc, label in SERVICES.items():
            restore_service(svc, label, state, mode)

        for path, name, _, _, label in REG_TARGETS:
            restore_reg(path, name, label, state, mode)

        if mode == "restore":
            state["last_restore"] = datetime.utcnow().isoformat() + "Z"
            save_state(state)

    msgbox(build_summary(mode), "Operation Complete", 0x40)

if __name__ == "__main__":
    main()
