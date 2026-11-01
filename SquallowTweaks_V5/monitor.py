"""SquallowTweaks - Hintergrund-Monitor. Ein Thread sammelt alle Messwerte; die UI liest nur `latest`.
So bleibt die Oberflaeche fluessig (keine psutil-/nvidia-smi-Aufrufe im UI-Thread)."""
from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
from collections import deque
from typing import Callable, Optional

import psutil

FORTNITE_EXE = "FortniteClient-Win64-Shipping.exe"
IS_WINDOWS = os.name == "nt"
HIST_LEN = 60


def parse_gpu_csv(text: str) -> dict:
    """nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,clocks.gr,clocks.mem"""
    if not text.strip():
        return {"available": False}
    parts = [p.strip() for p in text.strip().splitlines()[0].split(",")]
    if len(parts) < 5:
        return {"available": False}

    def num(i):
        try:
            return float(parts[i])
        except (ValueError, IndexError):
            return None
    return {"available": True, "name": parts[0], "usage": num(1), "mem_used": num(2), "mem_total": num(3),
            "temp": num(4), "power": num(5), "clock": num(6), "mem_clock": num(7)}


class Monitor(threading.Thread):
    def __init__(self, auto_priority: Callable[[], bool] = lambda: False, log: Callable[[str], None] = lambda m: None):
        super().__init__(daemon=True, name="squallow-monitor")
        self.auto_priority = auto_priority
        self.log = log
        self.latest: dict = {}
        self.hist = {k: deque([0.0] * HIST_LEN, maxlen=HIST_LEN) for k in ("cpu", "gpu", "ram", "down", "up")}
        self._stop_evt = threading.Event()
        self._net = psutil.net_io_counters()
        self._net_t = time.time()
        self._gpu: dict = {"available": False}
        self._gpu_t = 0.0
        self._fn_proc: Optional[psutil.Process] = None
        self._fn_t = 0.0
        self._fn: Optional[dict] = None
        self.gpu_name = ""

    def stop(self):
        self._stop_evt.set()

    # ---- einzelne Quellen ------------------------------------------------
    def _read_gpu(self) -> dict:
        exe = shutil.which("nvidia-smi")
        if not exe:
            return {"available": False}
        try:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WINDOWS else 0
            p = subprocess.run([exe, "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,clocks.gr,clocks.mem",
                                "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=4, creationflags=flags)
            return parse_gpu_csv(p.stdout) if p.returncode == 0 else {"available": False}
        except Exception:  # noqa: BLE001
            return {"available": False}

    def _find_fortnite(self) -> Optional[psutil.Process]:
        if self._fn_proc is not None:
            try:
                if self._fn_proc.is_running() and self._fn_proc.name().lower() == FORTNITE_EXE.lower():
                    return self._fn_proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            self._fn_proc = None
        for p in psutil.process_iter(["name"]):
            try:
                if (p.info.get("name") or "").lower() == FORTNITE_EXE.lower():
                    p.cpu_percent(None)
                    self._fn_proc = p
                    return p
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _fortnite_info(self) -> Optional[dict]:
        p = self._find_fortnite()
        if p is None:
            return None
        info = {"pid": p.pid, "cpu": 0.0, "ram_mb": 0.0, "high": False, "boosted": False}
        try:
            info["cpu"] = p.cpu_percent(None) / (psutil.cpu_count() or 1)
            info["ram_mb"] = p.memory_info().rss / 1048576
            high = getattr(psutil, "HIGH_PRIORITY_CLASS", None)
            if high is not None:
                if p.nice() != high and self.auto_priority():
                    p.nice(high)
                    info["boosted"] = True
                    self.log(f"Fortnite PID {p.pid}: Prioritaet HOCH gesetzt")
                info["high"] = p.nice() == high
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return info

    # ---- Hauptschleife ---------------------------------------------------
    def sample(self) -> dict:
        now = time.time()
        d: dict = {"t": now}
        d["cpu"] = psutil.cpu_percent(None)
        try:
            f = psutil.cpu_freq()
            d["cpu_mhz"] = f.current if f else None
        except Exception:  # noqa: BLE001
            d["cpu_mhz"] = None
        m = psutil.virtual_memory()
        d.update(ram=m.percent, ram_used=m.used, ram_total=m.total)
        try:
            root = os.environ.get("SystemDrive", "C:") + "\\" if IS_WINDOWS else "/"
            du = psutil.disk_usage(root)
            d.update(disk=du.percent, disk_free=du.free, disk_total=du.total)
        except Exception:  # noqa: BLE001
            d.update(disk=None, disk_free=0, disk_total=0)
        net = psutil.net_io_counters()
        dt = max(0.001, now - self._net_t)
        d["down"] = max(0, net.bytes_recv - self._net.bytes_recv) / dt
        d["up"] = max(0, net.bytes_sent - self._net.bytes_sent) / dt
        self._net, self._net_t = net, now
        if now - self._gpu_t >= 2.0:
            self._gpu, self._gpu_t = self._read_gpu(), now
            if self._gpu.get("name"):
                self.gpu_name = self._gpu["name"]
        d["gpu"] = self._gpu
        if now - self._fn_t >= 2.0:
            self._fn, self._fn_t = self._fortnite_info(), now
        d["fortnite"] = self._fn
        d["uptime"] = max(0.0, now - psutil.boot_time())
        return d

    def run(self):
        psutil.cpu_percent(None)
        while not self._stop_evt.is_set():
            try:
                d = self.sample()
                self.hist["cpu"].append(d["cpu"])
                self.hist["ram"].append(d["ram"])
                self.hist["gpu"].append((d["gpu"].get("usage") or 0.0) if d["gpu"].get("available") else 0.0)
                self.hist["down"].append(d["down"] / 125000.0)   # Mbit/s
                self.hist["up"].append(d["up"] / 125000.0)
                self.latest = d
            except Exception as exc:  # noqa: BLE001
                self.log(f"monitor: {exc}")
            self._stop_evt.wait(1.0)
