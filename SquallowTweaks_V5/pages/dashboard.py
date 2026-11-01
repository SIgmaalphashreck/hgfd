"""Dashboard: Systemstatus, Live-Ringe, Verlauf, Checks."""
from __future__ import annotations

import re
import shutil

import customtkinter as ctk

import kit
import netlab
import theme as T
import tweaklib
from pages.base import Page
from ui_widgets import RingGauge, Sparkline


def _run(args, timeout=6) -> str:
    code, out = tweaklib.default_runner(args, timeout)
    return out if code == 0 else ""


def compute_checks(ctx: dict) -> list[tuple[str, str, str]]:
    """Echte Pruefungen; level: ok | warn | info. Laeuft im Hintergrund-Thread."""
    rows: list[tuple[str, str, str]] = []
    mem = tweaklib._ps("Get-CimInstance Win32_PhysicalMemory | ForEach-Object { '{0};{1}' -f $_.Speed,$_.ConfiguredClockSpeed }")
    pairs = []
    for line in mem.splitlines():
        a = line.strip().split(";")
        if len(a) == 2 and a[0].isdigit() and a[1].isdigit():
            pairs.append((int(a[0]), int(a[1])))
    if pairs:
        nom, cur = max(p[0] for p in pairs), min(p[1] for p in pairs)
        if cur >= nom * 0.98:
            rows.append(("RAM-Takt", f"{cur} MT/s (Nennwert {nom})", "ok"))
        else:
            rows.append(("RAM-Takt", f"{cur} MT/s, Nennwert {nom}: DOCP/XMP im BIOS aktivieren", "warn"))
    else:
        rows.append(("RAM-Takt", "nicht lesbar", "info"))
    lan = [a for a in netlab.psutil_adapters() if a["kind"] == "LAN" and a["is_up"]]
    if lan:
        sp = lan[0]["speed_mbit"]
        rows.append(("Netzwerk", f"LAN {sp} Mbit/s" if sp else "LAN verbunden", "ok" if (sp or 0) >= 1000 else "warn"))
    else:
        wifi = [a for a in netlab.psutil_adapters() if a["kind"] == "WLAN" and a["is_up"]]
        rows.append(("Netzwerk", "nur WLAN: für stabilen Ping LAN-Kabel nutzen" if wifi else "keine Verbindung erkannt", "warn"))
    plan = _run(["powercfg", "/getactivescheme"])
    m = re.search(r"\(([^)]+)\)", plan)
    name = m.group(1) if m else "unbekannt"
    good = any(k in name.lower() for k in ("hoch", "high", "ultimat", "höchst"))
    rows.append(("Energieplan", name, "ok" if good else "warn"))
    exe = shutil.which("nvidia-smi")
    drv = _run([exe, "--query-gpu=driver_version", "--format=csv,noheader"]) if exe else ""
    rows.append(("GPU-Treiber", f"NVIDIA {drv.splitlines()[0]}" if drv else "nvidia-smi nicht gefunden", "info"))
    rows.append(("GPU-Planung (HAGS)", tweaklib.status_hags().split(": ")[-1], "info"))
    rows.append(("Fortnite-Config", "gefunden" if ctx["fortnite_config"] else "nicht gefunden (Fortnite einmal starten)",
                 "ok" if ctx["fortnite_config"] else "warn"))
    rows.append(("Administrator", "ja" if ctx["admin"] else "nein: Admin-Tweaks gesperrt", "ok" if ctx["admin"] else "warn"))
    return rows


class DashboardPage(Page):
    subtitle = "Dein System auf einen Blick"

    def build(self):
        self.sc = kit.Scroll(self.frame)
        self.sc.pack(fill="both", expand=True)
        root = self.sc.inner
        for c in range(4):
            root.grid_columnconfigure(c, weight=1, uniform="d")
        # --- Hero
        hero = kit.card(root, corner_radius=16)
        hero.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=(0, 8), pady=(0, 8))
        kit.label(hero, "DEIN SYSTEM", 10, T.DIM, True).pack(anchor="w", padx=22, pady=(18, 0))
        self.sys_lbl = kit.label(hero, "Hardware wird erkannt …", 13, T.TEXT2, wrap=640)
        self.sys_lbl.pack(anchor="w", padx=22, pady=(2, 10))
        self.opt_lbl = kit.label(hero, "–", 26, T.TEXT, True)
        self.opt_lbl.pack(anchor="w", padx=22)
        self.opt_bar = ctk.CTkProgressBar(hero, height=8, corner_radius=4, progress_color=T.VIOLET, fg_color=T.CARD2)
        self.opt_bar.set(0)
        self.opt_bar.pack(fill="x", padx=22, pady=(10, 4))
        self.opt_hint = kit.label(hero, "", 11, T.MUTED, wrap=640)
        self.opt_hint.pack(anchor="w", padx=22)
        row = ctk.CTkFrame(hero, fg_color="transparent")
        row.pack(anchor="w", padx=22, pady=(14, 20))
        kit.button(row, "AUTO OPTIMIZE", self.app.auto_optimize, "primary", icon="bolt_fill", height=44, width=190, icon_color=T.AMBER).pack(side="left")
        kit.button(row, "Wirkung messen", lambda: self.app.show_page("benchmark"), "ghost", icon="bench", height=44, width=170).pack(side="left", padx=10)
        # --- Fortnite
        fn = kit.card(root, corner_radius=16)
        fn.grid(row=0, column=3, sticky="nsew", pady=(0, 8))
        kit.label(fn, "FORTNITE", 10, T.DIM, True).pack(anchor="w", padx=18, pady=(18, 4))
        self.fn_badge = kit.badge(fn, "SUCHE …", T.MUTED)
        self.fn_badge.pack(anchor="w", padx=18)
        self.fn_lbl = kit.label(fn, "", 12, T.TEXT2, wrap=250)
        self.fn_lbl.pack(anchor="w", padx=18, pady=(10, 0))
        kit.button(fn, "Fortnite-Optimierung", lambda: self.app.show_page("fortnite"), "ghost", icon="game", height=36).pack(fill="x", padx=18, pady=(12, 18), side="bottom")
        # --- Ringe
        self.rings = {}
        spec = [("cpu", "CPU"), ("gpu", "GPU"), ("ram", "RAM"), ("vram", "VRAM")]
        for i, (key, title) in enumerate(spec):
            c = kit.card(root, corner_radius=16)
            c.grid(row=1, column=i, sticky="nsew", padx=(0 if i == 0 else 4, 4 if i < 3 else 0), pady=(0, 8))
            ring = RingGauge(c, size=124, thickness=11, color=T.VIOLET, color2=T.CYAN, warn=T.RED, bg=T.CARD, track="#1C1C2E",
                             text_color=T.TEXT, sub_color=T.MUTED)
            ring.pack(pady=(16, 4))
            kit.label(c, title, 12, T.TEXT, True, anchor="center").pack()
            sub = kit.label(c, "–", 10, T.MUTED, anchor="center")
            sub.pack(pady=(0, 14))
            self.rings[key] = (ring, sub)
        # --- Verlauf
        left = kit.card(root, corner_radius=16)
        left.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 4), pady=(0, 8))
        self.sp_cpu = Sparkline(left, height=76, color=T.VIOLET_L, bg=T.CARD, grid="#181828", label="CPU")
        self.sp_cpu.pack(fill="x", padx=14, pady=(14, 4))
        self.sp_gpu = Sparkline(left, height=76, color=T.CYAN, bg=T.CARD, grid="#181828", label="GPU")
        self.sp_gpu.pack(fill="x", padx=14, pady=(4, 14))
        right = kit.card(root, corner_radius=16)
        right.grid(row=2, column=2, columnspan=2, sticky="nsew", padx=(4, 0), pady=(0, 8))
        self.sp_down = Sparkline(right, height=76, color=T.GREEN, bg=T.CARD, grid="#181828", label="Download", unit=" Mbit/s", vmax=None)
        self.sp_down.pack(fill="x", padx=14, pady=(14, 4))
        self.sp_up = Sparkline(right, height=76, color=T.AMBER, bg=T.CARD, grid="#181828", label="Upload", unit=" Mbit/s", vmax=None)
        self.sp_up.pack(fill="x", padx=14, pady=(4, 14))
        # --- Checks
        self.checks_card = kit.card(root, corner_radius=16)
        self.checks_card.grid(row=3, column=0, columnspan=4, sticky="nsew", pady=(0, 16))
        kit.label(self.checks_card, "SYSTEM-CHECKS", 10, T.DIM, True).pack(anchor="w", padx=22, pady=(16, 6))
        self.checks_body = ctk.CTkFrame(self.checks_card, fg_color="transparent")
        self.checks_body.pack(fill="x", padx=22, pady=(0, 14))
        kit.label(self.checks_body, "Prüfe …", 11, T.MUTED).pack(anchor="w")
        self.app.on_states(self.update_opt)
        self._cpu_name = ""
        self._checks_t = 0.0

    # ----------------------------------------------------------------- Daten
    def on_show(self):
        self.update_opt()
        self.tick()
        self.every(1000, self.tick)
        import time
        if time.time() - self._checks_t > 45:
            self._checks_t = time.time()
            ctx = self.app.ctx()
            self.app.bg(lambda: (compute_checks(ctx), tweaklib._ps("(Get-CimInstance Win32_Processor | Select-Object -First 1).Name")),
                        self.show_checks)

    def show_checks(self, res):
        if not isinstance(res, tuple):
            return
        rows, cpu = res
        self._cpu_name = cpu.strip()
        for w in self.checks_body.winfo_children():
            w.destroy()
        colors = {"ok": T.GREEN, "warn": T.AMBER, "info": T.MUTED}
        for name, value, level in rows:
            r = ctk.CTkFrame(self.checks_body, fg_color="transparent")
            r.pack(fill="x", pady=3)
            ctk.CTkLabel(r, text="●", text_color=colors[level], width=18, font=kit.font(12)).pack(side="left")
            kit.label(r, name, 12, T.TEXT, True, width=170).pack(side="left")
            kit.label(r, value, 12, T.TEXT2).pack(side="left")
        self.update_sys_label()

    def update_sys_label(self):
        m = self.app.monitor.latest
        gpu = m.get("gpu", {}).get("name") or self.app.monitor.gpu_name or "GPU unbekannt"
        ram = m.get("ram_total", 0) / 1073741824
        parts = [self._cpu_name or "CPU wird erkannt", gpu, f"{ram:.0f} GB RAM" if ram else ""]
        self.sys_lbl.configure(text="  ·  ".join(p for p in parts if p))

    def update_opt(self):
        if not self.built:
            return
        ctx = self.app.ctx()
        rec = [t for t in self.app.catalog if t.kind in tweaklib.TOGGLE_KINDS and t.recommended]
        avail = [t for t in rec if tweaklib.applicable(t, ctx)[0] and self.app.states.get(t.id, ("", ""))[0] != tweaklib.STATUS_UNKNOWN]
        if not self.app.states:
            self.opt_lbl.configure(text="Prüfe Tweaks …")
            return
        active = sum(1 for t in avail if self.app.is_active(t.id))
        total = max(1, len(avail))
        self.opt_lbl.configure(text=f"{active} von {len(avail)} empfohlenen Tweaks aktiv")
        self.opt_bar.set(active / total)
        if active == len(avail) and avail:
            self.opt_hint.configure(text="Alles Empfohlene ist aktiv. Miss die Wirkung im Benchmark.", text_color=T.GREEN)
        else:
            self.opt_hint.configure(text="AUTO OPTIMIZE aktiviert den Rest automatisch (mit Backup und Undo).", text_color=T.MUTED)

    def tick(self):
        mon = self.app.monitor
        d = mon.latest
        if not d:
            return
        cpu_ring, cpu_sub = self.rings["cpu"]
        cpu_ring.set(d["cpu"] / 100, f"{d['cpu']:.0f}%")
        cpu_sub.configure(text=f"{d['cpu_mhz']:.0f} MHz" if d.get("cpu_mhz") else "Takt N/A")
        g = d.get("gpu", {})
        gr, gs = self.rings["gpu"]
        vr, vs = self.rings["vram"]
        if g.get("available") and g.get("usage") is not None:
            gr.set(g["usage"] / 100, f"{g['usage']:.0f}%")
            gs.configure(text=" · ".join(x for x in (f"{g['temp']:.0f} °C" if g.get("temp") is not None else "",
                                                       f"{g['clock']:.0f} MHz" if g.get("clock") else "") if x) or "–")
            if g.get("mem_total"):
                vr.set(g["mem_used"] / g["mem_total"], f"{g['mem_used'] / g['mem_total'] * 100:.0f}%")
                vs.configure(text=f"{g['mem_used'] / 1024:.1f} / {g['mem_total'] / 1024:.1f} GB")
        else:
            gr.set(None, "N/A")
            gs.configure(text="keine NVIDIA-Telemetrie")
            vr.set(None, "N/A")
            vs.configure(text="–")
        rr, rs = self.rings["ram"]
        rr.set(d["ram"] / 100, f"{d['ram']:.0f}%")
        rs.configure(text=f"{d['ram_used'] / 1073741824:.1f} / {d['ram_total'] / 1073741824:.0f} GB")
        h = mon.hist
        for sp, key in ((self.sp_cpu, "cpu"), (self.sp_gpu, "gpu"), (self.sp_down, "down"), (self.sp_up, "up")):
            sp.data.clear()
            sp.data.extend(h[key])
            sp.redraw()
        fnp = d.get("fortnite")
        cfg = tweaklib.fortnite_ini_path().exists()
        if fnp:
            self.fn_badge.configure(text=" LÄUFT ", text_color=T.GREEN)
            self.fn_lbl.configure(text=f"PID {fnp['pid']} · CPU {fnp['cpu']:.0f}% · {fnp['ram_mb']:.0f} MB\nPriorität: {'HOCH' if fnp['high'] else 'normal'}")
        else:
            self.fn_badge.configure(text=" NICHT GESTARTET " if cfg else " NICHT GEFUNDEN ", text_color=T.MUTED if cfg else T.AMBER)
            self.fn_lbl.configure(text="Config gefunden: bereit zum Optimieren." if cfg else "Starte Fortnite einmal, damit die Config erzeugt wird.")
        self.update_sys_label()
