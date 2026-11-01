"""SquallowTweaks - Benchmark-Speicher und A/B-Vergleich (damit jeder Tweak-Effekt gemessen statt geglaubt wird)."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Optional

# (Schluessel, Label, hoeher_ist_besser, Einheit)
METRICS = [
    ("avg_fps", "Ø FPS", True, ""),
    ("low1_fps", "1 % Low", True, " FPS"),
    ("low01_fps", "0,1 % Low", True, " FPS"),
    ("p99_ms", "99. Perzentil Frametime", False, " ms"),
    ("stutters", "Ruckler", False, ""),
]


class BenchStore:
    def __init__(self, path: Path):
        self.path = path
        self.runs: list[dict] = []
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.runs = data
        except Exception:  # noqa: BLE001
            self.runs = []

    def _save(self):
        try:
            self.path.write_text(json.dumps(self.runs, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def add(self, name: str, stats) -> dict:
        s = asdict(stats) if hasattr(stats, "__dataclass_fields__") else dict(stats)
        run = {"id": uuid.uuid4().hex[:8], "name": name or "Messung", "time": time.strftime("%d.%m. %H:%M"), "stats": s}
        self.runs.insert(0, run)
        self.runs = self.runs[:30]
        self._save()
        return run

    def get(self, run_id: str) -> Optional[dict]:
        return next((r for r in self.runs if r["id"] == run_id), None)

    def delete(self, run_id: str):
        self.runs = [r for r in self.runs if r["id"] != run_id]
        self._save()


def compare(before: dict, after: dict) -> list[dict]:
    """Zeilen fuer die Vergleichstabelle. delta_pct > 0 heisst immer 'besser'."""
    rows = []
    for key, label, higher_better, unit in METRICS:
        a, b = before["stats"].get(key), after["stats"].get(key)
        if a is None or b is None:
            continue
        change = (b - a) / a * 100 if a else 0.0
        better_pct = change if higher_better else -change
        verdict = "besser" if better_pct > 3.0 else ("schlechter" if better_pct < -3.0 else "gleich")
        rows.append({"label": label, "before": a, "after": b, "unit": unit, "delta_pct": better_pct, "verdict": verdict})
    return rows
