"""Tweaks: kompakte Kacheln mit Schalter. Aenderungen werden gesammelt und per 'Anwenden' ausgefuehrt."""
from __future__ import annotations

import customtkinter as ctk

import kit
import texts
import theme as T
import tweaklib
from icons import ctk_icon
from pages.base import Page

EFFECT_RANK = {"Stark": 0, "Mittel": 1, "Klein": 2, "Unsicher": 3}
GROUP_RANK = {"Fortnite": 0, "FPS": 1, "Latenz": 2, "Netzwerk": 3, "System": 4}
PROFILES = {"SAFE": "safe", "COMPETITIVE": "competitive", "MAX FPS": "maxfps"}


class Tile:
    def __init__(self, page, parent, t):
        self.page, self.t = page, t
        self.group, self.effect, short = texts.short_for(t)
        app = page.app
        self.locked = t.admin and not tweaklib.is_admin()
        f = kit.card(parent, corner_radius=14)
        self.frame = f
        f.grid_columnconfigure(0, weight=1)
        kit.label(f, t.name.split(":")[-1].strip() if t.id.startswith("fn_") else t.name, 13, T.TEXT, True, wrap=330).grid(
            row=0, column=0, sticky="w", padx=(16, 4), pady=(14, 0))
        self.var = ctk.BooleanVar(value=False)
        self.sw = ctk.CTkSwitch(f, text="", variable=self.var, onvalue=True, offvalue=False, width=46, switch_width=42, switch_height=22,
                                progress_color=T.CYAN, button_color="#FFFFFF", button_hover_color="#E8F9FF", fg_color="#2A2A40",
                                command=lambda: page.on_switch(t.id, bool(self.var.get())))
        self.sw.grid(row=0, column=1, rowspan=2, padx=(4, 16), pady=(12, 0), sticky="ne")
        kit.label(f, short, 11, T.TEXT2, wrap=330).grid(row=1, column=0, sticky="w", padx=(16, 4), pady=(2, 8))
        bar = ctk.CTkFrame(f, fg_color="transparent")
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 12))
        kit.badge(bar, self.effect.upper(), T.EFFECT_COLORS.get(self.effect, T.MUTED)).pack(side="left")
        if t.admin:
            kit.badge(bar, "ADMIN", T.AMBER).pack(side="left", padx=(6, 0))
        self.status = kit.label(bar, "", 11, T.MUTED)
        self.status.pack(side="left", padx=(10, 0))
        ctk.CTkButton(bar, text="", image=ctk_icon("info", 16, "#8E91AD"), width=28, height=24, fg_color="transparent",
                      hover_color=T.CARD2, command=lambda: page.show_info(t)).pack(side="right")
        kit.hoverable(f)

    def sync(self):
        app = self.page.app
        state, detail = app.states.get(self.t.id, ("", ""))
        active = state == tweaklib.STATUS_ACTIVE
        unavailable = state == tweaklib.STATUS_UNKNOWN and self.t.kind in ("powersetting", "ini", "nic", "registry") and bool(app.states)
        if self.t.id in app.pending:
            self.var.set(app.pending[self.t.id])
        else:
            self.var.set(active)
        if self.locked:
            self.sw.configure(state="disabled")
            self.status.configure(text="Administrator nötig", text_color=T.AMBER)
        elif unavailable and not active:
            self.sw.configure(state="disabled")
            self.status.configure(text="Nicht verfügbar", text_color=T.DIM)
        else:
            self.sw.configure(state="normal")
            text, color = {tweaklib.STATUS_ACTIVE: ("● Aktiv", T.GREEN), tweaklib.STATUS_PARTIAL: ("◐ Teilweise", T.AMBER)}.get(
                state, ("○ Aus" if state else "…", T.MUTED))
            if self.t.id in app.pending:
                text, color = "● wird angewendet" if app.pending[self.t.id] else "○ wird zurückgesetzt", T.CYAN
            self.status.configure(text=text, text_color=color)


class TweaksPage(Page):
    subtitle = "Schalter setzen, dann anwenden. Jede Änderung wird gesichert und geprüft."

    def build(self):
        f = self.frame
        f.grid_rowconfigure(1, weight=1)
        f.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(f, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.group = ctk.CTkSegmentedButton(top, values=texts.GROUPS, command=lambda _v: self.apply_filter(), height=34,
                                            fg_color=T.CARD2, selected_color=T.VIOLET, selected_hover_color=T.VIOLET_L,
                                            unselected_color=T.CARD2, unselected_hover_color=T.CARD_HOVER, text_color=T.TEXT,
                                            font=kit.font(12, True))
        self.group.set("Alle")
        self.group.pack(side="left")
        self.search = ctk.CTkEntry(top, placeholder_text="Tweak suchen …", width=240, height=34, fg_color=T.CARD2,
                                   border_color=T.BORDER, text_color=T.TEXT, corner_radius=10)
        self.search.pack(side="right")
        self.search.bind("<KeyRelease>", lambda _e: self._debounce())
        self.scroll = kit.Scroll(f)
        self.scroll.grid(row=1, column=0, sticky="nsew")
        self.grid = self.scroll.inner
        self.grid.grid_columnconfigure((0, 1), weight=1, uniform="t")
        self.empty = kit.label(self.grid, "Keine Tweaks gefunden.", 12, T.MUTED)
        # Aktionsleiste
        bar = kit.card(f, corner_radius=14, fg_color=T.CARD2)
        bar.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.count = kit.label(bar, "Keine Änderungen ausgewählt", 12, T.CYAN, True)
        self.count.pack(side="left", padx=18, pady=12)
        kit.button(bar, "Anwenden & Neustart", lambda: self.apply(True), "accent", height=38, width=180).pack(side="right", padx=(6, 12), pady=10)
        kit.button(bar, "Anwenden", lambda: self.apply(False), "primary", height=38, width=120).pack(side="right", padx=6, pady=10)
        kit.button(bar, "Zurücksetzen", self.clear_pending, "ghost", height=38, width=120).pack(side="right", padx=6, pady=10)
        kit.button(bar, "Profil wählen", self.pick_profile, "ghost", height=38, width=130).pack(side="right", padx=(6, 6), pady=10)
        self.profile = ctk.CTkOptionMenu(bar, values=list(PROFILES), width=140, height=38, fg_color=T.CARD, button_color=T.VIOLET_D,
                                         button_hover_color=T.VIOLET, text_color=T.TEXT, dropdown_fg_color=T.CARD2,
                                         command=self.set_profile)
        cur = self.app.settings.get("profile")
        self.profile.set(next((k for k, v in PROFILES.items() if v == cur), "COMPETITIVE"))
        self.profile.pack(side="right", padx=(6, 0), pady=10)
        # Kacheln schrittweise bauen (kein Einfrieren beim ersten Oeffnen)
        items = [t for t in self.app.catalog if t.kind in tweaklib.TOGGLE_KINDS]
        items.sort(key=lambda t: (GROUP_RANK.get(texts.short_for(t)[0], 9), EFFECT_RANK.get(texts.short_for(t)[1], 9), t.name))
        self.tiles: dict[str, Tile] = {}
        self._queue = items
        self._db = None
        self.app.on_states(self.sync_all)
        self._build_chunk()

    def _build_chunk(self):
        for _ in range(6):
            if not self._queue:
                break
            t = self._queue.pop(0)
            self.tiles[t.id] = Tile(self, self.grid, t)
        if self._queue:
            self.frame.after(8, self._build_chunk)
        else:
            self.apply_filter()
            self.sync_all()

    # ------------------------------------------------------------ Filter
    def _debounce(self):
        if self._db is not None:
            self.frame.after_cancel(self._db)
        self._db = self.frame.after(160, self.apply_filter)

    def apply_filter(self):
        self._db = None
        g = self.group.get()
        q = self.search.get().strip().lower()
        shown = []
        for tid, tile in self.tiles.items():
            ok = (g == "Alle" or tile.group == g) and (not q or q in tile.t.name.lower() or q in tile.t.description.lower())
            if ok:
                shown.append(tile)
            else:
                tile.frame.grid_remove()
        self.empty.grid_forget()
        for i, tile in enumerate(shown):
            tile.frame.grid(row=i // 2, column=i % 2, sticky="nsew", padx=(0 if i % 2 == 0 else 6, 6 if i % 2 == 0 else 0), pady=6)
        if not shown:
            self.empty.grid(row=0, column=0, columnspan=2, pady=40)

    def on_show(self):
        self.app.refresh_states()

    def sync_all(self):
        for tile in self.tiles.values():
            tile.sync()
        self.update_count()

    # ------------------------------------------------------------ Auswahl
    def on_switch(self, tid: str, want: bool):
        if want == self.app.is_active(tid):
            self.app.pending.pop(tid, None)
        else:
            self.app.pending[tid] = want
        self.tiles[tid].sync()
        self.update_count()

    def update_count(self):
        n = len(self.app.pending)
        self.count.configure(text="Keine Änderungen ausgewählt" if n == 0 else f"{n} Änderung{'en' if n != 1 else ''} ausgewählt",
                             text_color=T.CYAN if n == 0 else T.AMBER)

    def clear_pending(self):
        self.app.pending.clear()
        self.sync_all()

    def set_profile(self, name: str):
        self.app.settings.set("profile", PROFILES[name])

    def pick_profile(self):
        profile = PROFILES[self.profile.get()]
        ctx = self.app.ctx()
        self.app.set_status("Wähle Tweaks für dein System …")

        def work():
            return tweaklib.select_for_profile(self.app.catalog, self.app.engine, ctx, profile)

        def done(res):
            if not isinstance(res, tuple):
                return
            chosen, skipped = res
            for t in chosen:
                self.app.pending[t.id] = True
            self.sync_all()
            self.app.set_status(f"{len(chosen)} Tweaks für Profil {self.profile.get()} ausgewählt, {len(skipped)} übersprungen. Mit 'Anwenden' bestätigen.")
        self.app.bg(work, done)

    def show_info(self, t):
        txt = (f"{t.description}\n\nAuswirkung:\n{t.impact}\n\nWirksam: {t.restart if t.restart != 'Nein' else 'sofort'}"
               f"\nBackup: automatisch vor der Änderung · Undo: Schalter ausschalten und anwenden"
               + ("\nBenötigt Administratorrechte." if t.admin else ""))
        self.app.tell(t.name, txt)

    def apply(self, restart: bool):
        plan = [(self.app.by_id[tid], want) for tid, want in self.app.pending.items()]
        if not plan:
            self.app.tell("Keine Änderungen", "Schalte bei den Tweaks Schalter um oder wähle ein Profil, dann auf Anwenden klicken.")
            return
        lines = [("＋ " if on else "－ ") + t.name for t, on in self.app.order_plan(plan)]
        extra = "\n\nDanach startet der PC neu (20 s, abbrechbar)." if restart else ""
        if not self.app.ask("Änderungen anwenden?", "\n".join(lines) + "\n\nJeder Originalwert wird gesichert, jede Änderung geprüft." + extra, "Anwenden"):
            return
        self.app.run_plan(plan, "Tweaks anwenden", restart)
