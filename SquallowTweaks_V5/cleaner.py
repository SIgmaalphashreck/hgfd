"""SquallowTweaks - Bereinigung (Temp, Windows-Temp, Papierkorb, SSD-TRIM)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

IS_WINDOWS = os.name == "nt"


def targets() -> dict[str, Path]:
    out = {"Benutzer-Temp": Path(tempfile.gettempdir())}
    if IS_WINDOWS:
        out["Windows-Temp"] = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "Temp"
    return out


def dir_size(path: Path, limit_s: float = 5.0) -> int:
    total, t0 = 0, time.time()
    stack = [path]
    while stack and time.time() - t0 < limit_s:
        cur = stack.pop()
        try:
            with os.scandir(cur) as it:
                for e in it:
                    try:
                        if e.is_symlink():
                            continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(Path(e.path))
                        else:
                            total += e.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def clean_dir(path: Path) -> tuple[int, int]:
    """Loescht den Inhalt, ueberspringt gesperrte Dateien. -> (freigegebene Bytes, Fehlversuche)"""
    freed = failed = 0
    try:
        entries = list(os.scandir(path))
    except OSError:
        return 0, 0
    for e in entries:
        try:
            if e.is_dir(follow_symlinks=False):
                size = dir_size(Path(e.path), 3.0)
                shutil.rmtree(e.path, ignore_errors=False)
            else:
                size = e.stat(follow_symlinks=False).st_size
                os.unlink(e.path)
            freed += size
        except OSError:
            failed += 1
    return freed, failed


def _ps(script: str, timeout: int = 60) -> tuple[int, str]:
    if not IS_WINDOWS:
        return 1, ""
    try:
        p = subprocess.run(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                           capture_output=True, text=True, errors="replace", timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def recycle_size() -> int:
    code, out = _ps("$s=(New-Object -ComObject Shell.Application).NameSpace(0xA); "
                    "[long](($s.Items() | Measure-Object -Property Size -Sum).Sum)", 20)
    try:
        return int(float(out.strip().splitlines()[-1])) if code == 0 and out.strip() else 0
    except ValueError:
        return 0


def empty_recycle() -> bool:
    code, _ = _ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", 60)
    return code == 0


def trim_system_drive() -> tuple[bool, str]:
    if not IS_WINDOWS:
        return False, "Nur unter Windows."
    drive = os.environ.get("SystemDrive", "C:")
    code, out = _ps(f"Optimize-Volume -DriveLetter {drive[0]} -ReTrim -ErrorAction Stop", 180)
    return code == 0, out[:200] or ("TRIM ausgeführt." if code == 0 else "TRIM fehlgeschlagen (kein SSD-Laufwerk oder keine Adminrechte).")


def fmt_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"
