"""Einstiegspunkt:  python -m ferrari [--config PFAD] [-v]

Meilenstein 0: Geräte verbinden, Ereignisse protokollieren, Lautstärken über die
Drehgeber steuern und speichern. Die Modi kommen mit den nächsten Meilensteinen.
"""
from __future__ import annotations

import argparse
import logging
import queue
import signal
import sys
import time

from . import config as config_mod
from . import devices as ev
from .audio import Mixer
from .devices.pico import Pico
from .devices.relay import Relay
from .devices.wheel import Wheel
from .persist import DEFAULTS, Store
from .sdnotify import notify

log = logging.getLogger("ferrari")

TICK_S = 1 / 50


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ferrari")
    ap.add_argument("--config", default=config_mod.DEFAULT_PATH)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        # systemd/journald setzt selbst einen Zeitstempel
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        cfg = config_mod.load(args.config)
    except config_mod.ConfigError as e:
        log.error("%s", e)
        return 2

    defaults = dict(DEFAULTS, volume=dict(cfg.audio.default_volume))
    store = Store(cfg.persist.path, cfg.persist.save_delay_s, defaults)
    mixer = Mixer(cfg.audio.sinks)
    for ch in ("music", "effects"):
        mixer.set_volume(ch, store.get("volume", ch))

    events: queue.Queue = queue.Queue()
    wheel = Wheel(cfg.wheel, events)
    pico = Pico(cfg.pico, events)
    relay = Relay(cfg.relay, events)
    threads = [wheel, pico, relay]
    for t in threads:
        t.start()

    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    encoder_rest: dict[str, int] = {}
    volume_of = {"music_volume": "music", "effects_volume": "effects"}

    notify("READY=1")
    log.info("läuft (Konfiguration %s)", cfg.source)
    try:
        while running:
            deadline = time.monotonic() + TICK_S
            while True:
                try:
                    e = events.get(timeout=max(0.0, deadline - time.monotonic()))
                except queue.Empty:
                    break
                if isinstance(e, ev.EncoderTurned) and e.name in volume_of:
                    # Rohschritte zu Raststufen, Rest für die nächste Bewegung merken
                    n = encoder_rest.get(e.name, 0) + e.steps
                    detents = int(n / cfg.audio.encoder_steps_per_detent)
                    encoder_rest[e.name] = n - detents * cfg.audio.encoder_steps_per_detent
                    if detents:
                        ch = volume_of[e.name]
                        vol = round(max(0.0, min(1.0, store.get("volume", ch)
                                                 + detents * cfg.audio.volume_step)), 3)
                        store.set("volume", ch, vol)
                        mixer.set_volume(ch, vol)
                        log.info("Lautstärke %s: %.0f %%", ch, vol * 100)
                elif isinstance(e, ev.SwitchChanged) and e.name == "ignition":
                    log.info("Zündschloss betätigt")
                elif isinstance(e, ev.AnalogChanged):
                    log.debug("%s", e)  # bei offenen Eingängen sehr viele
                else:
                    log.info("%s", e)
            store.tick()
            notify("WATCHDOG=1")
    finally:
        notify("STOPPING=1")
        log.info("beende")
        store.flush()
        for t in threads:
            t.stop()
        for t in threads:
            t.join(timeout=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
