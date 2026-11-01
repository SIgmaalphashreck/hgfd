"""Prozesse: schnelle Tabelle (ttk.Treeview) mit Sortierung, Suche, Prioritaet und geschuetztem Beenden."""
from __future__ import annotations

from tkinter import ttk

import customtkinter as ctk

import kit
import procs
import theme as T
from monitor import FORTNITE_EXE
from pages.base import Page

COLS = (("name", "Name", 280, "w"), ("pid", "PID", 80, "e"), ("cpu", "CPU", 80, "e"), ("ram", "RAM", 110, "e"),
        ("prio", "Priorität", 100, "center"), ("status", "Status", 100, "center"))


def style_tree():
    st = ttk.Style()
    try:
        st.theme_use("clam")
    except Exception:  # noqa: BLE001
        pass
    st.configure("Sq.Treeview", background=T.CARD, fieldbackground=T.CARD, foreground=T.TEXT, rowheight=30, borderwidth=0,
                 relief="flat", font=(T.FONT, 11))
    st.configure("Sq.Treeview.Heading", background=T.CARD2, foreground=T.TEXT2, relief="flat", borderwidth=0, font=(T.FONT_BOLD, 10),
                 padding=(8, 8))
    st.map("Sq.Treeview", background=[("selected", T.VIOLET_D)], foreground=[("selected", "#FFFFFF")])
    st.map("Sq.Treeview.Heading", background=[("active", T.CARD_HOVER)])
    st.layout("Sq.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])


class ProcessesPage(Page):
    subtitle = "Was frisst Leistung? Priorität ändern oder Programme beenden (Systemprozesse sind geschützt)"

    def build(self):
        style_tree()
        self.sampler = procs.ProcSampler()
        self.rows: dict[int, dict] = {}
        self.sort_key, self.sort_rev = "cpu", True
        self.busy = False
        f = self.frame
        f.grid_columnconfigure(0, weight=1)
        f.grid_rowconfigure(1, weight=1)
        # Kennzahlen
        tiles = ctk.CTkFrame(f, fg_color="transparent")
        tiles.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        tiles.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="p")
        self.t_count = self._tile(tiles, 0, "PROZESSE")
        self.t_cpu = self._tile(tiles, 1, "CPU GESAMT")
        self.t_ram = self._tile(tiles, 2, "RAM GESAMT")
        self.t_top = self._tile(tiles, 3, "GRÖSSTER VERBRAUCHER")
        # Tabelle
        left = kit.card(f, corner_radius=14)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)
        bar = ctk.CTkFrame(left, fg_color="transparent")
        bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 8))
        self.search = ctk.CTkEntry(bar, placeholder_text="Prozess suchen …", width=260, height=34, fg_color=T.CARD2, border_color=T.BORDER,
                                   text_color=T.TEXT, corner_radius=10)
        self.search.pack(side="left")
        self.search.bind("<KeyRelease>", lambda _e: self.apply())
        self.filter = ctk.CTkSegmentedButton(bar, values=["Alle", "Hohe Last", "Fortnite"], height=34, command=lambda _v: self.apply(),
                                             fg_color=T.CARD2, selected_color=T.VIOLET, selected_hover_color=T.VIOLET_L,
                                             unselected_color=T.CARD2, unselected_hover_color=T.CARD_HOVER, font=kit.font(12, True))
        self.filter.set("Alle")
        self.filter.pack(side="left", padx=10)
        self.tree = ttk.Treeview(left, columns=[c[0] for c in COLS], show="headings", style="Sq.Treeview", selectmode="browse")
        for key, title, width, anchor in COLS:
            self.tree.heading(key, text=title, command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=width, anchor=anchor, stretch=(key == "name"))
        self.tree.tag_configure("prot", foreground=T.DIM)
        self.tree.tag_configure("hot", foreground=T.AMBER)
        self.tree.tag_configure("fn", foreground=T.CYAN)
        bar_y = ctk.CTkScrollbar(left, orientation="vertical", command=self.tree.yview, width=10, fg_color=T.CARD,
                                 button_color=T.BORDER, button_hover_color=T.VIOLET_D)
        self.tree.configure(yscrollcommand=bar_y.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
        bar_y.grid(row=1, column=1, sticky="ns", padx=(2, 8), pady=(0, 12))
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.show_selected())
        # Aktionen
        right = kit.card(f, corner_radius=14, width=300)
        right.grid(row=1, column=1, sticky="ns")
        right.grid_propagate(False)
        kit.label(right, "AUSGEWÄHLT", 10, T.DIM, True).pack(anchor="w", padx=18, pady=(16, 4))
        self.sel_name = kit.label(right, "Kein Prozess gewählt", 15, T.TEXT, True, wrap=260)
        self.sel_name.pack(anchor="w", padx=18)
        self.sel_info = kit.label(right, "Wähle links einen Prozess.", 11, T.MUTED, wrap=260)
        self.sel_info.pack(anchor="w", padx=18, pady=(4, 14))
        kit.label(right, "PRIORITÄT", 10, T.DIM, True).pack(anchor="w", padx=18, pady=(0, 6))
        pr = ctk.CTkFrame(right, fg_color="transparent")
        pr.pack(fill="x", padx=14)
        for lvl in procs.PRIORITIES:
            kit.button(pr, lvl, lambda l=lvl: self.set_prio(l), "ghost", height=34, width=84).pack(side="left", padx=4)
        kit.label(right, "Niemals Echtzeit: das kann Windows einfrieren.", 10, T.MUTED, wrap=260).pack(anchor="w", padx=18, pady=(8, 16))
        self.kill_btn = kit.button(right, "Prozess beenden", self.kill, "danger", height=40)
        self.kill_btn.pack(fill="x", padx=18)
        self.note = kit.label(right, "", 11, T.MUTED, wrap=260)
        self.note.pack(anchor="w", padx=18, pady=(10, 0))

    def _tile(self, parent, col, title):
        c = kit.card(parent, corner_radius=12)
        c.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 5, 5 if col < 3 else 0))
        kit.label(c, title, 10, T.DIM, True).pack(anchor="w", padx=16, pady=(12, 0))
        v = kit.label(c, "–", 18, T.TEXT, True)
        v.pack(anchor="w", padx=16, pady=(0, 12))
        return v

    # ------------------------------------------------------------ Daten
    def on_show(self):
        self.refresh()
        self.every(2000, self.refresh)

    def refresh(self):
        if self.busy:
            return
        self.busy = True

        def work():
            return self.sampler.snapshot()

        def done(res):
            self.busy = False
            if isinstance(res, list):
                self.rows = {r["pid"]: r for r in res}
                self.apply()
        self.app.bg(work, done)

    def sort_by(self, key):
        self.sort_rev = not self.sort_rev if key == self.sort_key else key in ("cpu", "ram")
        self.sort_key = key
        self.apply()

    def apply(self):
        if not self.built:
            return
        q = self.search.get().strip().lower()
        flt = self.filter.get()
        rows = list(self.rows.values())
        if q:
            rows = [r for r in rows if q in r["name"].lower() or q in str(r["pid"])]
        if flt == "Hohe Last":
            rows = [r for r in rows if r["cpu"] >= 2.0 or r["ram"] >= 500 * 1048576]
        elif flt == "Fortnite":
            rows = [r for r in rows if r["name"].lower() == FORTNITE_EXE.lower() or "fortnite" in r["name"].lower() or "epic" in r["name"].lower()]
        key = self.sort_key
        rows.sort(key=lambda r: (r["name"].lower() if key == "name" else r[key]), reverse=self.sort_rev)
        rows = rows[:400]
        want = [f"p{r['pid']}" for r in rows]
        have = set(self.tree.get_children())
        for iid in have - set(want):
            self.tree.delete(iid)
        for r in rows:
            iid = f"p{r['pid']}"
            vals = (r["name"], r["pid"], f"{r['cpu']:.1f} %", procs.fmt_ram(r["ram"]), r["prio"], r["status"])
            tags = ("prot",) if r["protected"] else (("fn",) if "fortnite" in r["name"].lower() else (("hot",) if r["cpu"] >= 15 else ()))
            if iid in have:
                self.tree.item(iid, values=vals, tags=tags)
            else:
                self.tree.insert("", "end", iid=iid, values=vals, tags=tags)
        if list(self.tree.get_children()) != want:
            for i, iid in enumerate(want):
                self.tree.move(iid, "", i)
        allrows = list(self.rows.values())
        self.t_count.configure(text=str(len(allrows)))
        d = self.app.monitor.latest
        self.t_cpu.configure(text=f"{d.get('cpu', 0):.0f} %")
        self.t_ram.configure(text=f"{d.get('ram', 0):.0f} %")
        if allrows:
            top = max(allrows, key=lambda r: r["cpu"])
            self.t_top.configure(text=f"{top['name'][:22]} · {top['cpu']:.0f} %")
        self.show_selected(refresh_only=True)

    def selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.rows.get(int(sel[0][1:]))

    def show_selected(self, refresh_only=False):
        r = self.selected()
        if not r:
            if not refresh_only:
                self.sel_name.configure(text="Kein Prozess gewählt")
                self.sel_info.configure(text="Wähle links einen Prozess.")
            return
        self.sel_name.configure(text=r["name"])
        self.sel_info.configure(text=f"PID {r['pid']}\nCPU {r['cpu']:.1f} %  ·  RAM {procs.fmt_ram(r['ram'])}\nPriorität {r['prio']}  ·  {r['status']}"
                                     + ("\n\nSystemprozess: geschützt." if r["protected"] else ""))
        self.kill_btn.configure(state="disabled" if r["protected"] else "normal")

    # ------------------------------------------------------------ Aktionen
    def set_prio(self, level):
        r = self.selected()
        if not r:
            self.note.configure(text="Wähle zuerst einen Prozess.", text_color=T.AMBER)
            return
        ok, msg = procs.set_priority(r["pid"], level)
        self.note.configure(text=msg, text_color=T.GREEN if ok else T.RED)
        self.refresh()

    def kill(self):
        r = self.selected()
        if not r:
            self.note.configure(text="Wähle zuerst einen Prozess.", text_color=T.AMBER)
            return
        if not self.app.ask("Prozess beenden?", f"„{r['name']}“ (PID {r['pid']}) beenden?\nNicht gespeicherte Daten gehen verloren.", "Beenden", danger=True):
            return
        ok, msg = procs.terminate(r["pid"])
        self.note.configure(text=msg, text_color=T.GREEN if ok else T.RED)
        self.frame.after(600, self.refresh)
