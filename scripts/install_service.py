"""Run Zevon in the background and start it automatically at login/boot (Linux systemd, macOS launchd, Windows Task Scheduler).
    python scripts/install_service.py              # dry run: shows exactly what would be installed
    python scripts/install_service.py --install
    python scripts/install_service.py --uninstall
Tip: put Zevon on a machine that is always on (home server, mini PC, Raspberry Pi) so your phone can always reach it."""
import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def plan(os_name: str, root: Path, python: str, port: int = 8000, home: Path | None = None) -> dict:
    """Pure function: returns the files to write and commands to run. (Unit-tested.)"""
    home = home or Path.home()
    backend = root / "backend"
    run = f"{python} -m uvicorn app.main:app --host 0.0.0.0 --port {port}"
    if os_name == "Linux":
        unit = home / ".config" / "systemd" / "user" / "zevon.service"
        text = ("[Unit]\nDescription=Zevon AI\nAfter=network-online.target\n\n[Service]\n"
                f"WorkingDirectory={backend}\nExecStart={run}\nRestart=on-failure\nRestartSec=5\n\n"
                "[Install]\nWantedBy=default.target\n")
        return {"files": {unit: text},
                "commands": [["systemctl", "--user", "daemon-reload"], ["systemctl", "--user", "enable", "--now", "zevon"]],
                "uninstall": [["systemctl", "--user", "disable", "--now", "zevon"]], "remove": [unit],
                "notes": "To keep it running when you are logged out: sudo loginctl enable-linger $USER"}
    if os_name == "Darwin":
        plist = home / "Library" / "LaunchAgents" / "ai.zevon.plist"
        args = "".join(f"\n    <string>{a}</string>" for a in [python, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port)])
        text = ('<?xml version="1.0" encoding="UTF-8"?>\n<plist version="1.0"><dict>\n'
                f'  <key>Label</key><string>ai.zevon</string>\n  <key>ProgramArguments</key><array>{args}\n  </array>\n'
                f'  <key>WorkingDirectory</key><string>{backend}</string>\n  <key>RunAtLoad</key><true/>\n'
                f'  <key>KeepAlive</key><true/>\n  <key>StandardOutPath</key><string>{root}/data/zevon.log</string>\n'
                f'  <key>StandardErrorPath</key><string>{root}/data/zevon.log</string>\n</dict></plist>\n')
        return {"files": {plist: text}, "commands": [["launchctl", "load", "-w", str(plist)]],
                "uninstall": [["launchctl", "unload", "-w", str(plist)]], "remove": [plist],
                "notes": "Starts when you log in. Logs: data/zevon.log"}
    if os_name == "Windows":
        tr = f'cmd /c "cd /d {backend} && {python} -m uvicorn app.main:app --host 0.0.0.0 --port {port}"'
        return {"files": {}, "commands": [["schtasks", "/Create", "/TN", "Zevon AI", "/SC", "ONLOGON", "/TR", tr, "/F"],
                                          ["schtasks", "/Run", "/TN", "Zevon AI"]],
                "uninstall": [["schtasks", "/Delete", "/TN", "Zevon AI", "/F"]], "remove": [],
                "notes": "Starts when you log in. Also allow it through Windows Firewall for private networks."}
    raise SystemExit(f"Unsupported OS: {os_name}")


def venv_python(root: Path) -> str:
    for cand in (root / "backend" / ".venv" / "bin" / "python", root / "backend" / ".venv" / "Scripts" / "python.exe"):
        if cand.exists():
            return str(cand)
    return sys.executable


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--port", type=int, default=int(os.getenv("ZEVON_PORT", "8000")))
    a = ap.parse_args()
    p = plan(platform.system(), ROOT, venv_python(ROOT), a.port)
    if a.uninstall:
        for c in p["uninstall"]:
            subprocess.run(c, check=False)
        for f in p["remove"]:
            f.unlink(missing_ok=True)
        print("Zevon service removed.")
        return
    for path, text in p["files"].items():
        print(f"--- {path}\n{text}")
        if a.install:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    for c in p["commands"]:
        print("$", " ".join(c))
        if a.install:
            subprocess.run(c, check=True)
    print(p["notes"])
    if not a.install:
        print("\n(dry run: re-run with --install to apply)")


if __name__ == "__main__":
    main()
