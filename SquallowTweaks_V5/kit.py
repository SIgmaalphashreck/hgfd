"""SquallowTweaks - UI-Baukasten (wenige, schnelle Bausteine; alle Farben aus theme.py)."""
from __future__ import annotations

import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk

import fx
import theme as T
from icons import ctk_icon


def font(size=12, bold=False):
    return ctk.CTkFont(T.FONT_BOLD if bold else T.FONT, size, "normal")


# ---------------------------------------------------------------- Layout
class Scroll(tk.Frame):
    """Schneller Scrollbereich (tk.Canvas statt CTkScrollableFrame, das bei vielen Kindern laggt)."""

    def __init__(self, parent, bg: str = T.BG):
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.bar = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview, width=10,
                                    fg_color=bg, button_color=T.BORDER, button_hover_color=T.VIOLET_D)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.bar.pack(side="right", fill="y", padx=(2, 0))
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.bind_all("<MouseWheel>", self._wheel, add="+")

    def _wheel(self, e):
        try:
            if not self.winfo_ismapped() or not fx._pointer_inside(self.canvas):
                return
            if self.inner.winfo_height() > self.canvas.winfo_height():
                self.canvas.yview_scroll(int(-e.delta / 120) * 3, "units")
        except Exception:  # noqa: BLE001
            pass


def card(parent, **kw) -> ctk.CTkFrame:
    opts = dict(fg_color=T.CARD, corner_radius=14, border_width=1, border_color=T.BORDER)
    opts.update(kw)
    return ctk.CTkFrame(parent, **opts)


def hoverable(widget, fg=(T.CARD, T.CARD_HOVER), border=(T.BORDER, T.BORDER_HOVER)):
    fx.hover_fade(widget, {"fg_color": fg, "border_color": border})
    return widget


def label(parent, text="", size=12, color=T.TEXT, bold=False, anchor="w", wrap=0, **kw) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=text, text_color=color, font=font(size, bold), anchor=anchor, justify="left",
                        wraplength=wrap, **kw)


def badge(parent, text: str, color: str = T.MUTED) -> ctk.CTkLabel:
    return ctk.CTkLabel(parent, text=f" {text} ", text_color=color, fg_color=fx.lerp_color(T.CARD, color, 0.16),
                        corner_radius=7, font=font(10, True), height=20)


def button(parent, text, command, kind="ghost", icon: Optional[str] = None, height=38, width=0, icon_color=None):
    palette = {
        "primary": (T.VIOLET, T.VIOLET_L, "#ffffff", T.VIOLET),
        "accent": (T.CYAN, "#67E8F9", "#04121A", T.CYAN),
        "ghost": (T.CARD2, T.CARD_HOVER, T.TEXT, T.BORDER),
        "danger": ("#2A1218", "#4A1824", "#FDA4AF", "#4A1824"),
        "text": ("transparent", T.CARD2, T.TEXT2, "transparent"),
    }
    fg, hov, tc, bc = palette[kind]
    img = ctk_icon(icon, 18, icon_color or tc) if icon else None
    b = ctk.CTkButton(parent, text=text, command=command, height=height, corner_radius=10, fg_color=fg, hover_color=hov,
                      text_color=tc, border_width=1, border_color=bc, font=font(12, True), image=img, compound="left",
                      **({"width": width} if width else {}))
    if kind in ("ghost", "primary", "accent"):
        fx.hover_fade(b, {"border_color": (bc, "#ffffff" if kind != "ghost" else T.VIOLET_L)})
    return b


def heading(parent, title: str, sub: str = "") -> ctk.CTkFrame:
    f = ctk.CTkFrame(parent, fg_color="transparent")
    label(f, title, 22, T.TEXT, True).pack(anchor="w")
    if sub:
        label(f, sub, 11, T.MUTED).pack(anchor="w", pady=(2, 0))
    return f


# ---------------------------------------------------------------- Dialoge
class Dialog(ctk.CTkToplevel):
    """Modaler Dialog im App-Design (ersetzt die grauen Windows-Messageboxen)."""

    def __init__(self, app, title: str, text: str, ok="OK", cancel: Optional[str] = None, danger=False, mono=False):
        super().__init__(app)
        self.result = False
        self.title(title)
        self.configure(fg_color=T.BG)
        self.resizable(False, False)
        try:
            self.transient(app)
        except Exception:  # noqa: BLE001
            pass
        box = card(self, fg_color=T.CARD, corner_radius=16)
        box.pack(fill="both", expand=True, padx=14, pady=14)
        label(box, title, 16, T.TEXT, True).pack(anchor="w", padx=20, pady=(18, 6))
        long = len(text) > 420 or text.count("\n") > 9
        if long:
            tb = ctk.CTkTextbox(box, width=520, height=260, fg_color=T.CARD2, text_color=T.TEXT2, corner_radius=10,
                                font=ctk.CTkFont("Consolas" if mono else T.FONT, 12), border_width=0)
            tb.insert("1.0", text)
            tb.configure(state="disabled")
            tb.pack(padx=20, pady=(0, 10))
        else:
            label(box, text, 12, T.TEXT2, wrap=480).pack(anchor="w", padx=20, pady=(0, 14))
        row = ctk.CTkFrame(box, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))
        if cancel:
            button(row, cancel, lambda: self._close(False), "ghost", height=36, width=120).pack(side="right", padx=(8, 0))
        button(row, ok, lambda: self._close(True), "danger" if danger else "primary", height=36, width=120).pack(side="right")
        self.update_idletasks()
        try:
            w, h = self.winfo_reqwidth(), self.winfo_reqheight()
            x = app.winfo_rootx() + (app.winfo_width() - w) // 2
            y = app.winfo_rooty() + (app.winfo_height() - h) // 3
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:  # noqa: BLE001
            pass
        self.protocol("WM_DELETE_WINDOW", lambda: self._close(False))
        self.after(60, self._grab)

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:  # noqa: BLE001
            pass

    def _close(self, value: bool):
        self.result = value
        try:
            self.grab_release()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()


def ask(app, title, text, ok="OK", cancel="Abbrechen", danger=False, mono=False) -> bool:
    d = Dialog(app, title, text, ok, cancel, danger, mono)
    app.wait_window(d)
    return d.result


def tell(app, title, text, mono=False) -> None:
    d = Dialog(app, title, text, "OK", None, False, mono)
    app.wait_window(d)


class ProgressDialog(ctk.CTkToplevel):
    """Zeigt Fortschritt und am Ende das Ergebnis. Schliessen erst nach Abschluss."""

    def __init__(self, app, title: str):
        super().__init__(app)
        self.app = app
        self.title(title)
        self.configure(fg_color=T.BG)
        self.resizable(False, False)
        try:
            self.transient(app)
        except Exception:  # noqa: BLE001
            pass
        self.done = False
        self.want_restart = False
        box = card(self, corner_radius=16)
        box.pack(fill="both", expand=True, padx=14, pady=14)
        self.title_lbl = label(box, title, 16, T.TEXT, True)
        self.title_lbl.pack(anchor="w", padx=20, pady=(18, 4))
        self.step = label(box, "Starte …", 12, T.TEXT2, wrap=520)
        self.step.pack(anchor="w", padx=20)
        self.bar = ctk.CTkProgressBar(box, width=520, height=8, corner_radius=4, progress_color=T.CYAN, fg_color=T.CARD2)
        self.bar.set(0)
        self.bar.pack(padx=20, pady=(10, 10))
        self.log = ctk.CTkTextbox(box, width=520, height=200, fg_color=T.CARD2, text_color=T.TEXT2, corner_radius=10,
                                  font=ctk.CTkFont(T.FONT, 12), border_width=0)
        self.log.configure(state="disabled")
        self.log.pack(padx=20)
        self.row = ctk.CTkFrame(box, fg_color="transparent")
        self.row.pack(fill="x", padx=20, pady=(12, 18))
        self.protocol("WM_DELETE_WINDOW", lambda: self.destroy() if self.done else None)
        self.update_idletasks()
        try:
            x = app.winfo_rootx() + (app.winfo_width() - self.winfo_reqwidth()) // 2
            y = app.winfo_rooty() + (app.winfo_height() - self.winfo_reqheight()) // 3
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:  # noqa: BLE001
            pass

    def update_progress(self, frac: float, text: str):
        self.bar.set(max(0.0, min(1.0, frac)))
        self.step.configure(text=text)

    def add(self, line: str, color: Optional[str] = None):
        self.log.configure(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def finish(self, headline: str, restart_offer: bool = False, on_restart: Optional[Callable[[], None]] = None):
        self.done = True
        self.bar.set(1.0)
        self.step.configure(text=headline)
        for w in self.row.winfo_children():
            w.destroy()
        button(self.row, "Schließen", self.destroy, "primary", height=36, width=130).pack(side="right")
        if restart_offer and on_restart:
            button(self.row, "Jetzt neu starten", lambda: (self.destroy(), on_restart()), "accent", height=36, width=170).pack(side="right", padx=8)
