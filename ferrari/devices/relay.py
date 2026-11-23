"""Arduino Pro Micro mit 16 Relais (Ventilatoren, Fernseher, später Strobos usw.)."""
from __future__ import annotations

import queue
import threading

from .. import protocol
from ..config import RelayConfig
from .serial_link import SerialLink


class Relay(SerialLink):
    name_ = "relay"

    def __init__(self, cfg: RelayConfig, events: queue.Queue):
        super().__init__(cfg.device, events, cfg.heartbeat_s, cfg.timeout_s)
        self.cfg = cfg
        self._lock = threading.Lock()
        self._mask = 0
        self.actual_mask: int | None = None   # was die Firmware zuletzt bestätigt hat
        self._fan_stages = [0] * len(cfg.fans)
        self._tv = False
        self._ready = False   # erst nach HELLO der richtigen Firmware senden

    # --- öffentliche Schnittstelle ---
    def set_fan(self, index: int, stage: int):
        with self._lock:
            self._fan_stages[index] = stage
            self._update()

    def set_tv(self, on: bool):
        with self._lock:
            self._tv = on
            self._update()

    def set_raw(self, mask: int):
        """Nur für Tests (tools/monitor.py): setzt die Maske direkt."""
        with self._lock:
            self._mask = mask
        if self._ready:
            self.send(protocol.relay_set(mask))

    @property
    def mask(self) -> int:
        return self._mask

    # --- intern ---
    def _update(self):
        m = 0
        for chans, stage in zip(self.cfg.fans, self._fan_stages):
            m |= protocol.fan_bits(chans, stage)
        if self._tv:
            m |= 1 << self.cfg.tv
        if m != self._mask:
            self._mask = m
            if self._ready:
                self.send(protocol.relay_set(m))

    # --- SerialLink ---
    def on_open(self):
        self.actual_mask = None
        self._ready = False
        self.send(protocol.hello_request())

    def on_close(self):
        self._ready = False

    def on_heartbeat(self):
        if self._ready:
            # Die Maske dient gleichzeitig als Heartbeat
            self.send(protocol.relay_set(self._mask))
        else:
            self.send(protocol.hello_request())

    def on_message(self, msg):
        if isinstance(msg, protocol.Hello):
            if msg.device != "relay" or msg.version != protocol.RELAY_PROTOCOL:
                self.log.error("Falsche Firmware: %s v%d (erwartet relay v%d)",
                               msg.device, msg.version, protocol.RELAY_PROTOCOL)
                return
            self._ready = True
            self.send(protocol.relay_keep(self.cfg.keep_mask))
            self.send(protocol.relay_set(self._mask))
            self.mark_connected()
        elif isinstance(msg, protocol.RelayState):
            self.actual_mask = msg.mask
        elif isinstance(msg, protocol.RelayTimeout):
            self.log.warning("Firmware meldet Timeout, Relais wurden abgeschaltet")
