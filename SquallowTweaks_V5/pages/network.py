"""Netzwerk: Live-Ping mit Jitter/Verlust, Speedtest, Verbindungsdetails, Epic-Endpunkte."""
from __future__ import annotations

import threading
import time

import customtkinter as ctk

import kit
import netlab
import theme as T
from pages.base import Page
from ui_widgets import Sparkline


class NetworkPage(Page):
    subtitle = "Echte Messungen: Ping, Jitter, Paketverlust, Durchsatz. Kein Fortnite-Serverping."

    def build(self):
        sc = kit.Scroll(self.frame)
        sc.pack(fill="both", expand=True)
        root = sc.inner
        root.grid_columnconfigure((0, 1), weight=1, uniform="n")
        self.gateway = None
        self.samples: list = []
        self.sent = 0
        self.running = False
        self._thread = None
        # Live-Ping
        live = kit.card(root, corner_radius=16)
        live.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        row = ctk.CTkFrame(live, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(18, 8))
        kit.label(row, "Live-Ping", 16, T.TEXT, True).pack(side="left")
        self.target = ctk.CTkSegmentedButton(row, values=["Router", "1.1.1.1", "8.8.8.8"], height=34, fg_color=T.CARD2, selected_color=T.VIOLET,
                                             selected_hover_color=T.VIOLET_L, unselected_color=T.CARD2, unselected_hover_color=T.CARD_HOVER,
                                             font=kit.font(12, True))
        self.target.set("1.1.1.1")
        self.target.pack(side="left", padx=16)
        self.go = kit.button(row, "Start", self.toggle, "primary", height=34, width=100)
        self.go.pack(side="right")
        self.spark = Sparkline(live, height=110, color=T.CYAN, bg=T.CARD, grid="#181828", label="Ping", unit=" ms", vmax=None)
        self.spark.pack(fill="x", padx=20, pady=(0, 6))
        self.stats = kit.label(live, "Noch nicht gestartet. Zum Testen die Verbindung beobachten, während du spielst oder lädst.", 12, T.TEXT2, wrap=980)
        self.stats.pack(anchor="w", padx=20)
        self.verdict = kit.label(live, "", 13, T.MUTED, True)
        self.verdict.pack(anchor="w", padx=20, pady=(4, 16))
        # Speed
        sp = kit.card(root, corner_radius=16)
        sp.grid(row=1, column=0, sticky="nsew", padx=(0, 5), pady=(0, 10))
        kit.label(sp, "DURCHSATZ", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 4))
        kit.label(sp, "HTTPS-Transfer über Cloudflare (ca. 8 s je Richtung). Verbraucht etwas Datenvolumen.", 11, T.MUTED, wrap=420).pack(anchor="w", padx=20)
        r = ctk.CTkFrame(sp, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=10)
        self.dl_btn = kit.button(r, "Download testen", self.download, "ghost", height=38)
        self.dl_btn.pack(side="left", expand=True, fill="x", padx=4)
        self.ul_btn = kit.button(r, "Upload testen", self.upload, "ghost", height=38)
        self.ul_btn.pack(side="left", expand=True, fill="x", padx=4)
        self.speed = kit.label(sp, "Noch nicht gemessen.", 12, T.TEXT2, wrap=420)
        self.speed.pack(anchor="w", padx=20, pady=(0, 16))
        # Epic
        ep = kit.card(root, corner_radius=16)
        ep.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=(0, 10))
        kit.label(ep, "EPIC-ENDPUNKTE & DNS", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 4))
        kit.label(ep, "TCP-Handshake zu Epic-Webseiten und DNS-Zeit. Das ist NICHT der Spielserver-Ping.", 11, T.MUTED, wrap=420).pack(anchor="w", padx=20)
        kit.button(ep, "Testen", self.epic, "ghost", height=38).pack(fill="x", padx=20, pady=10)
        self.epic_lbl = kit.label(ep, "Noch nicht gemessen.", 12, T.TEXT2, wrap=420)
        self.epic_lbl.pack(anchor="w", padx=20, pady=(0, 16))
        # Verbindung
        info = kit.card(root, corner_radius=16)
        info.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        kit.label(info, "VERBINDUNG", 10, T.DIM, True).pack(anchor="w", padx=20, pady=(16, 6))
        self.conn = kit.label(info, "Wird geladen …", 12, T.TEXT2, wrap=980)
        self.conn.pack(anchor="w", padx=20, pady=(0, 16))

    def on_show(self):
        def work():
            return netlab.get_network_config()

        def done(cfg):
            if not isinstance(cfg, list):
                return
            lines = []
            for c in cfg:
                self.gateway = self.gateway or (c["gateway"][0] if c["gateway"] else None)
                lines.append(f"{c['name']}  ·  {c['link_speed'] or 'Geschwindigkeit N/A'}  ·  IPv4 {', '.join(c['ipv4']) or 'N/A'}  ·  "
                             f"Gateway {', '.join(c['gateway']) or 'N/A'}  ·  DNS {', '.join(c['dns']) or 'N/A'}")
            self.conn.configure(text="\n".join(lines) or "Keine aktive Verbindung erkannt.")
        self.app.bg(work, done)

    def on_hide(self):
        super().on_hide()
        self.running = False
        self.go.configure(text="Start")

    # ------------------------------------------------------------ Live-Ping
    def host(self):
        t = self.target.get()
        if t == "Router":
            return self.gateway
        return t

    def toggle(self):
        if self.running:
            self.running = False
            self.go.configure(text="Start")
            return
        host = self.host()
        if not host:
            self.stats.configure(text="Kein Router/Gateway erkannt. Wähle ein anderes Ziel.", text_color=T.AMBER)
            return
        self.samples, self.sent = [], 0
        self.spark.data.clear()
        self.spark.data.extend([0.0] * 60)
        self.running = True
        self.go.configure(text="Stopp")

        def loop():
            while self.running and self.app.alive:
                v = netlab.ping_once(host, 1000)
                self.sent += 1
                self.samples.append(v)
                time.sleep(0.35)
        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        self.every(500, self.tick)

    def tick(self):
        if not self.running:
            return
        got = [s for s in self.samples if s is not None]
        if not got:
            return
        recent = self.samples[-60:]
        self.spark.data.clear()
        self.spark.data.extend([s if s is not None else 0.0 for s in recent])
        self.spark.redraw()
        window = [s for s in self.samples[-100:] if s is not None]
        loss = 100.0 * (len(self.samples) - len(got)) / max(1, len(self.samples))
        jit = netlab.calc_jitter(window) or 0.0
        avg = sum(window) / len(window)
        self.stats.configure(text=f"Ziel {self.host()}  ·  Ø {avg:.1f} ms  ·  min {min(window):.1f}  ·  max {max(window):.1f}  ·  "
                                  f"Jitter {jit:.1f} ms  ·  Verlust {loss:.1f} %  ·  {len(self.samples)} Pings", text_color=T.TEXT2)
        if loss == 0 and jit < 3:
            self.verdict.configure(text="● Stabil", text_color=T.GREEN)
        elif loss < 2 and jit < 8:
            self.verdict.configure(text="● Leichte Schwankungen", text_color=T.AMBER)
        else:
            self.verdict.configure(text="● Instabil: Kabel, WLAN, Router oder Hintergrund-Downloads prüfen", text_color=T.RED)

    # ------------------------------------------------------------ Tests
    def _busy(self, on: bool):
        for b in (self.dl_btn, self.ul_btn):
            b.configure(state="disabled" if on else "normal")

    def download(self):
        self._busy(True)
        self.speed.configure(text="Download läuft …", text_color=T.CYAN)

        def work():
            return netlab.download_test(8.0, 4, progress=lambda m: self.app.ui(lambda: self.speed.configure(text=f"Download läuft … {m:.0f} Mbit/s")))
        self.app.bg(work, lambda r: (self._busy(False), self.speed.configure(text=r.summary() if hasattr(r, "summary") else str(r), text_color=T.TEXT2)))

    def upload(self):
        self._busy(True)
        self.speed.configure(text="Upload läuft … (bis ca. 25 s)", text_color=T.CYAN)
        self.app.bg(lambda: netlab.upload_test(8.0, 3),
                    lambda r: (self._busy(False), self.speed.configure(text=r.summary() if hasattr(r, "summary") else str(r), text_color=T.TEXT2)))

    def epic(self):
        self.epic_lbl.configure(text="Teste …", text_color=T.CYAN)

        def work():
            lines = []
            for host in ("www.epicgames.com", "cloudflare.com"):
                ms, info = netlab.dns_lookup_ms(host)
                lines.append(f"DNS {host}: {ms:.0f} ms" if ms is not None else f"DNS {host}: fehlgeschlagen")
            for host, port in netlab.EPIC_TCP_TARGETS:
                lines.append(netlab.tcp_connect_ms(host, port, 5).summary())
            return "\n".join(lines)
        self.app.bg(work, lambda r: self.epic_lbl.configure(text=str(r), text_color=T.TEXT2))
