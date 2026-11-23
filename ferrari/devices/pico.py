"""Pi Pico: Mittelkonsole (Eingänge) und LED-Streifen."""
from __future__ import annotations

import queue
import time

from .. import protocol
from ..config import PicoConfig
from . import AnalogChanged, ButtonPressed, EncoderTurned, SwitchChanged
from .serial_link import SerialLink


CFG_WAIT_S = 1.0


class Pico(SerialLink):
    name_ = "pico"

    def __init__(self, cfg: PicoConfig, events: queue.Queue):
        super().__init__(cfg.device, events, cfg.heartbeat_s, cfg.timeout_s)
        self.cfg = cfg
        self.inputs = cfg.digital_inputs
        self.n_buttons = len(cfg.buttons)
        self.encoders = list(cfg.encoders)
        self.analogs = list(cfg.analog)
        self.outputs = list(cfg.outputs)
        self.configured = False
        self.state: dict[str, bool] = {}       # aktueller Zustand aller Digitaleingänge
        self.analog: dict[str, float] = {}
        self._baseline = False
        self._cfg_sent = 0.0   # monotonic; verhindert mehrfaches CFG auf gestapelte HELLOs
        self._output_state: dict[str, bool] = {n: False for n in self.outputs}

    # --- öffentliche Schnittstelle ---
    def set_output(self, name: str, on: bool):
        self._output_state[name] = on
        if self.configured:
            self.send(protocol.pico_output(self.outputs.index(name), on))

    def send_leds(self, rgb: bytes):
        if self.configured:
            self.send(protocol.pico_leds(rgb))

    # --- SerialLink ---
    def on_open(self):
        self.configured = False
        self._baseline = False
        self._cfg_sent = 0.0
        self.send(protocol.hello_request())

    def on_close(self):
        self.configured = False

    def on_heartbeat(self):
        if self.configured:
            self.send(protocol.pico_heartbeat())
        elif time.monotonic() - self._cfg_sent > CFG_WAIT_S:
            self.send(protocol.hello_request())

    def on_message(self, msg):
        if isinstance(msg, protocol.Hello):
            if msg.device != "pico" or msg.version != protocol.PICO_PROTOCOL:
                self.log.error("Falsche Firmware: %s v%d (erwartet pico v%d)",
                               msg.device, msg.version, protocol.PICO_PROTOCOL)
                return
            if not self.configured and time.monotonic() - self._cfg_sent < CFG_WAIT_S:
                return  # Antwort auf eine frühere Anfrage, CFG ist schon unterwegs
            self.configured = False
            self._baseline = False
            self._cfg_sent = time.monotonic()
            self.send(protocol.pico_config(self.cfg.firmware_config()))
        elif isinstance(msg, protocol.Ready):
            self.configured = True
            for i, name in enumerate(self.outputs):
                self.send(protocol.pico_output(i, self._output_state[name]))
            self.log.info("konfiguriert")
            self.mark_connected()
        elif isinstance(msg, protocol.Error):
            self.log.error("Pico meldet: %s", msg.text)
        elif not self.configured:
            return
        elif isinstance(msg, protocol.Digital):
            if 0 <= msg.index < len(self.inputs):
                self._digital(self.inputs[msg.index], msg.index, msg.on)
        elif isinstance(msg, protocol.Encoder):
            if 0 <= msg.index < len(self.encoders) and msg.delta:
                self.emit(EncoderTurned(self.encoders[msg.index], msg.delta))
        elif isinstance(msg, protocol.Analog):
            if 0 <= msg.index < len(self.analogs):
                self._analog(self.analogs[msg.index], msg.value)
        elif isinstance(msg, protocol.Snapshot):
            self._snapshot(msg)

    # --- intern ---
    def _digital(self, name: str, index: int, on: bool):
        if self.state.get(name) == on:
            return
        self.state[name] = on
        if index < self.n_buttons:
            if on:
                self.emit(ButtonPressed(name))
        else:
            self.emit(SwitchChanged(name, on))

    def _analog(self, name: str, raw: int):
        v = max(0.0, min(1.0, raw / 4095))
        if self.analog.get(name) != v:
            self.analog[name] = v
            self.emit(AnalogChanged(name, v))

    def _snapshot(self, s: protocol.Snapshot):
        if len(s.inputs) != len(self.inputs) or len(s.analog) != len(self.analogs):
            self.log.warning("Snapshot passt nicht zur Konfiguration")
            return
        if not self._baseline:
            # Erster Zustand nach dem Verbinden: still übernehmen. Die Stellung des
            # Zündschlosses beim Start soll nichts auslösen.
            self.state = dict(zip(self.inputs, s.inputs))
            self.analog = {n: max(0.0, min(1.0, v / 4095)) for n, v in zip(self.analogs, s.analog)}
            self._baseline = True
            return
        # Verpasste Änderungen nachholen
        for i, (name, on) in enumerate(zip(self.inputs, s.inputs)):
            self._digital(name, i, on)
        for name, v in zip(self.analogs, s.analog):
            self._analog(name, v)
