import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("install_service", ROOT / "scripts" / "install_service.py")
svc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(svc)


def test_linux_systemd_unit(tmp_path):
    p = svc.plan("Linux", Path("/opt/zevon"), "/opt/zevon/backend/.venv/bin/python", 9000, tmp_path)
    (unit, text), = p["files"].items()
    assert unit == tmp_path / ".config/systemd/user/zevon.service"
    assert "WorkingDirectory=/opt/zevon/backend" in text and "--port 9000" in text and "Restart=on-failure" in text
    assert ["systemctl", "--user", "enable", "--now", "zevon"] in p["commands"] and "linger" in p["notes"]


def test_macos_launchd_plist(tmp_path):
    p = svc.plan("Darwin", Path("/Users/me/zevon"), "/usr/bin/python3", 8000, tmp_path)
    (plist, text), = p["files"].items()
    assert plist.name == "ai.zevon.plist" and "<key>KeepAlive</key><true/>" in text and "<string>uvicorn</string>" in text
    assert p["commands"][0][:3] == ["launchctl", "load", "-w"]


def test_windows_task_and_unsupported():
    p = svc.plan("Windows", Path("C:/zevon"), "C:/zevon/backend/.venv/Scripts/python.exe", 8000)
    assert p["files"] == {} and p["commands"][0][:4] == ["schtasks", "/Create", "/TN", "Zevon AI"] and "/SC" in p["commands"][0]
    assert p["uninstall"][0][:2] == ["schtasks", "/Delete"]
    try:
        svc.plan("Plan9", Path("."), "py")
        assert False
    except SystemExit:
        pass
