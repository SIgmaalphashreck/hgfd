"""Einstellungen: Profil, Automatik, Wiederherstellung."""
from __future__ import annotations

import customtkinter as ctk

import kit
import paths
import restorepoint
import theme as T
import tweaklib
from pages.base import Page

PROFILES = {"SAFE": "safe", "COMPETITIVE": "competitive", "MAX FPS": "maxfps"}
PROFILE_TEXT = {"safe": "Nur Basis-Tweaks, minimales Risiko.",
                "competitive": "Alles Empfohlene für dein System (Basis, Energie, Fortnite-Config, LAN).",
                "maxfps": "Competitive plus Effekte aus, Hintergrund-Apps, Telemetrie und MSI-Modus."}


class SettingsPage(Page):
    subtitle = "Profil, Automatik und Wiederherstellung"

    def build(self):
        sc = kit.Scroll(self.frame)
        sc.pack(fill="both", expand=True)
        root = sc.inner
        root.grid_columnconfigure(0, weight=1)
        s = self.app.settings
        c1 = kit.card(root, corner_radius=16)
        c1.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        kit.label(c1, "AUTO OPTIMIZE", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        row = ctk.CTkFrame(c1, fg_color="transparent")
        row.pack(fill="x", padx=20)
        kit.label(row, "Profil", 12, T.TEXT, True).pack(side="left")
        self.menu = ctk.CTkOptionMenu(row, values=list(PROFILES), width=170, height=34, fg_color=T.CARD2, button_color=T.VIOLET_D,
                                      button_hover_color=T.VIOLET, dropdown_fg_color=T.CARD2, command=self.set_profile)
        self.menu.set(next((k for k, v in PROFILES.items() if v == s.get("profile")), "COMPETITIVE"))
        self.menu.pack(side="left", padx=12)
        self.profile_txt = kit.label(c1, PROFILE_TEXT[s.get("profile")], 11, T.MUTED, wrap=900)
        self.profile_txt.pack(anchor="w", padx=20, pady=(6, 10))
        self.rp = ctk.BooleanVar(value=bool(s.get("restore_point")))
        ctk.CTkSwitch(c1, text="  Wiederherstellungspunkt vor Auto Optimize versuchen (mit Admin)", variable=self.rp, progress_color=T.CYAN,
                      font=kit.font(12), text_color=T.TEXT, command=lambda: s.set("restore_point", bool(self.rp.get()))).pack(anchor="w", padx=20, pady=(0, 16))
        c2 = kit.card(root, corner_radius=16)
        c2.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        kit.label(c2, "SICHERHEIT & WIEDERHERSTELLUNG", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        self.backups = kit.label(c2, "", 12, T.TEXT2, wrap=900)
        self.backups.pack(anchor="w", padx=20)
        r = ctk.CTkFrame(c2, fg_color="transparent")
        r.pack(anchor="w", padx=20, pady=(12, 6))
        kit.button(r, "Wiederherstellungspunkt jetzt erstellen", self.make_rp, "ghost", height=40, width=320).pack(side="left")
        kit.button(r, "Alle Tweaks zurücksetzen", self.undo_all, "danger", height=40, width=220).pack(side="left", padx=10)
        self.msg = kit.label(c2, "", 12, T.TEXT2, wrap=900)
        self.msg.pack(anchor="w", padx=20, pady=(4, 16))
        c3 = kit.card(root, corner_radius=16)
        c3.grid(row=2, column=0, sticky="ew", pady=(0, 16))
        kit.label(c3, "ÜBER", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        kit.label(c3, f"SquallowTweaks {paths.APP_VERSION}\nDaten: {paths.DATA}\nLog: {paths.LOG_FILE.name}\n\n"
                      "Nicht enthalten (bewusst): Defender/Firewall/Windows Update deaktivieren, Anti-Cheat-Eingriffe, bcdedit/HPET, TCP-Registry-Hacks, Treiberinstallation.",
                  11, T.MUTED, wrap=900).pack(anchor="w", padx=20, pady=(0, 16))

    def on_show(self):
        n = sum(1 for t in self.app.catalog if self.app.engine.has_backup(t.id))
        self.backups.configure(text=f"{n} Tweak(s) mit gesichertem Originalzustand. Jeder lässt sich im Tab Tweaks per Schalter zurücksetzen.")

    def set_profile(self, name):
        key = PROFILES[name]
        self.app.settings.set("profile", key)
        self.profile_txt.configure(text=PROFILE_TEXT[key])

    def make_rp(self):
        self.msg.configure(text="Erstelle Wiederherstellungspunkt (bis ca. 60 s) …", text_color=T.CYAN)
        self.app.bg(restorepoint.create, lambda r: self.msg.configure(text=r[1] if isinstance(r, tuple) else str(r), text_color=T.GREEN if isinstance(r, tuple) and r[0] else T.AMBER))

    def undo_all(self):
        plan = [(t, False) for t in self.app.catalog if t.kind in tweaklib.TOGGLE_KINDS and self.app.engine.has_backup(t.id)]
        if not plan:
            self.app.tell("Nichts zurückzusetzen", "Es gibt keine gesicherten Änderungen.")
            return
        if self.app.ask("Alle Tweaks zurücksetzen?", f"{len(plan)} Tweak(s) werden auf den gesicherten Originalzustand gesetzt.", "Zurücksetzen", danger=True):
            self.app.run_plan(plan, "Alles zurücksetzen")
