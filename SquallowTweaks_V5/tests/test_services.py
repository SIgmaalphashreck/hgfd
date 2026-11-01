import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bench  # noqa: E402
import cleaner  # noqa: E402
import monitor  # noqa: E402
import paths  # noqa: E402
import procs  # noqa: E402
import texts  # noqa: E402
import tweaklib as tl  # noqa: E402


class MonitorParse(unittest.TestCase):
    def test_gpu_csv(self):
        g = monitor.parse_gpu_csv("NVIDIA GeForce RTX 5060 Ti, 12, 644, 8151, 39, 24.14, 2580, 14201\n")
        self.assertTrue(g["available"])
        self.assertEqual(g["name"], "NVIDIA GeForce RTX 5060 Ti")
        self.assertEqual(g["usage"], 12.0)
        self.assertEqual(g["mem_total"], 8151.0)
        self.assertEqual(g["clock"], 2580.0)

    def test_gpu_csv_na_values(self):
        g = monitor.parse_gpu_csv("GPU X, 5, 100, 8000, 40, [N/A], [N/A], [N/A]")
        self.assertTrue(g["available"])
        self.assertIsNone(g["power"])
        self.assertFalse(monitor.parse_gpu_csv("")["available"])
        self.assertFalse(monitor.parse_gpu_csv("kaputt")["available"])

    def test_sample_runs(self):
        m = monitor.Monitor()
        d = m.sample()
        for k in ("cpu", "ram", "down", "up", "gpu", "fortnite", "uptime"):
            self.assertIn(k, d)
        self.assertGreaterEqual(d["ram"], 0)


class ProcTests(unittest.TestCase):
    def test_protection(self):
        self.assertTrue(procs.is_protected(4, "System"))
        self.assertTrue(procs.is_protected(1234, "svchost.exe"))
        self.assertTrue(procs.is_protected(1234, "LSASS.EXE"))
        self.assertTrue(procs.is_protected(os.getpid(), "anything"))
        self.assertFalse(procs.is_protected(99999, "discord.exe"))

    def test_terminate_protected_refused(self):
        ok, msg = procs.terminate(os.getpid())
        self.assertFalse(ok)

    def test_snapshot(self):
        s = procs.ProcSampler()
        rows = s.snapshot()
        rows2 = s.snapshot()
        self.assertTrue(rows2)
        me = next(r for r in rows2 if r["pid"] == os.getpid())
        self.assertTrue(me["protected"])
        self.assertIn("name", me)

    def test_fmt(self):
        self.assertEqual(procs.fmt_ram(5 * 1048576), "5 MB")
        self.assertIn("GB", procs.fmt_ram(3 * 1073741824))


class CleanerTests(unittest.TestCase):
    def test_clean_dir_and_size(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.bin").write_bytes(b"x" * 1000)
            (root / "sub").mkdir()
            (root / "sub" / "b.bin").write_bytes(b"y" * 500)
            self.assertEqual(cleaner.dir_size(root), 1500)
            freed, failed = cleaner.clean_dir(root)
            self.assertEqual(freed, 1500)
            self.assertEqual(failed, 0)
            self.assertEqual(list(root.iterdir()), [])
            self.assertTrue(root.exists())  # Ordner selbst bleibt

    def test_fmt_size(self):
        self.assertEqual(cleaner.fmt_size(500), "500 B")
        self.assertEqual(cleaner.fmt_size(1536), "1.5 KB")


class BenchTests(unittest.TestCase):
    def test_store_and_compare(self):
        with tempfile.TemporaryDirectory() as d:
            store = bench.BenchStore(Path(d) / "b.json")
            a = store.add("Vorher", {"avg_fps": 200.0, "low1_fps": 100.0, "low01_fps": 80.0, "p99_ms": 10.0, "stutters": 12})
            b = store.add("Nachher", {"avg_fps": 220.0, "low1_fps": 130.0, "low01_fps": 79.0, "p99_ms": 8.0, "stutters": 12})
            rows = {r["label"]: r for r in bench.compare(a, b)}
            self.assertEqual(rows["Ø FPS"]["verdict"], "besser")
            self.assertAlmostEqual(rows["Ø FPS"]["delta_pct"], 10.0)
            self.assertEqual(rows["99. Perzentil Frametime"]["verdict"], "besser")   # niedriger ist besser
            self.assertAlmostEqual(rows["99. Perzentil Frametime"]["delta_pct"], 20.0)
            self.assertEqual(rows["Ruckler"]["verdict"], "gleich")
            self.assertEqual(rows["0,1 % Low"]["verdict"], "gleich")                   # -1,25 % liegt im Rauschen (< 3 %)
            reloaded = bench.BenchStore(Path(d) / "b.json")
            self.assertEqual(len(reloaded.runs), 2)
            reloaded.delete(a["id"])
            self.assertEqual(len(bench.BenchStore(Path(d) / "b.json").runs), 1)


class TextsTests(unittest.TestCase):
    def test_every_toggle_tweak_has_curated_text(self):
        cat = tl.build_catalog()
        missing = [t.id for t in cat if t.kind in tl.TOGGLE_KINDS and t.id not in texts.TEXTS]
        self.assertEqual(missing, [], f"Kurztext fehlt: {missing}")

    def test_no_stale_text_ids(self):
        ids = {t.id for t in tl.build_catalog()}
        self.assertEqual([k for k in texts.TEXTS if k not in ids], [])

    def test_short_texts_are_short(self):
        for k, (g, e, s) in texts.TEXTS.items():
            self.assertIn(g, texts.GROUPS)
            self.assertIn(e, ("Stark", "Mittel", "Klein", "Unsicher"))
            self.assertLessEqual(len(s), 80, k)


class FakePS:
    """Simuliert PowerShell-Ausgabe fuer Netzwerkkarten-Eigenschaften."""

    def __init__(self):
        self.props = {("Ethernet", "*EEE"): "1", ("Ethernet", "EnableGreenEthernet"): "1",
                      ("Ethernet", "*InterruptModeration"): "1", ("Ethernet", "*SpeedDuplex"): "0"}
        self.sets = []

    def __call__(self, args, timeout=12):
        script = args[-1]
        if "Get-NetAdapter" in script:
            return 0, json.dumps([{"Adapter": a, "Keyword": k, "Value": v} for (a, k), v in self.props.items()])
        if "Set-NetAdapterAdvancedProperty" in script:
            import re
            m = re.search(r"-Name '([^']*)' -RegistryKeyword '([^']*)' -RegistryValue '([^']*)'", script)
            a, k, v = m.groups()
            self.sets.append((a, k, v))
            self.props[(a, k)] = v
            return 0, ""
        return 1, ""


class NicTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ps = FakePS()
        self.engine = tl.TweakEngine(tl.MemoryBackend(), Path(self.tmp.name) / "s.json", runner=self.ps, admin_check=lambda: True)
        self.cat = {t.id: t for t in tl.build_catalog()}

    def tearDown(self):
        self.tmp.cleanup()

    def test_roundtrip_only_existing_keywords(self):
        t = self.cat["nic_power_off"]
        self.assertEqual(self.engine.status(t)[0], tl.STATUS_INACTIVE)
        r = self.engine.apply(t)
        self.assertTrue(r.ok and r.verified, r.message)
        self.assertEqual(self.ps.props[("Ethernet", "*EEE")], "0")
        self.assertEqual(self.ps.props[("Ethernet", "EnableGreenEthernet")], "0")
        self.assertEqual(self.ps.props[("Ethernet", "*SpeedDuplex")], "0")      # Fremde Einstellung unveraendert
        self.assertNotIn(("Ethernet", "GigaLite"), self.ps.props)                # nicht vorhandene wird nicht erfunden
        self.assertEqual(self.engine.status(t)[0], tl.STATUS_ACTIVE)
        u = self.engine.undo(t)
        self.assertTrue(u.ok, u.message)
        self.assertEqual(self.ps.props[("Ethernet", "*EEE")], "1")
        self.assertEqual(self.ps.props[("Ethernet", "EnableGreenEthernet")], "1")

    def test_unavailable(self):
        self.ps.props = {("Ethernet", "*SpeedDuplex"): "0"}
        t = self.cat["nic_intmod_off"]
        self.assertEqual(self.engine.status(t)[0], tl.STATUS_UNKNOWN)
        self.assertFalse(self.engine.apply(t).ok)
        self.assertFalse(self.engine.has_backup(t.id))

    def test_admin_required(self):
        eng = tl.TweakEngine(tl.MemoryBackend(), Path(self.tmp.name) / "s2.json", runner=self.ps, admin_check=lambda: False)
        r = eng.apply(self.cat["nic_power_off"])
        self.assertFalse(r.ok)
        self.assertEqual(self.ps.sets, [])


class PathsTests(unittest.TestCase):
    def test_migration_copies_old_backup(self):
        with tempfile.TemporaryDirectory() as d:
            old = Path(d) / "RisenTweaks"
            old.mkdir()
            (old / "tweak_state.json").write_text('{"game_mode": {}}', encoding="utf-8")
            dest = Path(d) / "SquallowTweaks"
            dest.mkdir()
            prev = os.environ.get("LOCALAPPDATA")
            os.environ["LOCALAPPDATA"] = d
            try:
                moved = paths.migrate_old_data(dest)
            finally:
                if prev is None:
                    del os.environ["LOCALAPPDATA"]
                else:
                    os.environ["LOCALAPPDATA"] = prev
            self.assertEqual(moved, ["tweak_state.json"])
            self.assertEqual(json.loads((dest / "tweak_state.json").read_text()), {"game_mode": {}})
            self.assertTrue((old / "tweak_state.json").exists())     # Original bleibt


if __name__ == "__main__":
    unittest.main(verbosity=2)
