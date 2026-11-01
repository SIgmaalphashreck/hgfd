"""Erzeugt assets/bird.png (transparent), assets/badge.png und assets/squallow.ico.
Saubere Vektor-Neuzeichnung des vom Nutzer gelieferten lila Vogels (Original nur ~30x28 px gross)."""
import math
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter

OUTLINE = (127, 102, 247, 255)
FILL_TOP = (240, 236, 255)
FILL_BOT = (208, 196, 250)


def ellipse_pts(cx, cy, rx, ry, rot_deg, n=90):
    t = math.radians(rot_deg)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * math.cos(t) - y * math.sin(t), cy + x * math.sin(t) + y * math.cos(t)))
    return pts


def chaikin(pts, n=2):
    for _ in range(n):
        out = []
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            out += [(0.75 * p[0] + 0.25 * q[0], 0.75 * p[1] + 0.25 * q[1]),
                    (0.25 * p[0] + 0.75 * q[0], 0.25 * p[1] + 0.75 * q[1])]
        pts = out
    return pts


def bird(size=1024):
    S = size * 3
    sc = S / 100.0
    P = lambda pts: [(x * sc, y * sc) for x, y in pts]
    mask = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(mask)
    d.polygon(P(ellipse_pts(48, 56, 29, 15, -22)), fill=255)                      # Koerper
    d.polygon(P(ellipse_pts(73, 38, 13.5, 12.5, 0)), fill=255)                    # Kopf
    d.polygon(P([(83, 32), (99, 40), (84, 46)]), fill=255)                        # Schnabel
    d.polygon(P(chaikin([(58, 46), (48, 30), (30, 18), (12, 14), (24, 32), (40, 52)], 2)), fill=255)   # Fluegel
    d.polygon(P(chaikin([(30, 64), (4, 76), (9, 83), (38, 72)], 1)), fill=255)    # Schwanz 1
    d.polygon(P(chaikin([(36, 70), (12, 92), (20, 95), (46, 76)], 1)), fill=255)  # Schwanz 2
    d.polygon(P([(36, 66), (46, 62), (48, 72), (40, 74)]), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(sc * 0.5)).point(lambda v: 255 if v > 127 else 0)
    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(int(sc * 2.6) // 2 * 2 + 1)), mask)
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        gd.line([(0, y), (S, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(FILL_TOP, FILL_BOT)) + (255,))
    body = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    body.paste(grad, (0, 0), mask)
    # Fluegel-Innenlinie und Auge
    inner = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    idr = ImageDraw.Draw(inner)
    wing_line = P(chaikin([(56, 47), (46, 36), (30, 26), (20, 24)], 2))
    idr.line(wing_line, fill=OUTLINE, width=int(sc * 1.6), joint="curve")
    idr.line(P([(40, 52), (52, 50), (62, 46)]), fill=(127, 102, 247, 150), width=int(sc * 1.0))
    ex, ey, r = 76 * sc, 35.5 * sc, sc * 2.5
    idr.ellipse((ex - r, ey - r, ex + r, ey + r), fill=OUTLINE)
    body = Image.alpha_composite(body, inner)
    ol = Image.new("RGBA", (S, S), OUTLINE)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(ol, (0, 0), edge)
    return Image.alpha_composite(body, out).resize((size, size), Image.LANCZOS)


def badge(size=512):
    s4 = size * 4
    base = Image.new("RGBA", (s4, s4), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((0, 0, s4 - 1, s4 - 1), radius=int(s4 * 0.22), fill=(13, 13, 24, 255))
    d.rounded_rectangle((s4 * 0.025, s4 * 0.025, s4 * 0.975, s4 * 0.975), radius=int(s4 * 0.2), outline=(139, 92, 246, 255), width=int(s4 * 0.016))
    b = bird(int(s4 * 0.70))
    base.alpha_composite(b, (int(s4 * 0.15), int(s4 * 0.16)))
    return base.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "assets"
    bird(512).save(f"{out}/bird.png")
    bd = badge(512)
    bd.save(f"{out}/badge.png")
    bd.save(f"{out}/squallow.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("ok")
