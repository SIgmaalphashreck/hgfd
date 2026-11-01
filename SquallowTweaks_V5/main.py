"""SquallowTweaks - Windows Gaming Optimizer (Fortnite-Fokus).

Architektur: main.py = Fenster + Dienste, pages/* = Seiten (lazy gebaut), monitor.py = Messthread,
tweaklib.py = Tweak-Engine (Backup, Verifikation, Undo), alles Schwere laeuft in Hintergrundthreads.
"""
from __future__ import annotations

import ctypes
import importlib
import os
import queue
import sys
import threading
import time
from pathlib import Path

import psutil

IS_WINDOWS = os.name == "nt"

import paths
from paths import APP_NAME, APP_VERSION, BENCH_FILE, STATE_FILE, Settings, log, resource_path

import tweaklib
from bench import BenchStore
from monitor import Monitor


# --------------------------------------------------------------------------- Selbsttest (CI, ohne Fenster)
def selftest() -> int:
    import tempfile
    lines, problems = [], []

    def check(name, fn):
        try:
            lines.append(f"OK    {name}: {fn()}")
        except Exception as exc:  # noqa: BLE001
            problems.append(name)
            lines.append(f"FAIL  {name}: {exc!r}")

    import tkinter
    check("Tcl/Tk", lambda: tkinter.Tcl().eval("info patchlevel"))
    import customtkinter
    check("customtkinter", lambda: getattr(customtkinter, "__version__", "importiert"))
    check("psutil", lambda: psutil.__version__)
    check("PIL-Icons", lambda: __import__("icons").pil_icon("tweaks", 20).size)
    check("Assets", lambda: f"{resource_path('assets/squallow.ico').exists()} / {resource_path('assets/bird.png').exists()}")
    check("winreg", lambda: tweaklib.WinRegBackend().read(r"Software\Microsoft\Windows\CurrentVersion\Explorer", "NoSuchValue")[0])
    check("Ping-Parser", lambda: __import__("netlab").parse_ping_reply("Reply from 1.1.1.1: bytes=32 time=12ms TTL=57"))
    check("Frame-Statistik", lambda: round(__import__("fnmon").compute_frame_stats([4.0] * 100).avg_fps, 1))
    check("PresentMon gebündelt", lambda: str(__import__("fnmon").find_presentmon() or "nicht gefunden"))

    def roundtrip():
        with tempfile.TemporaryDirectory() as d:
            eng = tweaklib.TweakEngine(tweaklib.MemoryBackend(), Path(d) / "s.json", admin_check=lambda: True)
            t = next(x for x in tweaklib.build_catalog() if x.id == "game_dvr")
            a, u = eng.apply(t), eng.undo(t)
            if not (a.ok and u.ok):
                raise RuntimeError(f"{a.message} / {u.message}")
            return "apply+undo verifiziert"
    check("Tweak-Engine", roundtrip)
    check("Katalog", lambda: f"{len(tweaklib.build_catalog())} Einträge")
    for mod in ("pages.dashboard", "pages.tweaks", "pages.fortnite", "pages.benchmark", "pages.processes",
                "pages.network", "pages.cleanup", "pages.settings"):
        check(mod, lambda m=mod: importlib.import_module(m).__name__)
    try:
        (paths.DATA / "selftest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass
    print("\n".join(lines))
    return 2 if problems else 0


if "--selftest" in sys.argv:
    sys.exit(selftest())

import customtkinter as ctk
from PIL import Image

import fx
import kit
import theme as T
from icons import ctk_icon

PAGES = [
    # key, Titel, Icon, Modul, Klasse, Sektion
    ("dashboard", "Dashboard", "dashboard", "pages.dashboard", "DashboardPage", "ÜBERSICHT"),
    ("tweaks", "Tweaks", "tweaks", "pages.tweaks", "TweaksPage", "OPTIMIERUNG"),
    ("fortnite", "Fortnite", "game", "pages.fortnite", "FortnitePage", None),
    ("benchmark", "Benchmark", "bench", "pages.benchmark", "BenchmarkPage", None),
    ("processes", "Prozesse", "process", "pages.processes", "ProcessesPage", "SYSTEM"),
    ("network", "Netzwerk", "network", "pages.network", "NetworkPage", None),
    ("cleanup", "Bereinigung", "cleanup", "pages.cleanup", "CleanupPage", None),
    ("settings", "Einstellungen", "settings", "pages.settings", "SettingsPage", None),
]
FALLBACK = {"power_ultimate": "power_high"}


class NavItem(ctk.CTkFrame):
    def __init__(self, parent, text, icon, command):
        super().__init__(parent, fg_color="transparent", height=42)
        self.icon_n = ctk_icon(icon, 20, "#8E91AD")
        self.icon_a = ctk_icon(icon, 20, "#C4B5FD")
        self.accent = ctk.CTkFrame(self, width=3, height=24, corner_radius=2, fg_color=T.SIDEBAR)
        self.accent.place(x=0, rely=0.5, anchor="w")
        self.btn = ctk.CTkButton(self, text="   " + text, image=self.icon_n, compound="left", anchor="w", height=40,
                                 corner_radius=10, fg_color=T.SIDEBAR, hover_color="#14141F", text_color=T.TEXT2,
                                 font=kit.font(13, False), command=command)
        self.btn.pack(fill="x", padx=(12, 10), pady=1)

    def set_active(self, on: bool):
        self.btn.configure(fg_color=T.VIOLET_D if on else T.SIDEBAR, text_color=T.TEXT if on else T.TEXT2,
                           image=self.icon_a if on else self.icon_n)
        self.accent.configure(fg_color=T.VIOLET_L if on else T.SIDEBAR)


class App(ctk.CTk):
    def __init__(self):
        ctk.set_appearance_mode("dark")
        super().__init__(fg_color=T.BG)
        self.title(APP_NAME)
        self.geometry("1380x880")
        self.minsize(1180, 720)
        self.alive = True
        self.settings = Settings()
        self.catalog = tweaklib.build_catalog()
        self.by_id = {t.id: t for t in self.catalog}
        self.monitor = Monitor(auto_priority=lambda: bool(self.settings.get("auto_priority")), log=log)
        self.engine = tweaklib.TweakEngine(tweaklib.WinRegBackend(), STATE_FILE, hooks=tweaklib.DEFAULT_HOOKS, logger=log,
                                           fortnite_running=lambda: bool(self.monitor.latest.get("fortnite")))
        self.bench = BenchStore(BENCH_FILE)
        self.states: dict[str, tuple[str, str]] = {}
        self.pending: dict[str, bool] = {}
        self._state_cbs: list = []
        self._q: queue.Queue = queue.Queue()
        self.pages: dict = {}
        self.nav: dict = {}
        self.current = None
        self._busy = False
        self._icon()
        self._build_shell()
        self.monitor.start()
        self._pump()
        self.show_page("dashboard")
        self.refresh_states()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        log(f"{APP_NAME} {APP_VERSION} gestartet (admin={tweaklib.is_admin()}, migriert={paths.MIGRATED})")

    # ------------------------------------------------------------ Grundlagen
    def _icon(self):
        ico = resource_path("assets/squallow.ico")

        def apply():
            try:
                self.iconbitmap(str(ico))
            except Exception:  # noqa: BLE001
                pass
        self.after(250, apply)   # CTk setzt sein eigenes Icon verzoegert, daher danach ueberschreiben

    def ui(self, fn):
        """Thread-sicher: fuehrt fn im UI-Thread aus."""
        self._q.put(fn)

    def _pump(self):
        try:
            for _ in range(60):
                fn = self._q.get_nowait()
                try:
                    fn()
                except Exception as exc:  # noqa: BLE001
                    log(f"ui-callback: {exc!r}")
        except queue.Empty:
            pass
        if self.alive:
            self.after(30, self._pump)

    def bg(self, work, done=None):
        def runner():
            try:
                res = work()
            except Exception as exc:  # noqa: BLE001
                log(f"bg: {exc!r}")
                res = exc
            if done is not None and self.alive:
                self.ui(lambda: done(res))
        threading.Thread(target=runner, daemon=True).start()

    def set_status(self, text: str):
        try:
            self.status.configure(text=text)
        except Exception:  # noqa: BLE001
            pass

    def ask(self, title, text, ok="OK", cancel="Abbrechen", danger=False):
        return kit.ask(self, title, text, ok, cancel, danger)

    def tell(self, title, text, mono=False):
        kit.tell(self, title, text, mono)

    def ctx(self) -> dict:
        try:
            battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
        except Exception:  # noqa: BLE001
            battery = None
        return {"desktop": battery is None, "admin": tweaklib.is_admin(),
                "fortnite_config": tweaklib.fortnite_ini_path().exists(),
                "fortnite_running": bool(self.monitor.latest.get("fortnite"))}

    # ------------------------------------------------------------ Shell
    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        side = ctk.CTkFrame(self, width=236, corner_radius=0, fg_color=T.SIDEBAR)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(20, 16))
        try:
            bird = ctk.CTkImage(Image.open(resource_path("assets/bird.png")), size=(38, 38))
            ctk.CTkLabel(brand, text="", image=bird).pack(side="left")
        except Exception:  # noqa: BLE001
            pass
        word = ctk.CTkFrame(brand, fg_color="transparent")
        word.pack(side="left", padx=(10, 0))
        row = ctk.CTkFrame(word, fg_color="transparent")
        row.pack(anchor="w")
        kit.label(row, "Squallow", 17, T.TEXT, True).pack(side="left")
        kit.label(row, "Tweaks", 17, T.VIOLET_L, True).pack(side="left")
        kit.label(word, f"v{APP_VERSION}", 10, T.MUTED).pack(anchor="w")
        for key, title, icon, mod, cls, section in PAGES:
            if section:
                kit.label(side, section, 10, T.DIM, True).pack(anchor="w", padx=22, pady=(14, 4))
            item = NavItem(side, title, icon, lambda k=key: self.show_page(k))
            item.pack(fill="x")
            self.nav[key] = item
        foot = ctk.CTkFrame(side, fg_color="transparent")
        foot.pack(side="bottom", fill="x", padx=16, pady=14)
        admin = tweaklib.is_admin()
        chip = kit.badge(foot, "ADMINISTRATOR" if admin else "OHNE ADMIN", T.GREEN if admin else T.AMBER)
        chip.pack(anchor="w")
        if not admin:
            kit.button(foot, "Als Administrator starten", self.relaunch_admin, "ghost", height=32).pack(fill="x", pady=(8, 0))

        main = ctk.CTkFrame(self, fg_color=T.BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(main, fg_color=T.BG, corner_radius=0, height=68)
        top.grid(row=0, column=0, sticky="ew", padx=28, pady=(14, 0))
        top.grid_columnconfigure(0, weight=1)
        self.page_title = kit.label(top, "", 24, T.TEXT, True)
        self.page_title.grid(row=0, column=0, sticky="w")
        self.page_sub = kit.label(top, "", 11, T.MUTED)
        self.page_sub.grid(row=1, column=0, sticky="w")
        self.auto_btn = kit.button(top, "AUTO OPTIMIZE", self.auto_optimize, "primary", icon="bolt_fill", height=44, width=190, icon_color=T.AMBER)
        self.auto_btn.grid(row=0, column=1, rowspan=2, sticky="e")
        self.host = ctk.CTkFrame(main, fg_color=T.BG, corner_radius=0)
        self.host.grid(row=1, column=0, sticky="nsew", padx=28, pady=(10, 0))
        self.host.grid_rowconfigure(0, weight=1)
        self.host.grid_columnconfigure(0, weight=1)
        self.status = kit.label(main, "Bereit.", 10, T.MUTED)
        self.status.grid(row=2, column=0, sticky="w", padx=30, pady=(4, 8))
        glow = __import__("tkinter").Canvas(side, height=2, bg=T.SIDEBAR, highlightthickness=0, bd=0)
        glow.bind("<Configure>", lambda e: fx.draw_gradient(glow, [T.VIOLET, T.CYAN], e.width, 2))
        glow.pack(side="bottom", fill="x")

    def page(self, key):
        if key not in self.pages:
            for k, title, icon, mod, cls, section in PAGES:
                if k == key:
                    klass = getattr(importlib.import_module(mod), cls)
                    pg = klass(self, self.host)
                    pg.ensure_built()
                    pg.frame.grid(row=0, column=0, sticky="nsew")
                    pg.frame.grid_remove()
                    self.pages[key] = pg
        return self.pages[key]

    def current_page_obj(self):
        return self.pages.get(self.current) if self.current else None

    def show_page(self, key: str):
        if self.current == key:
            return
        if self.current:
            old = self.pages[self.current]
            old.on_hide()
            old.frame.grid_remove()
            self.nav[self.current].set_active(False)
        pg = self.page(key)
        self.current = key
        title = next(p[1] for p in PAGES if p[0] == key)
        self.page_title.configure(text=title)
        self.page_sub.configure(text=pg.subtitle)
        pg.frame.grid()
        self.nav[key].set_active(True)
        pg.on_show()

    # ------------------------------------------------------------ Tweak-Zustaende
    def toggle_tweaks(self):
        return [t for t in self.catalog if t.kind in tweaklib.TOGGLE_KINDS]

    def on_states(self, cb):
        self._state_cbs.append(cb)

    def refresh_states(self, done=None):
        def work():
            return {t.id: self.engine.status(t) for t in self.toggle_tweaks()}

        def finish(res):
            if isinstance(res, dict):
                self.states = res
            for cb in list(self._state_cbs):
                try:
                    cb()
                except Exception as exc:  # noqa: BLE001
                    log(f"state-cb: {exc!r}")
            if done:
                done()
        self.bg(work, finish)

    def is_active(self, tid: str) -> bool:
        return self.states.get(tid, ("", ""))[0] == tweaklib.STATUS_ACTIVE

    # ------------------------------------------------------------ Plaene ausfuehren
    @staticmethod
    def order_plan(plan):
        def key(item):
            t, on = item
            if on:
                return (1, 0 if t.kind == "power" else 1)
            return (0, {"powersetting": 0, "power": 2}.get(t.kind, 1))
        return sorted(plan, key=key)

    def _apply_one(self, t, on: bool):
        if on:
            r = self.engine.apply(t)
            fb = FALLBACK.get(t.id)
            if not r.ok and fb:
                alt = self.by_id[fb]
                r2 = self.engine.apply(alt)
                if r2.ok:
                    return alt, tweaklib.Result(True, f"{alt.name} (Ersatz: gewünschter Plan nicht verfügbar)", True)
            return t, r
        if not self.engine.has_backup(t.id):
            return t, tweaklib.Result(False, "Kein Backup: SquallowTweaks hat das nicht angewendet.")
        return t, self.engine.undo(t)

    def run_plan(self, plan, title="Tweaks anwenden", restart=False, pre=None, post=None, notes=None):
        """plan: [(Tweak, an?)]. pre/post: optionale Zusatzschritte (Name, Funktion->Text) im Hintergrund."""
        if self._busy:
            self.tell(APP_NAME, "Es läuft bereits eine Aktion.")
            return
        plan = self.order_plan(plan)
        self._busy = True
        dlg = kit.ProgressDialog(self, title)
        for n in notes or []:
            dlg.add("• " + n)
        steps = list(pre or []) + [("tweak", p) for p in plan] + list(post or [])
        total = max(1, len(steps))
        results = []

        def work():
            for i, st in enumerate(steps):
                if st[0] == "tweak":
                    t, on = st[1]
                    self.ui(lambda i=i, t=t, on=on: dlg.update_progress(i / total, f"{'Aktiviere' if on else 'Setze zurück'}: {t.name}"))
                    t2, r = self._apply_one(t, on)
                    results.append((t2, on, r))
                    self.ui(lambda t2=t2, r=r: dlg.add(("✔ " if r.ok else "✖ ") + t2.name + ("" if r.ok else f": {r.message}")))
                else:
                    name, fn = st
                    self.ui(lambda i=i, name=name: dlg.update_progress(i / total, name))
                    try:
                        msg = fn()
                    except Exception as exc:  # noqa: BLE001
                        msg = f"Fehler: {exc}"
                    self.ui(lambda name=name, msg=msg: dlg.add(f"• {name}: {msg}"))
            return results

        def done(_res):
            self._busy = False
            ok = [x for x in results if x[2].ok]
            bad = [x for x in results if not x[2].ok]
            needs = any((t.restart and t.restart != "Nein") or t.kind in ("power", "nic") for t, on, r in ok)
            head = f"Fertig: {len(ok)} erfolgreich" + (f", {len(bad)} fehlgeschlagen" if bad else "")
            self.set_status(head)
            dlg.finish(head, restart_offer=needs and not restart, on_restart=self.restart_countdown)
            self.pending.clear()
            self.refresh_states()
            if restart and not bad:
                dlg.destroy()
                self.restart_countdown()
        self.bg(work, done)

    # ------------------------------------------------------------ Auto Optimize
    def auto_optimize(self):
        if self._busy:
            return
        profile = self.settings.get("profile")
        names = {"safe": "SAFE (nur Basis)", "competitive": "COMPETITIVE (empfohlen)", "maxfps": "MAX FPS (mit Zusatz-Tweaks)"}
        c = self.ctx()
        notes = []
        if c["fortnite_running"]:
            notes.append("Fortnite läuft: Config-Tweaks werden übersprungen (Spiel beenden und erneut starten).")
        if not c["admin"]:
            notes.append("Ohne Administratorrechte werden Admin-Tweaks übersprungen.")
        text = (f"Profil: {names.get(profile, profile)}\n\n"
                "SquallowTweaks erkennt dein System, wählt die passenden Tweaks, sichert jeden Originalwert, wendet sie an, "
                "prüft jede Änderung per Rücklesen und räumt danach Temp-Dateien auf.\n\n" + "\n".join(notes))
        if not self.ask("Auto Optimize starten?", text.strip(), "Los geht's", "Abbrechen"):
            return

        pre = []
        if self.settings.get("restore_point") and c["admin"]:
            def rp():
                import restorepoint
                ok, msg = restorepoint.create()
                return msg
            pre.append(("Wiederherstellungspunkt (kann einige Sekunden dauern)", rp))

        def select_and_run():
            chosen, skipped = tweaklib.select_for_profile(self.catalog, self.engine, c, profile)
            plan = [(t, True) for t in chosen]
            post = [("Temp-Dateien bereinigen", self._quiet_clean), ("DNS-Cache leeren", self._flush_dns)]
            notes = [f"Übersprungen: {t.name}: {why}" for t, why in skipped]
            if not plan:
                notes.append("Keine neuen Tweaks nötig: alles Passende ist bereits aktiv.")
            self.ui(lambda: self.run_plan(plan, "Auto Optimize", False, pre, post, notes))
        self.bg(select_and_run)

    def _quiet_clean(self) -> str:
        import cleaner
        freed = 0
        for p in cleaner.targets().values():
            f, _ = cleaner.clean_dir(p)
            freed += f
        return f"{cleaner.fmt_size(freed)} freigegeben"

    def _flush_dns(self) -> str:
        import netlab
        ok, msg = netlab.flush_dns()
        return "geleert" if ok else msg[:80]

    # ------------------------------------------------------------ Neustart / Admin
    def restart_countdown(self):
        import subprocess
        try:
            subprocess.run(["shutdown", "/r", "/t", "20", "/c", "SquallowTweaks: Neustart nach Optimierung"], check=True,
                           capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception as exc:  # noqa: BLE001
            self.tell(APP_NAME, f"Neustart konnte nicht geplant werden:\n{exc}")
            return
        win = ctk.CTkToplevel(self)
        win.title("Neustart")
        win.configure(fg_color=T.BG)
        box = kit.card(win, corner_radius=16)
        box.pack(padx=14, pady=14)
        lbl = kit.label(box, "Neustart in 20 s", 24, T.CYAN, True, anchor="center")
        lbl.pack(padx=40, pady=(24, 6))
        kit.label(box, "Speichere offene Arbeit. Du kannst abbrechen.", 12, T.MUTED, anchor="center").pack(padx=30)

        def cancel():
            subprocess.run(["shutdown", "/a"], capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            win.destroy()
            self.set_status("Neustart abgebrochen")
        kit.button(box, "Neustart abbrechen", cancel, "primary", width=200).pack(pady=(16, 22))

        def tick(n=19):
            if n < 0 or not self.alive:
                return
            try:
                lbl.configure(text=f"Neustart in {n} s")
                win.after(1000, lambda: tick(n - 1))
            except Exception:  # noqa: BLE001
                pass
        win.after(1000, tick)

    def relaunch_admin(self):
        if not IS_WINDOWS:
            return
        exe = sys.executable
        params = "" if getattr(sys, "frozen", False) else f'"{Path(__file__).resolve()}"'
        try:
            rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
            if rc > 32:
                self.on_close()
        except Exception as exc:  # noqa: BLE001
            self.tell(APP_NAME, f"Neustart als Administrator nicht möglich: {exc}")

    def on_close(self):
        self.alive = False
        try:
            self.monitor.stop()
        except Exception:  # noqa: BLE001
            pass
        for pg in self.pages.values():
            try:
                pg.on_hide()
            except Exception:  # noqa: BLE001
                pass
        self.destroy()


def main() -> int:
    if not IS_WINDOWS:
        print("SquallowTweaks ist für Windows 10/11 gedacht.")
        return 1
    App().mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
