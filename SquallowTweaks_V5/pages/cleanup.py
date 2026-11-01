"""Bereinigung: Temp-Dateien, Papierkorb, DNS, SSD-TRIM und Autostart-Programme."""
from __future__ import annotations

import customtkinter as ctk

import cleaner
import kit
import netlab
import theme as T
import tweaklib
from pages.base import Page


class CleanupPage(Page):
    subtitle = "Platz schaffen und Hintergrundprogramme beim Start abschalten"

    def build(self):
        sc = kit.Scroll(self.frame)
        sc.pack(fill="both", expand=True)
        root = sc.inner
        root.grid_columnconfigure((0, 1), weight=1, uniform="c")
        left = kit.card(root, corner_radius=16)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))
        kit.label(left, "SPEICHER", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        self.size_rows: dict[str, ctk.CTkLabel] = {}
        for name in list(cleaner.targets()) + ["Papierkorb"]:
            r = ctk.CTkFrame(left, fg_color=T.CARD2, corner_radius=10)
            r.pack(fill="x", padx=16, pady=3)
            kit.label(r, name, 12, T.TEXT, True).pack(side="left", padx=14, pady=10)
            lbl = kit.label(r, "…", 12, T.TEXT2)
            lbl.pack(side="right", padx=14)
            self.size_rows[name] = lbl
        self.total = kit.label(left, "", 12, T.CYAN, True)
        self.total.pack(anchor="w", padx=20, pady=(8, 0))
        self.result = kit.label(left, "", 12, T.GREEN, wrap=420)
        self.result.pack(anchor="w", padx=20, pady=(2, 0))
        self.clean_btn = kit.button(left, "ALLES BEREINIGEN", self.clean_all, "primary", icon="cleanup", height=44)
        self.clean_btn.pack(fill="x", padx=20, pady=(12, 18))
        right = kit.card(root, corner_radius=16)
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 10))
        kit.label(right, "WARTUNG", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        for text, desc, cmd in (("DNS-Cache leeren", "Hilft bei Namensauflösungs-Problemen. Senkt den Ingame-Ping nicht.", self.dns),
                                ("SSD optimieren (TRIM)", "Hält die SSD-Schreibleistung stabil. Braucht Adminrechte.", self.trim)):
            kit.button(right, text, cmd, "ghost", height=40).pack(fill="x", padx=20, pady=(8, 0))
            kit.label(right, desc, 11, T.MUTED, wrap=420).pack(anchor="w", padx=22, pady=(2, 0))
        self.maint = kit.label(right, "", 12, T.TEXT2, wrap=420)
        self.maint.pack(anchor="w", padx=20, pady=(12, 18))
        self.auto_card = kit.card(root, corner_radius=16)
        self.auto_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))

    def on_show(self):
        for lbl in self.size_rows.values():
            lbl.configure(text="…")

        def work():
            out = {n: cleaner.dir_size(p) for n, p in cleaner.targets().items()}
            out["Papierkorb"] = cleaner.recycle_size()
            return out

        def done(res):
            if not isinstance(res, dict):
                return
            for n, size in res.items():
                self.size_rows[n].configure(text=cleaner.fmt_size(size))
            self.total.configure(text=f"Gesamt: {cleaner.fmt_size(sum(res.values()))}")
        self.app.bg(work, done)
        self.render_autostart()

    def clean_all(self):
        if not self.app.ask("Alles bereinigen?", "Benutzer-Temp, Windows-Temp und Papierkorb werden geleert. Gesperrte Dateien werden übersprungen. Das lässt sich nicht rückgängig machen.", "Bereinigen"):
            return
        self.clean_btn.configure(state="disabled")
        self.result.configure(text="Bereinige …", text_color=T.CYAN)

        def work():
            freed = failed = 0
            for p in cleaner.targets().values():
                f, x = cleaner.clean_dir(p)
                freed += f
                failed += x
            cleaner.empty_recycle()
            return freed, failed

        def done(res):
            self.clean_btn.configure(state="normal")
            if isinstance(res, tuple):
                self.result.configure(text=f"{cleaner.fmt_size(res[0])} freigegeben ({res[1]} gesperrte Einträge übersprungen).", text_color=T.GREEN)
            self.on_show()
        self.app.bg(work, done)

    def dns(self):
        self.app.bg(netlab.flush_dns, lambda r: self.maint.configure(text="DNS-Cache geleert." if r[0] else f"Fehler: {r[1][:100]}", text_color=T.GREEN if r[0] else T.RED))

    def trim(self):
        self.maint.configure(text="TRIM läuft …", text_color=T.CYAN)
        self.app.bg(cleaner.trim_system_drive, lambda r: self.maint.configure(text=r[1], text_color=T.GREEN if r[0] else T.AMBER))

    # ------------------------------------------------------------ Autostart
    def render_autostart(self):
        for w in self.auto_card.winfo_children():
            w.destroy()
        kit.label(self.auto_card, "AUTOSTART (BENUTZER)", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 2))
        kit.label(self.auto_card, "Schalter aus = startet nicht mehr mit Windows. Es wird nichts gelöscht; jederzeit wieder einschaltbar.", 11, T.MUTED).pack(anchor="w", padx=20, pady=(0, 8))
        entries = tweaklib.list_startup(self.app.engine.backend)
        if not entries:
            kit.label(self.auto_card, "Keine Benutzer-Autostart-Einträge gefunden.", 12, T.TEXT2).pack(anchor="w", padx=20, pady=(0, 16))
            return
        for e in entries:
            r = ctk.CTkFrame(self.auto_card, fg_color=T.CARD2, corner_radius=10)
            r.pack(fill="x", padx=16, pady=3)
            var = ctk.BooleanVar(value=e.enabled)
            sw = ctk.CTkSwitch(r, text="", variable=var, width=46, switch_width=42, switch_height=22, progress_color=T.CYAN,
                               button_color="#FFFFFF", fg_color="#2A2A40", command=lambda n=e.name, v=var: self.toggle(n, bool(v.get())))
            sw.pack(side="right", padx=14, pady=8)
            kit.label(r, e.name, 12, T.TEXT, True).pack(side="left", padx=14)
            kit.label(r, e.command[:90], 10, T.MUTED).pack(side="left")
        ctk.CTkFrame(self.auto_card, fg_color="transparent", height=10).pack()

    def toggle(self, name: str, enable: bool):
        res = tweaklib.set_startup_enabled(self.app.engine.backend, name, enable)
        self.app.set_status(("✔ " if res.ok else "✖ ") + res.message[:110])
        if not res.ok:
            self.app.tell("Autostart", res.message)
            self.render_autostart()
