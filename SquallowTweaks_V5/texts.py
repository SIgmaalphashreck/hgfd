"""SquallowTweaks - kurze, lesbare Texte fuer die Tweak-Kacheln.

Jeder Eintrag: id -> (Gruppe, Wirkung, Kurzbeschreibung).
Wirkung ist eine ehrliche Einschaetzung (Stark/Mittel/Klein/Unsicher), keine Garantie.
Die langen Erklaerungen (description/impact) stehen im Info-Dialog der Kachel.
"""
GROUPS = ["Alle", "FPS", "Latenz", "Netzwerk", "Fortnite", "System"]

TEXTS = {
    # Fortnite (echte Config-Aenderungen)
    "fn_graphics_perf": ("Fortnite", "Stark", "Schatten, Effekte, Post, Laub, GI auf Niedrig. Größter FPS-Hebel."),
    "fn_fps_limit": ("Fortnite", "Mittel", "FPS-Limit 240 für stabile Frametimes am 244-Hz-Monitor."),
    "fn_vsync_off": ("Fortnite", "Mittel", "V-Sync aus: weniger Eingabelatenz."),
    "fn_fullscreen": ("Fortnite", "Mittel", "Echtes Vollbild statt Fenster-Vollbild."),
    "fn_motionblur_off": ("Fortnite", "Klein", "Bewegungsunschärfe aus für klareres Bild."),
    "fn_menu_fps": ("Fortnite", "Klein", "Lobby auf 60 FPS: weniger Wärme und Lärm."),
    # Latenz
    "power_ultimate": ("Latenz", "Mittel", "Ultimative Leistung: CPU bleibt auf hohem Takt."),
    "power_high": ("Latenz", "Mittel", "Höchstleistung-Energieplan aktivieren."),
    "ps_min_cpu": ("Latenz", "Mittel", "CPU taktet im Netzbetrieb nie herunter."),
    "ps_pcie_aspm_off": ("Latenz", "Klein", "GPU-Verbindung ohne Schlafzustände."),
    "ps_usb_suspend_off": ("Latenz", "Klein", "Maus und Tastatur schlafen nie ein."),
    "mouse_accel": ("Latenz", "Klein", "Mausbeschleunigung aus."),
    "keyboard_fast": ("Latenz", "Klein", "Schnellste Tastaturwiederholung."),
    "fso_global": ("Latenz", "Unsicher", "Vollbild-Optimierungen: Exklusiv-Verhalten."),
    "msi_gpu": ("Latenz", "Unsicher", "GPU im MSI-Modus (oft schon aktiv)."),
    # FPS (Windows)
    "game_mode": ("FPS", "Klein", "Windows Game Mode einschalten."),
    "game_dvr": ("FPS", "Klein", "Hintergrundaufnahme (Game DVR) aus."),
    "games_task": ("FPS", "Klein", "Spiele-Scheduler: höhere CPU/GPU-Priorität."),
    "win32_prio": ("FPS", "Unsicher", "Vordergrund-Programme bevorzugen."),
    "power_throttling_off": ("FPS", "Klein", "Windows Power Throttling aus."),
    "bg_apps_off": ("FPS", "Klein", "Hintergrund-Apps abschalten."),
    # Netzwerk
    "nic_power_off": ("Netzwerk", "Mittel", "LAN-Energiesparmodi aus: stabilerer Ping."),
    "nic_intmod_off": ("Netzwerk", "Klein", "LAN-Interrupt-Drosselung aus."),
    "net_throttle_off": ("Netzwerk", "Klein", "Multimedia-Drosselung aus (v. a. Streaming)."),
    "delivery_opt_off": ("Netzwerk", "Klein", "Windows teilt Updates nicht per Internet."),
    # System
    "sticky_keys_off": ("System", "Klein", "Keine Shift-Popups mitten im Spiel."),
    "gamebar_nexus": ("System", "Klein", "Controller öffnet nicht die Game Bar."),
    "visualfx": ("System", "Klein", "Visuelle Effekte auf Beste Leistung."),
    "transparency_off": ("System", "Klein", "Transparenzeffekte aus."),
    "window_anim_off": ("System", "Klein", "Fensteranimationen aus."),
    "telemetry_policy": ("System", "Klein", "Telemetrie auf Minimum (Richtlinie)."),
    "diagtrack_off": ("System", "Klein", "Telemetrie-Dienst deaktivieren."),
}

HIDDEN_KINDS = ("info", "action")   # erscheinen nicht als Kachel auf der Tweaks-Seite


def short_for(t) -> tuple[str, str, str]:
    """(Gruppe, Wirkung, Kurztext) - mit Fallback fuer unbekannte Tweaks."""
    if t.id in TEXTS:
        return TEXTS[t.id]
    first = t.description.split(".")[0].strip()
    return ("System", "Klein", first[:70] + ("…" if len(first) > 70 else ""))
