"""SquallowTweaks - Vektor-Icons, zur Laufzeit mit PIL gezeichnet (kein Emoji, keine Bilddateien noetig)."""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import Image, ImageDraw

SS = 8  # Supersampling


def _canvas(size):
    n = size * SS
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img), n / 100.0


def _draw(name: str, size: int, color: str) -> Image.Image:
    img, d, k = _canvas(size)
    w = max(2, int(7 * k))
    P = lambda *pts: [(x * k, y * k) for x, y in pts]
    if name == "dashboard":
        for x, y, ww, hh in ((14, 14, 32, 40), (54, 14, 32, 22), (14, 62, 32, 24), (54, 44, 32, 42)):
            d.rounded_rectangle((x * k, y * k, (x + ww) * k, (y + hh) * k), radius=7 * k, outline=color, width=w)
    elif name == "tweaks":      # Blitz
        d.polygon(P((58, 8), (22, 54), (46, 54), (38, 92), (78, 42), (54, 42)), outline=color, width=w, fill=None)
        d.line(P((58, 8), (22, 54), (46, 54), (38, 92), (78, 42), (54, 42), (58, 8)), fill=color, width=w, joint="curve")
    elif name == "game":        # Fadenkreuz
        d.ellipse(P((20, 20), (80, 80)), outline=color, width=w)
        for a, b in (((50, 6), (50, 32)), ((50, 68), (50, 94)), ((6, 50), (32, 50)), ((68, 50), (94, 50))):
            d.line(P(a, b), fill=color, width=w)
        d.ellipse(P((45, 45), (55, 55)), fill=color)
    elif name == "bench":       # Balkendiagramm
        for x, top in ((16, 50), (42, 20), (68, 66)):
            d.rounded_rectangle((x * k, top * k, (x + 16) * k, 88 * k), radius=4 * k, outline=color, width=w)
    elif name == "process":     # Liste
        for y in (24, 50, 76):
            d.ellipse(P((12, y - 6), (24, y + 6)), fill=color)
            d.line(P((34, y), (88, y)), fill=color, width=w)
    elif name == "network":     # WLAN-Bogen
        for r in (18, 34, 50):
            d.arc(P((50 - r, 78 - r), (50 + r, 78 + r)), start=225, end=315, fill=color, width=w)
        d.ellipse(P((44, 72), (56, 84)), fill=color)
    elif name == "cleanup":     # Besen/Abfall: Tonne
        d.line(P((18, 26), (82, 26)), fill=color, width=w)
        d.line(P((38, 26), (38, 14), (62, 14), (62, 26)), fill=color, width=w, joint="curve")
        d.rounded_rectangle(P((26, 30), (74, 90)), radius=6 * k, outline=color, width=w)
        d.line(P((42, 42), (42, 78)), fill=color, width=int(w * 0.8))
        d.line(P((58, 42), (58, 78)), fill=color, width=int(w * 0.8))
    elif name == "settings":    # Zahnrad
        c = 50 * k
        for i in range(8):
            a = math.radians(i * 45)
            x1, y1 = c + math.cos(a) * 30 * k, c + math.sin(a) * 30 * k
            x2, y2 = c + math.cos(a) * 44 * k, c + math.sin(a) * 44 * k
            d.line([(x1, y1), (x2, y2)], fill=color, width=int(11 * k))
        d.ellipse(P((22, 22), (78, 78)), outline=color, width=w)
        d.ellipse(P((38, 38), (62, 62)), outline=color, width=w)
    elif name == "bolt_fill":   # gefuellter Blitz (Auto-Button)
        d.polygon(P((58, 6), (20, 56), (46, 56), (38, 94), (80, 40), (54, 40)), fill=color)
    elif name == "check":
        d.line(P((22, 54), (42, 74), (80, 28)), fill=color, width=int(9 * k), joint="curve")
    elif name == "info":
        d.ellipse(P((10, 10), (90, 90)), outline=color, width=w)
        d.line(P((50, 44), (50, 72)), fill=color, width=int(8 * k))
        d.ellipse(P((45, 26), (55, 36)), fill=color)
    return img.resize((size, size), Image.LANCZOS)


@lru_cache(maxsize=64)
def pil_icon(name: str, size: int = 22, color: str = "#B4B7D0") -> Image.Image:
    return _draw(name, size, color)


def ctk_icon(name: str, size: int = 20, color: str = "#B4B7D0"):
    import customtkinter as ctk
    img = pil_icon(name, size * 2, color)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
