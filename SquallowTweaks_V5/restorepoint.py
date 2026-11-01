"""SquallowTweaks - Windows-Wiederherstellungspunkt (best effort, nur mit Adminrechten und aktivem Systemschutz)."""
from __future__ import annotations

import os
import subprocess

IS_WINDOWS = os.name == "nt"
DESCRIPTION = "SquallowTweaks vor Optimierung"


def _ps(script: str, timeout: int) -> tuple[int, str]:
    try:
        p = subprocess.run(["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                           capture_output=True, text=True, errors="replace", timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        return 1, str(exc)


def create() -> tuple[bool, str]:
    """-> (erstellt, Meldung). Windows erlaubt standardmaessig nur einen Punkt pro 24 h."""
    if not IS_WINDOWS:
        return False, "Nur unter Windows."
    script = ("$ErrorActionPreference='Stop';try{Checkpoint-Computer -Description '%s' -RestorePointType MODIFY_SETTINGS;"
              "$r=Get-ComputerRestorePoint | Where-Object {$_.Description -eq '%s'} | Sort-Object SequenceNumber | Select-Object -Last 1;"
              "if($r -and ([Management.ManagementDateTimeConverter]::ToDateTime($r.CreationTime) -gt (Get-Date).AddMinutes(-10))){'CREATED'}else{'SKIPPED'}}"
              "catch{'ERR:'+$_.Exception.Message}") % (DESCRIPTION, DESCRIPTION)
    code, out = _ps(script, 120)
    last = (out.strip().splitlines() or [""])[-1]
    if last == "CREATED":
        return True, "Wiederherstellungspunkt erstellt."
    if last == "SKIPPED":
        return False, "Windows hat keinen neuen Punkt angelegt (max. 1 pro 24 h oder Systemschutz aus)."
    return False, f"Nicht möglich: {last[4:] if last.startswith('ERR:') else last or 'unbekannter Fehler'}"[:200]
