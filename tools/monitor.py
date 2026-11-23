"""Live-Anzeige aller Eingänge und Relais-Test. Ersetzt t80_test.py.

    .venv/bin/python -m tools.monitor [--config PFAD]

Tasten: 0-9, a-f  Relais-Kanal umschalten   x  alle Relais aus   q  beenden
Der Dienst muss dafür gestoppt sein (systemctl --user stop ferrari), weil die
seriellen Schnittstellen exklusiv geöffnet werden.
"""
from __future__ import annotations

import argparse
import curses
import logging
import queue
import time
from collections import deque

from ferrari import config as config_mod
from ferrari import devices as ev
from ferrari.devices.pico import Pico
from ferrari.devices.relay import Relay
from ferrari.devices.wheel import DPAD_CENTER, Wheel

DPAD = {0: "hoch", 1: "hoch-rechts", 2: "rechts", 3: "runter-rechts", 4: "runter",
        5: "runter-links", 6: "links", 7: "hoch-links", DPAD_CENTER: "-"}


class ListHandler(logging.Handler):
    def __init__(self, sink: deque):
        super().__init__()
        self.sink = sink

    def emit(self, record):
        self.sink.append(f"{record.levelname[0]} {record.name}: {record.getMessage()}")


def bar(frac: float, width: int) -> str:
    n = max(0, min(width, round(frac * width)))
    return "#" * n + "." * (width - n)


def run(scr, cfg):
    curses.curs_set(0)
    scr.nodelay(True)
    log_lines: deque[str] = deque(maxlen=200)
    logging.getLogger().addHandler(ListHandler(log_lines))
    logging.getLogger().setLevel(logging.INFO)

    events: queue.Queue = queue.Queue()
    wheel, pico, relay = Wheel(cfg.wheel, events), Pico(cfg.pico, events), Relay(cfg.relay, events)
    for t in (wheel, pico, relay):
        t.start()
    enc_total = {n: 0 for n in cfg.pico.encoders}
    wheel_seen: set[int] = set()
    ignition_count = 0

    try:
        while True:
            while True:
                try:
                    e = events.get_nowait()
                except queue.Empty:
                    break
                if isinstance(e, ev.EncoderTurned):
                    enc_total[e.name] += e.steps
                elif isinstance(e, ev.WheelButton) and e.pressed:
                    wheel_seen.add(e.index)
                if isinstance(e, ev.SwitchChanged) and e.name == "ignition":
                    ignition_count += 1
                if not isinstance(e, ev.AnalogChanged):
                    log_lines.append(str(e))

            k = scr.getch()
            if k in (ord("q"), 27):
                break
            if k == ord("x"):
                relay.set_raw(0)
            elif k != -1 and chr(k) in "0123456789abcdef":
                relay.set_raw(relay.mask ^ (1 << int(chr(k), 16)))

            scr.erase()
            h, w = scr.getmaxyx()
            rows: list[str] = []
            st = wheel.state
            rows.append(f"LENKRAD  {'verbunden' if wheel.connected else 'GETRENNT'}")
            rows.append(f"  Lenkung {st.steer:+.2f} [{bar((st.steer + 1) / 2, 30)}]")
            rows.append(f"  Gas     {st.throttle:4.2f} [{bar(st.throttle, 30)}]")
            rows.append(f"  Bremse  {st.brake:4.2f} [{bar(st.brake, 30)}]")
            rows.append(f"  D-Pad {DPAD.get(st.dpad, '?'):<14} Tasten {sorted(st.buttons) or '-'}"
                        f"   bisher gesehen {sorted(wheel_seen) or '-'}")
            rows.append("")
            rows.append(f"PICO  {'konfiguriert' if pico.configured else 'nicht verbunden'}")
            for n in cfg.pico.buttons:
                rows.append(f"  Taster   {n:<16} {'GEDRÜCKT' if pico.state.get(n) else '-'}")
            for n in cfg.pico.switches:
                extra = f"  ({ignition_count} Wechsel)" if n == "ignition" else ""
                rows.append(f"  Schalter {n:<16} {'AN' if pico.state.get(n) else 'aus'}{extra}")
            for n in cfg.pico.encoders:
                rows.append(f"  Drehgeber {n:<15} {enc_total[n]:+d} Schritte")
            for n in cfg.pico.analog:
                v = pico.analog.get(n, 0.0)
                rows.append(f"  Analog   {n:<16} {v:4.2f} [{bar(v, 30)}]")
            rows.append("")
            act = "?" if relay.actual_mask is None else f"{relay.actual_mask:04X}"
            rows.append(f"RELAIS  {'verbunden' if relay.connected else 'nicht verbunden'}"
                        f"   gesetzt {relay.mask:04X}  bestätigt {act}")
            rows.append("  " + " ".join(f"{c:X}:{'#' if relay.mask >> c & 1 else '.'}"
                                        for c in range(16)))
            rows.append("")
            rows.append("0-9/a-f Relais umschalten   x alle aus   q beenden")
            rows.append("-" * min(w - 1, 78))
            free = h - len(rows) - 1
            rows += list(log_lines)[-free:] if free > 0 else []
            for y, line in enumerate(rows[: h - 1]):
                scr.addnstr(y, 0, line, w - 1)
            scr.refresh()
            time.sleep(0.03)
    finally:
        relay.set_raw(0)
        time.sleep(0.1)
        for t in (wheel, pico, relay):
            t.stop()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=config_mod.DEFAULT_PATH)
    args = ap.parse_args()
    cfg = config_mod.load(args.config)
    curses.wrapper(run, cfg)


if __name__ == "__main__":
    main()
