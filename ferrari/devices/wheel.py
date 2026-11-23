"""Thrustmaster T80 (044f:b668) direkt über hidraw.

Report-Aufbau (Report-ID 1, 64 Byte), durch Ausprobieren ermittelt:
    Byte 5 unteres Nibble   D-Pad (0..7 im Uhrzeigersinn ab oben, 8 = Mitte)
    Byte 5 oberes Nibble + Byte 6, 7: Tasten-Bits
    Byte 43-44  Lenkung (16 Bit LE)
    Byte 45-46  Gas    (16 Bit LE, 65535 = losgelassen)
    Byte 47-48  Bremse (16 Bit LE, 65535 = losgelassen)
"""
from __future__ import annotations

import logging
import os
import queue
import select
import threading
from dataclasses import dataclass

from ..config import WheelConfig
from . import Connected, Lost, WheelButton

log = logging.getLogger("ferrari.wheel")

RETRY_S = 1.0
DPAD_CENTER = 8


@dataclass(frozen=True)
class WheelState:
    steer: float = 0.0      # -1 (links) .. 1 (rechts)
    throttle: float = 0.0   # 0..1
    brake: float = 0.0      # 0..1
    dpad: int = DPAD_CENTER
    buttons: frozenset[int] = frozenset()


def parse_report(rep: bytes, deadzone: float = 0.0) -> WheelState | None:
    if len(rep) < 49 or rep[0] != 1:
        return None
    steer = rep[43] | rep[44] << 8
    thr = 1 - (rep[45] | rep[46] << 8) / 65535
    brk = 1 - (rep[47] | rep[48] << 8) / 65535
    btns = set()
    for bi, b in enumerate(range(5, 8)):
        for bit in range(8):
            if bi == 0 and bit < 4:
                continue  # D-Pad
            if rep[b] >> bit & 1:
                btns.add(bi * 8 + bit - 4)
    return WheelState(
        steer=max(-1.0, min(1.0, (steer - 32767.5) / 32767.5)),
        throttle=0.0 if thr < deadzone else thr,
        brake=0.0 if brk < deadzone else brk,
        dpad=rep[5] & 0x0F,
        buttons=frozenset(btns),
    )


class Wheel(threading.Thread):
    name_ = "wheel"

    def __init__(self, cfg: WheelConfig, events: queue.Queue):
        super().__init__(name=self.name_, daemon=True)
        self.cfg = cfg
        self.events = events
        self.state = WheelState()   # wird atomar ersetzt, vom Hauptthread lesbar
        self.connected = False
        self._quit = threading.Event()

    def stop(self):
        self._quit.set()

    def run(self):
        warned = False
        while not self._quit.is_set():
            try:
                fd = os.open(self.cfg.device, os.O_RDONLY | os.O_NONBLOCK)
            except OSError as e:
                if not warned:
                    log.warning("%s nicht verfügbar (%s), versuche es weiter", self.cfg.device, e)
                    warned = True
                self._quit.wait(RETRY_S)
                continue
            warned = False
            self.connected = True
            self.events.put(Connected(self.name_))
            reason = "beendet"
            try:
                while not self._quit.is_set():
                    if not select.select([fd], [], [], 0.2)[0]:
                        continue
                    try:
                        rep = os.read(fd, 64)
                    except BlockingIOError:
                        continue
                    st = parse_report(rep, self.cfg.pedal_deadzone)
                    if st is not None:
                        self._update(st)
            except OSError as e:
                reason = f"Gerät getrennt ({e})"
            finally:
                os.close(fd)
            self.connected = False
            self._update(WheelState())  # alles losgelassen
            self.events.put(Lost(self.name_, reason))
            log.warning("Verbindung beendet: %s", reason)
            self._quit.wait(RETRY_S)

    def _update(self, st: WheelState):
        old = self.state
        self.state = st
        for b in sorted(st.buttons - old.buttons):
            self.events.put(WheelButton(b, True))
        for b in sorted(old.buttons - st.buttons):
            self.events.put(WheelButton(b, False))
