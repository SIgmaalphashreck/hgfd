"""Fortnite: Ein-Klick-Optimierung der Config, Status der Fortnite-Tweaks, automatische Prioritaet."""
from __future__ import annotations

import time

import customtkinter as ctk
import psutil

import kit
import texts
import theme as T
import tweaklib
from monitor import FORTNITE_EXE
from pages.base import Page


class FortnitePage(Page):
    subtitle = "Config-Optimierung mit Backup, Rücklese-Prüfung und Undo"

    def build(self):
        sc = kit.Scroll(self.frame)
        sc.pack(fill="both", expand=True)
        root = sc.inner
        root.grid_columnconfigure((0, 1), weight=1, uniform="f")
        # Kopf
        head = kit.card(root, corner_radius=16)
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        kit.label(head, "Fortnite", 26, T.TEXT, True).pack(anchor="w", padx=22, pady=(18, 0))
        row = ctk.CTkFrame(head, fg_color="transparent")
        row.pack(anchor="w", padx=22, pady=(6, 0))
        self.b_cfg = kit.badge(row, "CONFIG …", T.MUTED)
        self.b_cfg.pack(side="left")
        self.b_run = kit.badge(row, "PROZESS …", T.MUTED)
        self.b_run.pack(side="left", padx=6)
        self.info = kit.label(head, "", 12, T.TEXT2, wrap=900)
        self.info.pack(anchor="w", padx=22, pady=(8, 0))
        btns = ctk.CTkFrame(head, fg_color="transparent")
        btns.pack(anchor="w", padx=22, pady=(14, 20))
        kit.button(btns, "FORTNITE OPTIMIEREN", self.optimize, "primary", icon="bolt_fill", height=46, width=230, icon_color=T.AMBER).pack(side="left")
        kit.button(btns, "Zurücksetzen", self.reset, "ghost", height=46, width=140).pack(side="left", padx=10)
        kit.button(btns, "Wirkung messen", lambda: self.app.show_page("benchmark"), "ghost", icon="bench", height=46, width=170).pack(side="left")
        # Tweak-Status
        left = kit.card(root, corner_radius=16)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 5))
        kit.label(left, "FORTNITE-TWEAKS", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        self.rows: dict[str, tuple] = {}
        for t in self.app.catalog:
            if t.id.startswith("fn_"):
                r = ctk.CTkFrame(left, fg_color="transparent")
                r.pack(fill="x", padx=20, pady=4)
                dot = ctk.CTkLabel(r, text="●", width=18, text_color=T.MUTED, font=kit.font(12))
                dot.pack(side="left")
                kit.label(r, t.name.split(":")[-1].strip(), 12, T.TEXT, True).pack(side="left")
                st = kit.label(r, "", 11, T.MUTED)
                st.pack(side="right")
                self.rows[t.id] = (dot, st)
        kit.button(left, "Einzelne Schalter im Tweaks-Tab", lambda: self.app.show_page("tweaks"), "text", height=32).pack(anchor="w", padx=14, pady=(8, 14))
        # Live + Auto-Prioritaet
        right = kit.card(root, corner_radius=16)
        right.grid(row=1, column=1, sticky="nsew", padx=(5, 0))
        kit.label(right, "LIVE & AUTOMATIK", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        self.live = kit.label(right, "Fortnite läuft nicht.", 12, T.TEXT2, wrap=420)
        self.live.pack(anchor="w", padx=20)
        sw = ctk.CTkFrame(right, fg_color="transparent")
        sw.pack(fill="x", padx=20, pady=(14, 4))
        self.auto_var = ctk.BooleanVar(value=bool(self.app.settings.get("auto_priority")))
        ctk.CTkSwitch(sw, text="  Priorität automatisch auf HOCH", variable=self.auto_var, progress_color=T.CYAN, font=kit.font(12),
                      text_color=T.TEXT, command=lambda: self.app.settings.set("auto_priority", bool(self.auto_var.get()))).pack(anchor="w")
        kit.label(right, "Setzt Fortnite beim Start auf HOHE Priorität (nie Echtzeit). Wirkung: klein, aber kostenlos.", 11, T.MUTED, wrap=420).pack(anchor="w", padx=20, pady=(4, 10))
        kit.label(right, "GUT ZU WISSEN", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(6, 4))
        kit.label(right, "• NVIDIA Reflex im Spiel auf „Ein + Boost“ stellen (senkt Latenz, geht nur im Spiel).\n"
                         "• Eingabelatenz lässt sich per Software nicht messen. FPS und Frametimes schon: Tab Benchmark.\n"
                         "• Fortnite kann Werte beim Speichern der Spiel-Einstellungen überschreiben. Dann einfach erneut optimieren.",
                  11, T.TEXT2, wrap=420).pack(anchor="w", padx=20, pady=(0, 18))
        self.app.on_states(self.sync)

    def on_show(self):
        self.sync()
        self.tick()
        self.every(1500, self.tick)

    def tick(self):
        d = self.app.monitor.latest.get("fortnite")
        cfg = tweaklib.fortnite_ini_path().exists()
        self.b_cfg.configure(text=" CONFIG GEFUNDEN " if cfg else " CONFIG FEHLT ", text_color=T.GREEN if cfg else T.AMBER)
        self.b_run.configure(text=" LÄUFT " if d else " NICHT GESTARTET ", text_color=T.CYAN if d else T.MUTED)
        self.info.configure(text="Bereit. Zum Anwenden muss Fortnite geschlossen sein." if cfg else
                            "Starte Fortnite einmal bis ins Hauptmenü und schließe es wieder, damit die Config erzeugt wird.")
        if d:
            self.live.configure(text=f"PID {d['pid']} · CPU {d['cpu']:.0f}% · RAM {d['ram_mb']:.0f} MB · Priorität {'HOCH' if d['high'] else 'normal'}")
        else:
            self.live.configure(text="Fortnite läuft nicht.")

    def sync(self):
        if not self.built:
            return
        for tid, (dot, st) in self.rows.items():
            state = self.app.states.get(tid, ("", ""))[0]
            if state == tweaklib.STATUS_ACTIVE:
                dot.configure(text_color=T.GREEN)
                st.configure(text="Aktiv", text_color=T.GREEN)
            elif state == tweaklib.STATUS_UNKNOWN:
                dot.configure(text_color=T.DIM)
                st.configure(text="Config fehlt", text_color=T.DIM)
            else:
                dot.configure(text_color=T.MUTED)
                st.configure(text="Aus" if state else "…", text_color=T.MUTED)

    # ------------------------------------------------------------ Aktionen
    def _fn_tweaks(self, only_recommended=True):
        return [t for t in self.app.catalog if t.id.startswith("fn_") and (t.recommended or not only_recommended)]

    def _close_fortnite(self) -> bool:
        for p in psutil.process_iter(["name"]):
            try:
                if (p.info.get("name") or "").lower() == FORTNITE_EXE.lower():
                    p.terminate()
            except psutil.Error:
                pass
        for _ in range(40):
            time.sleep(0.25)
            if not any((p.info.get("name") or "").lower() == FORTNITE_EXE.lower() for p in psutil.process_iter(["name"])):
                return True
        return False

    def optimize(self):
        ctx = self.app.ctx()
        if not ctx["fortnite_config"]:
            self.app.tell("Config nicht gefunden", "Starte Fortnite einmal bis ins Hauptmenü und schließe es wieder. Danach erzeugt Fortnite die Config, und SquallowTweaks kann sie optimieren.")
            return
        plan = [(t, True) for t in self._fn_tweaks() if not self.app.is_active(t.id)]
        if not plan and not ctx["fortnite_running"]:
            self.app.tell("Bereits optimiert", "Alle empfohlenen Fortnite-Tweaks sind aktiv.")
            return
        if ctx["fortnite_running"]:
            if not self.app.ask("Fortnite beenden?", "Fortnite muss geschlossen sein, sonst überschreibt das Spiel die Einstellungen beim Beenden. Jetzt beenden und optimieren?", "Beenden & optimieren"):
                return
            self.app.set_status("Beende Fortnite …")
            self.app.bg(self._close_fortnite, lambda ok: self.app.run_plan(plan, "Fortnite optimieren") if ok else
                        self.app.tell("Fortnite läuft noch", "Fortnite konnte nicht beendet werden. Schließe es manuell und versuche es erneut."))
        else:
            self.app.run_plan(plan, "Fortnite optimieren")

    def reset(self):
        plan = [(t, False) for t in self._fn_tweaks(False) if self.app.engine.has_backup(t.id)]
        if not plan:
            self.app.tell("Nichts zurückzusetzen", "Für Fortnite gibt es keine gesicherten Änderungen von SquallowTweaks.")
            return
        if self.app.ctx()["fortnite_running"]:
            self.app.tell("Fortnite läuft", "Beende Fortnite zuerst, dann kann die Config zurückgesetzt werden.")
            return
        if self.app.ask("Fortnite-Tweaks zurücksetzen?", "Alle von SquallowTweaks geänderten Fortnite-Werte werden auf den gesicherten Originalzustand gesetzt.", "Zurücksetzen"):
            self.app.run_plan(plan, "Fortnite zurücksetzen")
