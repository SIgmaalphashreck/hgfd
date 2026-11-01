"""UI-Smoke-Test ohne Windows/GUI: customtkinter/tkinter werden durch Mocks ersetzt.
Prueft, dass alle Seiten bauen und die Hauptablaeufe (Schalter, Anwenden, Auto Optimize, Benchmark, Prozesse, Netzwerk)
ohne Exception durchlaufen. Kein visueller Test."""
import os
import sys
import tempfile
import threading
import time
import types
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TMP = tempfile.mkdtemp(prefix="sq_smoke_")
os.environ["LOCALAPPDATA"] = TMP
PENDING = []


class W:
    """Universelles Fake-Widget."""
    def __init__(self, *a, **k):
        self._kw = dict(k)
        self._val = k.get("value", "")

    def after(self, ms, fn=None, *a):
        if fn:
            PENDING.append(fn)
        return "id"

    def after_cancel(self, *a): pass
    def winfo_children(self): return []
    def winfo_ismapped(self): return True
    def winfo_width(self): return 800
    def winfo_height(self): return 600
    def winfo_rootx(self): return 0
    def winfo_rooty(self): return 0
    def winfo_pointerxy(self): return (1, 1)
    def get(self): return self._kw.get("_v", "")
    def set(self, v): self._kw["_v"] = v
    def configure(self, *a, **k): self._kw.update(k)
    cget = lambda self, k: self._kw.get(k)
    def selection(self): return ()
    def get_children(self): return ()
    def wait_window(self, *a): pass
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return MagicMock(name=name)


class Var:
    def __init__(self, value=False, **k): self.v = value
    def get(self): return self.v
    def set(self, v): self.v = v


ctk = types.ModuleType("customtkinter")
for n in ("CTk", "CTkFrame", "CTkLabel", "CTkButton", "CTkEntry", "CTkSwitch", "CTkProgressBar", "CTkSegmentedButton",
          "CTkOptionMenu", "CTkScrollbar", "CTkTextbox", "CTkToplevel", "CTkImage", "CTkFont"):
    setattr(ctk, n, type(n, (W,), {}))
ctk.BooleanVar = Var
ctk.set_appearance_mode = lambda *a: None
sys.modules["customtkinter"] = ctk
tk = types.ModuleType("tkinter")
tk.Frame, tk.Canvas, tk.TclError = type("Frame", (W,), {}), type("Canvas", (W,), {}), Exception
tk.Tcl = lambda: MagicMock()
ttk = types.ModuleType("tkinter.ttk")
ttk.Style = type("Style", (W,), {})
ttk.Treeview = type("Treeview", (W,), {})
tk.ttk = ttk
sys.modules.update({"tkinter": tk, "tkinter.ttk": ttk})

import tweaklib  # noqa: E402
tweaklib.WinRegBackend = tweaklib.MemoryBackend
tweaklib.is_admin = lambda: True
import cleaner  # noqa: E402
sandbox = Path(TMP) / "fake_temp"
sandbox.mkdir()
(sandbox / "junk.bin").write_bytes(b"x" * 4096)
cleaner.targets = lambda: {"Benutzer-Temp": sandbox}
cleaner.empty_recycle = lambda: True
import kit  # noqa: E402
kit.ask = lambda *a, **k: True
kit.tell = lambda *a, **k: None
import main  # noqa: E402

errors = []
def step(name, fn):
    try:
        fn(); print("ok  ", name)
    except Exception as exc:
        import traceback; traceback.print_exc()
        errors.append(name); print("FAIL", name, repr(exc))

def drain(n=300):
    for _ in range(n):
        if not PENDING:
            break
        PENDING.pop(0)()

def settle(seconds=1.5):
    end = time.time() + seconds
    while time.time() < end:
        app._pump()
        time.sleep(0.03)
        drain(20)

app = main.App()
app.engine.runner = lambda args, timeout=12: (1, "n/a")      # kein powercfg/PowerShell
settle(1.0)
step("startseite", lambda: None)
for key in [p[0] for p in main.PAGES]:
    step(f"seite {key}", lambda k=key: (app.show_page(k), settle(0.8)))

tw = app.pages["tweaks"]
step("tweaks: alle kacheln gebaut", lambda: [drain(500), (_ for _ in ()).throw(AssertionError(len(tw.tiles))) if len(tw.tiles) != len(app.toggle_tweaks()) else None])
def tweaks_flow():
    app.show_page("tweaks"); settle(0.5)
    tw.on_switch("game_mode", True)
    tw.on_switch("fn_vsync_off", True)
    assert app.pending == {"game_mode": True, "fn_vsync_off": True}, app.pending
    tw.apply(False); settle(2.0)
    assert app.is_active("game_mode"), app.states.get("game_mode")
    assert app.engine.has_backup("game_mode")
    # Undo per Schalter
    tw.on_switch("game_mode", False); tw.apply(False); settle(2.0)
    assert not app.is_active("game_mode") and not app.engine.has_backup("game_mode")
step("tweaks: anwenden + undo", tweaks_flow)
step("tweaks: filter+suche", lambda: (tw.group.set("Fortnite"), tw.apply_filter(), tw.group.set("Alle"), tw.apply_filter()))
step("tweaks: profil waehlen", lambda: (tw.pick_profile(), settle(2.0)))
def auto_flow():
    app.auto_optimize(); settle(4.0)
    assert not app._busy, "Auto Optimize haengt"
    assert any(app.engine.has_backup(t.id) for t in app.toggle_tweaks()), "nichts angewendet"
    assert not (sandbox / "junk.bin").exists(), "Temp nicht bereinigt"
step("auto optimize", auto_flow)
step("alles zuruecksetzen", lambda: (app.pages["settings"].undo_all(), settle(3.0)))
def fn_flow():
    app.show_page("fortnite"); settle(0.5)
    app.pages["fortnite"].optimize(); settle(0.5)
    app.pages["fortnite"].reset(); settle(0.5)
step("fortnite seite", fn_flow)
def bench_flow():
    import fnmon
    from fnmon import compute_frame_stats
    a = compute_frame_stats([4.0] * 500); b = compute_frame_stats([3.5] * 500)
    app.bench.add("Vorher", a); app.bench.add("Nachher", b)
    app.show_page("benchmark"); app.pages["benchmark"].render_hist(); settle(0.3)
    app.pages["benchmark"].start()   # ohne PresentMon -> Hinweis
step("benchmark", bench_flow)
def proc_flow():
    app.show_page("processes"); settle(1.5)
    p = app.pages["processes"]
    assert p.rows, "keine Prozesse"
    p.sort_by("name"); p.sort_by("ram")
step("prozesse", proc_flow)
def net_flow():
    app.show_page("network"); settle(0.5)
    n = app.pages["network"]
    n.toggle(); settle(1.0); n.toggle()
    n.epic(); settle(0.5)
step("netzwerk", net_flow)
step("cleanup seite", lambda: (app.show_page("cleanup"), settle(1.0), app.pages["cleanup"].clean_all(), settle(1.0)))
step("dashboard checks", lambda: (app.show_page("dashboard"), settle(2.5)))
app.on_close()
log = (main.paths.LOG_FILE.read_text(encoding="utf-8") if main.paths.LOG_FILE.exists() else "")
bad = [l for l in log.splitlines() if "ui-callback" in l or "bg:" in l or "state-cb" in l or "monitor:" in l]
print("LOG-FEHLER:", bad[:8])
print("ERRORS:", errors)
sys.exit(1 if (errors or bad) else 0)
