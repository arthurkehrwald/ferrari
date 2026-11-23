"""Gemeinsame Basis für Pico und Pro Micro: Zeilen über USB-Seriell, Heartbeat, Neuverbinden."""
from __future__ import annotations

import logging
import queue
import threading
import time

import serial

from .. import protocol
from . import Connected, Lost

RETRY_S = 1.0


class SerialLink(threading.Thread):
    name_: str = "serial"

    def __init__(self, device: str, events: queue.Queue, heartbeat_s: float, timeout_s: float):
        super().__init__(name=self.name_, daemon=True)
        self.device = device
        self.events = events
        self.heartbeat_s = heartbeat_s
        self.timeout_s = timeout_s
        self.log = logging.getLogger(f"ferrari.{self.name_}")
        self._port: serial.Serial | None = None
        self._wlock = threading.Lock()
        self._quit = threading.Event()
        self.connected = False

    # --- von Unterklassen zu füllen ---
    def on_open(self):
        pass

    def on_message(self, msg):
        pass

    def on_heartbeat(self):
        pass

    def on_close(self):
        pass

    # --- Schnittstelle ---
    def send(self, data: bytes) -> bool:
        with self._wlock:
            port = self._port
            if port is None:
                return False
            try:
                port.write(data)
                return True
            except (serial.SerialException, OSError) as e:
                self.log.debug("Schreiben fehlgeschlagen: %s", e)
                return False

    def stop(self):
        self._quit.set()

    def emit(self, ev):
        self.events.put(ev)

    # --- Thread ---
    def run(self):
        warned = False
        while not self._quit.is_set():
            try:
                # 1200 Baud würde den Pro Micro in den Bootloader schicken, also nie 1200.
                port = serial.Serial(self.device, 115200, timeout=0.05, write_timeout=0.5,
                                     exclusive=True)
            except (serial.SerialException, OSError) as e:
                if not warned:
                    self.log.warning("%s nicht verfügbar (%s), versuche es weiter", self.device, e)
                    warned = True
                self._quit.wait(RETRY_S)
                continue
            warned = False
            reason = self._session(port)
            self.on_close()
            if self.connected:
                self.connected = False
                self.emit(Lost(self.name_, reason))
            self.log.warning("Verbindung beendet: %s", reason)
            self._quit.wait(RETRY_S)

    def mark_connected(self):
        if not self.connected:
            self.connected = True
            self.emit(Connected(self.name_))

    def _session(self, port: serial.Serial) -> str:
        with self._wlock:
            self._port = port
        buf = bytearray()
        partial = True  # erste Zeile nach dem Öffnen kann abgeschnitten sein
        last_rx = time.monotonic()
        next_hb = 0.0
        try:
            port.reset_input_buffer()
            self.on_open()
            while not self._quit.is_set():
                chunk = port.read(port.in_waiting or 1)
                now = time.monotonic()
                if chunk:
                    last_rx = now
                    buf += chunk
                    if partial and (i := buf.find(b"\n")) >= 0:
                        del buf[: i + 1]
                        partial = False
                    while not partial and (i := buf.find(b"\n")) >= 0:
                        raw, buf = bytes(buf[:i]), buf[i + 1:]
                        self._handle_line(raw)
                    if len(buf) > protocol.MAX_LINE:
                        self.log.warning("Zeile zu lang, verworfen")
                        buf.clear()
                if now >= next_hb:
                    next_hb = now + self.heartbeat_s
                    self.on_heartbeat()
                if now - last_rx > self.timeout_s:
                    return f"{self.timeout_s:.1f} s keine Antwort"
            return "beendet"
        except (serial.SerialException, OSError) as e:
            return f"Gerät getrennt ({e})"
        finally:
            with self._wlock:
                self._port = None
            try:
                port.close()
            except Exception:
                pass

    def _handle_line(self, raw: bytes):
        line = raw.decode("ascii", "replace").strip()
        if not line:
            return
        try:
            msg = protocol.parse(line)
        except protocol.ParseError:
            # MicroPython-Fehlermeldungen o. ä. landen hier, deshalb sichtbar loggen
            self.log.warning("< %s", line)
            return
        self.log.debug("< %s", line)
        self.on_message(msg)
