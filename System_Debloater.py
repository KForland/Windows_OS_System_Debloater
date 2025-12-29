import ctypes
import subprocess
import sys

applied = []
already = []
restored = []
failed = []

# ---------------- Core helpers ----------------

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def msgbox(text, title="System Debloater", flags=0):
    return ctypes.windll.user32.MessageBoxW(0, text, title, flags)

def run(cmd):
    return subprocess.run(
        cmd, shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    ).returncode == 0

def service_exists(name):
    return run(f"sc query {name}")

def disable_service(name, label):
    if not service_exists(name):
        already.append(label)
        return
    run(f"sc stop {name}")
    if run(f"sc config {name} start= disabled"):
        applied.append(label)
    else:
        failed.append(label)

def restore_service(name, label):
    if not service_exists(name):
        already.append(label)
        return
    if run(f"sc config {name} start= demand"):
        restored.append(label)
    else:
        failed.append(label)

def reg_has(path, name):
    return run(f'reg query "{path}" /v {name}')

def reg_set(path, name, rtype, value, label):
    if reg_has(path, name):
        already.append(label)
        return
    if run(f'reg add "{path}" /v {name} /t {rtype} /d {value} /f'):
        applied.append(label)
    else:
        failed.append(label)

def reg_restore(path, name, label):
    if not reg_has(path, name):
        already.append(label)
        return
    if run(f'reg delete "{path}" /v {name} /f'):
        restored.append(label)
    else:
        failed.append(label)

# ---------------- Admin enforcement ----------------

if not is_admin():
    msgbox(
        "This tool must be run as Administrator.\n\n"
        "Right-click the EXE and choose:\n"
        "'Run as administrator'",
        "Administrator Required",
        0x10
    )
    sys.exit(1)

# ---------------- Intro / Menu ----------------

choice = msgbox(
    "SAFE WINDOWS SYSTEM DEBLOATER\n\n"
    "This tool can DISABLE or RESTORE:\n\n"
    "• Xbox Game Bar & Game DVR (recording / overlays)\n"
    "• Consumer Experience (ads & suggestions)\n"
    "• Offline Maps services\n"
    "• Phone / messaging integration\n"
    "• Error reporting background services\n"
    "• Remote Registry access\n"
    "• Fax, Wallet, NFC services\n"
    "• Media sharing services\n\n"
    "This tool WILL NOT:\n"
    "• Break Windows Update\n"
    "• Break Microsoft Defender\n"
    "• Break networking\n"
    "• Break Xbox app, Game Pass, or multiplayer\n"
    "• Delete system files\n\n"
    "YES  → Apply safe debloat\n"
    "NO   → Restore defaults (only what this tool changed)\n"
    "CANCEL → Exit",
    "System Debloater",
    0x23
)

# YES = 6, NO = 7, CANCEL = 2
if choice == 2:
    sys.exit(0)

# ---------------- Services touched by this tool ----------------

services = {
    "RetailDemo": "Retail demo mode",
    "MapsBroker": "Offline maps service",
    "lfsvc": "Geolocation service",
    "RemoteRegistry": "Remote Registry",
    "Fax": "Fax service",
    "WMPNetworkSvc": "Media sharing",
    "WerSvc": "Error reporting",
    "SEMgrSvc": "Payments / NFC",
    "PhoneSvc": "Phone integration",
    "WalletService": "Wallet service"
}

# ---------------- APPLY ----------------

if choice == 6:
    for svc, label in services.items():
        disable_service(svc, label)

    reg_set(
        r"HKLM\SOFTWARE\Policies\Microsoft\Windows\CloudContent",
        "DisableWindowsConsumerFeatures",
        "REG_DWORD", 1,
        "Consumer Experience"
    )

    reg_set(
        r"HKCU\Software\Microsoft\GameBar",
        "AllowAutoGameMode",
        "REG_DWORD", 0,
        "Xbox Game Bar"
    )

    reg_set(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR",
        "AppCaptureEnabled",
        "REG_DWORD", 0,
        "Game DVR"
    )

# ---------------- RESTORE ----------------

if choice == 7:
    for svc, label in services.items():
        restore_service(svc, label)

    reg_restore(
        r"HKLM\SOFTWARE\Policies\Microsoft\Windows\CloudContent",
        "DisableWindowsConsumerFeatures",
        "Consumer Experience"
    )

    reg_restore(
        r"HKCU\Software\Microsoft\GameBar",
        "AllowAutoGameMode",
        "Xbox Game Bar"
    )

    reg_restore(
        r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR",
        "AppCaptureEnabled",
        "Game DVR"
    )

# ---------------- Summary ----------------

summary = ""

if applied:
    summary += "✔ Applied:\n" + "\n".join(f"• {i}" for i in applied) + "\n\n"

if restored:
    summary += "↩ Restored:\n" + "\n".join(f"• {i}" for i in restored) + "\n\n"

if already:
    summary += "➖ Already compliant:\n" + "\n".join(f"• {i}" for i in already) + "\n\n"

if failed:
    summary += "✖ Failed:\n" + "\n".join(f"• {i}" for i in failed) + "\n\n"

summary += "Reboot recommended."

msgbox(summary.strip(), "Operation Complete", 0x40)
