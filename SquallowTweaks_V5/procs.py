"""SquallowTweaks - Prozessverwaltung (Snapshot, Prioritaet, Beenden mit Schutz fuer Systemprozesse)."""
from __future__ import annotations

import os
from typing import Optional

import psutil

IS_WINDOWS = os.name == "nt"

PROTECTED = {
    "system", "system idle process", "registry", "memory compression", "smss.exe", "csrss.exe", "wininit.exe",
    "services.exe", "lsass.exe", "winlogon.exe", "svchost.exe", "fontdrvhost.exe", "dwm.exe", "explorer.exe",
    "msmpeng.exe", "securityhealthservice.exe", "sihost.exe", "taskhostw.exe", "ctfmon.exe", "audiodg.exe",
    "squallowtweaks.exe", "python.exe", "pythonw.exe", "wudfhost.exe", "spoolsv.exe", "searchindexer.exe",
}

PRIORITIES = ("Hoch", "Normal", "Niedrig")


def is_protected(pid: int, name: str) -> bool:
    return pid <= 4 or pid == os.getpid() or name.lower() in PROTECTED


def _classes():
    return {"Hoch": getattr(psutil, "HIGH_PRIORITY_CLASS", None),
            "Normal": getattr(psutil, "NORMAL_PRIORITY_CLASS", None),
            "Niedrig": getattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS", None)}


def prio_label(nice) -> str:
    for label, cls in _classes().items():
        if cls is not None and nice == cls:
            return label
    if IS_WINDOWS and nice == getattr(psutil, "IDLE_PRIORITY_CLASS", -1):
        return "Niedrig"
    if IS_WINDOWS and nice == getattr(psutil, "REALTIME_PRIORITY_CLASS", -1):
        return "Echtzeit"
    return "–"


class ProcSampler:
    """Haelt Process-Objekte, damit cpu_percent(None) zwischen den Aufrufen korrekt misst."""

    def __init__(self):
        self._procs: dict[int, psutil.Process] = {}
        self.ncpu = psutil.cpu_count() or 1

    def snapshot(self) -> list[dict]:
        live = set(psutil.pids())
        for pid in list(self._procs):
            if pid not in live:
                del self._procs[pid]
        for pid in live:
            if pid not in self._procs:
                try:
                    p = psutil.Process(pid)
                    p.cpu_percent(None)
                    self._procs[pid] = p
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        rows = []
        for pid, p in list(self._procs.items()):
            try:
                with p.oneshot():
                    name = p.name()
                    cpu = p.cpu_percent(None) / self.ncpu
                    ram = p.memory_info().rss
                    status = p.status()
                    try:
                        prio = prio_label(p.nice())
                    except (psutil.AccessDenied, OSError):
                        prio = "–"
                rows.append({"pid": pid, "name": name, "cpu": cpu, "ram": ram, "status": status, "prio": prio,
                             "protected": is_protected(pid, name)})
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue
        return rows


def set_priority(pid: int, level: str) -> tuple[bool, str]:
    try:
        p = psutil.Process(pid)
        name = p.name()
    except psutil.Error as exc:
        return False, f"Prozess nicht verfügbar: {exc}"
    if is_protected(pid, name):
        return False, "Systemprozess: geschützt."
    cls = _classes().get(level)
    if cls is None:
        return False, "Priorität auf diesem System nicht unterstützt."
    try:
        p.nice(cls)
        return True, f"{name}: Priorität {level}."
    except psutil.Error as exc:
        return False, f"Nicht möglich: {exc}"


def terminate(pid: int) -> tuple[bool, str]:
    try:
        p = psutil.Process(pid)
        name = p.name()
    except psutil.Error as exc:
        return False, f"Prozess nicht verfügbar: {exc}"
    if is_protected(pid, name):
        return False, "Systemprozess: geschützt und kann nicht beendet werden."
    try:
        p.terminate()
        return True, f"Beenden angefordert: {name}."
    except psutil.Error as exc:
        return False, f"Nicht möglich: {exc}"


def fmt_ram(b: float) -> str:
    return f"{b / 1073741824:.2f} GB" if b >= 1073741824 else f"{b / 1048576:.0f} MB"
