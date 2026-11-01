"""Basisklasse fuer Seiten: lazy gebaut, on_show/on_hide fuer Timer."""
import customtkinter as ctk

import theme as T


class Page:
    subtitle = ""

    def __init__(self, app, parent):
        self.app = app
        self.frame = ctk.CTkFrame(parent, fg_color=T.BG, corner_radius=0)
        self.built = False
        self._timer = None

    def ensure_built(self):
        if not self.built:
            self.build()
            self.built = True

    def build(self):
        pass

    def on_show(self):
        pass

    def on_hide(self):
        if self._timer is not None:
            try:
                self.frame.after_cancel(self._timer)
            except Exception:  # noqa: BLE001
                pass
            self._timer = None

    def every(self, ms: int, fn):
        """Wiederholt fn solange die Seite sichtbar ist (wird von on_hide gestoppt)."""
        def tick():
            self._timer = None
            if not self.app.alive or self.app.current_page_obj() is not self:
                return
            try:
                fn()
            finally:
                if self.app.alive and self.app.current_page_obj() is self:
                    self._timer = self.frame.after(ms, tick)
        self._timer = self.frame.after(ms, tick)
