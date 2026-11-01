"""SquallowTweaks - Pfade, Einstellungen, Logging, Migration alter RisenTweaks-Daten."""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

APP_NAME = "SquallowTweaks"
APP_VERSION = "5.0.0"
OLD_NAMES = ("RisenTweaks",)


def resource_path(rel: str) -> Path:
    """Datei im Projekt bzw. im PyInstaller-Bundle (sys._MEIPASS)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def data_dir() -> Path:
    root = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    d = Path(root) / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def migrate_old_data(dest: Path) -> list[str]:
    """Uebernimmt Backups aus dem alten Ordner (RisenTweaks), damit Undo weiter funktioniert.
    Der alte Ordner bleibt unveraendert erhalten."""
    moved = []
    root = Path(os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share"))
    for old in OLD_NAMES:
        src = root / old
        if not src.is_dir():
            continue
        for name in ("tweak_state.json", "backup_v2.json", "config_backups"):
            s, d = src / name, dest / name
            if s.exists() and not d.exists():
                try:
                    if s.is_dir():
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                    moved.append(name)
                except OSError:
                    pass
    return moved


DATA = data_dir()
LOG_FILE = DATA / "squallow.log"
STATE_FILE = DATA / "tweak_state.json"
SETTINGS_FILE = DATA / "settings.json"
BENCH_FILE = DATA / "benchmarks.json"
CAPTURE_CSV = DATA / "capture.csv"
MIGRATED = migrate_old_data(DATA)


def log(msg: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}\n")
    except OSError:
        pass


DEFAULT_SETTINGS = {
    "auto_priority": True,        # Fortnite beim Start auf HOCH setzen
    "restore_point": True,        # vor Auto Optimize Wiederherstellungspunkt versuchen
    "profile": "competitive",     # safe | competitive | maxfps
}


class Settings:
    def __init__(self, path: Path = SETTINGS_FILE):
        self.path = path
        self.data = dict(DEFAULT_SETTINGS)
        try:
            if path.exists():
                self.data.update(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:  # noqa: BLE001
            log(f"settings: {exc}")

    def get(self, key):
        return self.data.get(key, DEFAULT_SETTINGS.get(key))

    def set(self, key, value) -> None:
        self.data[key] = value
        try:
            self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except OSError as exc:
            log(f"settings save: {exc}")
