"""Benchmark: FPS/Frametime vor und nach den Tweaks messen (PresentMon) und vergleichen."""
from __future__ import annotations

import time

import customtkinter as ctk

import bench
import fnmon
import kit
import theme as T
from paths import CAPTURE_CSV
from pages.base import Page


class BenchmarkPage(Page):
    subtitle = "Messen statt glauben: Vorher/Nachher-Vergleich mit echten Frametimes"

    def build(self):
        sc = kit.Scroll(self.frame)
        sc.pack(fill="both", expand=True)
        root = sc.inner
        root.grid_columnconfigure(0, weight=1)
        intro = kit.card(root, corner_radius=16)
        intro.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        kit.label(intro, "So geht's", 14, T.TEXT, True).pack(anchor="w", padx=20, pady=(16, 4))
        kit.label(intro, "1. Fortnite starten und in ein Match oder den Kreativ-Modus gehen.   2. Hier „Messung starten“ drücken (Name: Vorher).   "
                         "3. Tweaks anwenden.   4. Erneut messen (Name: Nachher) und vergleichen.", 12, T.TEXT2, wrap=980).pack(anchor="w", padx=20, pady=(0, 16))
        self.pm_warn = kit.label(intro, "", 11, T.AMBER, wrap=980)
        self.pm_warn.pack(anchor="w", padx=20, pady=(0, 14))
        ctrl = kit.card(root, corner_radius=16)
        ctrl.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        row = ctk.CTkFrame(ctrl, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(18, 8))
        self.name = ctk.CTkEntry(row, placeholder_text="Name der Messung (z. B. Vorher)", width=300, height=40, fg_color=T.CARD2,
                                 border_color=T.BORDER, text_color=T.TEXT, corner_radius=10)
        self.name.pack(side="left")
        self.dur = ctk.CTkSegmentedButton(row, values=["30 s", "60 s", "120 s"], height=40, fg_color=T.CARD2, selected_color=T.VIOLET,
                                          selected_hover_color=T.VIOLET_L, unselected_color=T.CARD2, unselected_hover_color=T.CARD_HOVER,
                                          font=kit.font(12, True))
        self.dur.set("60 s")
        self.dur.pack(side="left", padx=10)
        self.start_btn = kit.button(row, "Messung starten", self.start, "primary", icon="bench", height=40, width=190)
        self.start_btn.pack(side="left")
        self.bar = ctk.CTkProgressBar(ctrl, height=8, corner_radius=4, progress_color=T.CYAN, fg_color=T.CARD2)
        self.bar.set(0)
        self.bar.pack(fill="x", padx=20, pady=(4, 6))
        self.state = kit.label(ctrl, "Bereit.", 12, T.MUTED, wrap=980)
        self.state.pack(anchor="w", padx=20, pady=(0, 16))
        self.hist = kit.card(root, corner_radius=16)
        self.hist.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.cmp = kit.card(root, corner_radius=16)
        self.cmp.grid(row=3, column=0, sticky="ew", pady=(0, 16))
        self._running = False
        self.render_hist()

    def on_show(self):
        pm = fnmon.find_presentmon()
        self.pm_warn.configure(text="" if pm else "PresentMon.exe wurde nicht gefunden. Im fertigen Release ist es enthalten; bei einem lokalen Build "
                                                  "PresentMon.exe (Intel, MIT-Lizenz) neben die EXE legen.")
        self.render_hist()

    # ------------------------------------------------------------ Messung
    def start(self):
        if self._running:
            return
        pm = fnmon.find_presentmon()
        if not pm:
            self.app.tell("PresentMon fehlt", "PresentMon.exe wurde nicht gefunden. Ohne PresentMon kann keine echte FPS-Messung stattfinden, und SquallowTweaks erfindet keine Werte.")
            return
        if not self.app.monitor.latest.get("fortnite"):
            self.app.tell("Fortnite läuft nicht", "Starte Fortnite, gehe in ein Match oder den Kreativ-Modus und starte die Messung dann erneut.")
            return
        secs = int(self.dur.get().split()[0])
        name = self.name.get().strip() or f"Messung {len(self.app.bench.runs) + 1}"
        self._running = True
        self.start_btn.configure(state="disabled")
        t0 = time.time()
        self.bar.set(0)

        def countdown():
            if not self._running:
                return
            el = time.time() - t0
            self.bar.set(min(1.0, el / secs))
            self.state.configure(text=f"Messung läuft … {max(0, int(secs - el))} s. Bleibe im Spiel und bewege dich normal.", text_color=T.CYAN)
            self.frame.after(500, countdown)
        countdown()

        def work():
            ok, err = fnmon.run_capture(pm, CAPTURE_CSV, secs)
            if not ok:
                return ("err", err)
            stats = fnmon.compute_frame_stats(fnmon.parse_presentmon_csv(CAPTURE_CSV))
            return ("ok", stats) if stats else ("err", "Zu wenige Frames erfasst (Spiel im Hintergrund?).")

        def done(res):
            self._running = False
            self.start_btn.configure(state="normal")
            self.bar.set(0)
            if isinstance(res, tuple) and res[0] == "ok":
                self.app.bench.add(name, res[1])
                self.state.configure(text="Fertig: " + "  ·  ".join(res[1].lines()[1:3]), text_color=T.GREEN)
            else:
                self.state.configure(text=f"Messung fehlgeschlagen: {res[1] if isinstance(res, tuple) else res}", text_color=T.RED)
            self.render_hist()
        self.app.bg(work, done)

    # ------------------------------------------------------------ Verlauf & Vergleich
    def render_hist(self):
        for w in self.hist.winfo_children():
            w.destroy()
        kit.label(self.hist, "MESSUNGEN", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        runs = self.app.bench.runs[:8]
        if not runs:
            kit.label(self.hist, "Noch keine Messung.", 12, T.MUTED).pack(anchor="w", padx=20, pady=(0, 16))
        for r in runs:
            s = r["stats"]
            row = ctk.CTkFrame(self.hist, fg_color=T.CARD2, corner_radius=10)
            row.pack(fill="x", padx=16, pady=3)
            kit.label(row, r["name"], 12, T.TEXT, True, width=200).pack(side="left", padx=(12, 0), pady=8)
            kit.label(row, r["time"], 11, T.MUTED, width=100).pack(side="left")
            kit.label(row, f"Ø {s['avg_fps']:.0f} FPS", 12, T.TEXT2, width=110).pack(side="left")
            kit.label(row, f"1 % Low {s['low1_fps']:.0f}", 12, T.TEXT2, width=120).pack(side="left")
            kit.label(row, f"p99 {s['p99_ms']:.1f} ms", 12, T.TEXT2, width=110).pack(side="left")
            kit.button(row, "Löschen", lambda i=r["id"]: (self.app.bench.delete(i), self.render_hist()), "text", height=28, width=80).pack(side="right", padx=8)
        ctk.CTkFrame(self.hist, fg_color="transparent", height=10).pack()
        self.render_cmp()

    def render_cmp(self):
        for w in self.cmp.winfo_children():
            w.destroy()
        kit.label(self.cmp, "VERGLEICH", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        runs = self.app.bench.runs
        if len(runs) < 2:
            kit.label(self.cmp, "Für einen Vergleich werden mindestens zwei Messungen gebraucht.", 12, T.MUTED).pack(anchor="w", padx=20, pady=(0, 16))
            return
        labels = {f"{r['name']} ({r['time']})": r["id"] for r in runs}
        names = list(labels)
        row = ctk.CTkFrame(self.cmp, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 8))
        kit.label(row, "Vorher", 12, T.TEXT2).pack(side="left")
        a = ctk.CTkOptionMenu(row, values=names, width=230, height=34, fg_color=T.CARD2, button_color=T.VIOLET_D, dropdown_fg_color=T.CARD2)
        a.set(names[min(1, len(names) - 1)])
        a.pack(side="left", padx=(8, 18))
        kit.label(row, "Nachher", 12, T.TEXT2).pack(side="left")
        b = ctk.CTkOptionMenu(row, values=names, width=230, height=34, fg_color=T.CARD2, button_color=T.VIOLET_D, dropdown_fg_color=T.CARD2)
        b.set(names[0])
        b.pack(side="left", padx=8)
        out = ctk.CTkFrame(self.cmp, fg_color="transparent")
        out.pack(fill="x", padx=20, pady=(4, 16))

        def compare():
            for w in out.winfo_children():
                w.destroy()
            ra, rb = self.app.bench.get(labels[a.get()]), self.app.bench.get(labels[b.get()])
            if not ra or not rb:
                return
            for r in bench.compare(ra, rb):
                color = {"besser": T.GREEN, "schlechter": T.RED, "gleich": T.MUTED}[r["verdict"]]
                line = ctk.CTkFrame(out, fg_color="transparent")
                line.pack(fill="x", pady=3)
                kit.label(line, r["label"], 12, T.TEXT, True, width=220).pack(side="left")
                kit.label(line, f"{r['before']:.1f}{r['unit']}  →  {r['after']:.1f}{r['unit']}", 12, T.TEXT2, width=220).pack(side="left")
                kit.label(line, f"{r['delta_pct']:+.1f} %  {r['verdict']}", 12, color, True).pack(side="left")
            kit.label(out, "Kleine Unterschiede (unter ca. 3 %) liegen im Messrauschen. Miss für belastbare Werte mehrmals in derselben Spielsituation.", 11, T.MUTED, wrap=900).pack(anchor="w", pady=(8, 0))
        kit.button(row, "Vergleichen", compare, "primary", height=34, width=130).pack(side="left", padx=12)
        compare()
