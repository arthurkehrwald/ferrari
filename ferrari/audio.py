"""Lautstärke der virtuellen PipeWire-Sinks (setup/pipewire/) über pactl.

Wer etwas abspielt (CD, pygame, Motorsound), schickt es per PULSE_SINK=ferrari-music
bzw. ferrari-effects an den passenden Sink. Hier wird nur die Lautstärke gesetzt.
"""
from __future__ import annotations

import logging
import subprocess
import threading

log = logging.getLogger(__name__)


class Mixer:
    """Setzt Lautstärken asynchron; schnelles Drehen erzeugt nur einen pactl-Aufruf pro Sink."""

    def __init__(self, sinks: dict[str, str]):
        self.sinks = sinks
        self._pending: dict[str, float] = {}
        self._cv = threading.Condition()
        self._thread = threading.Thread(target=self._run, name="mixer", daemon=True)
        self._thread.start()

    def set_volume(self, channel: str, volume: float):
        with self._cv:
            self._pending[channel] = max(0.0, min(1.0, volume))
            self._cv.notify()

    def _run(self):
        failed: set[str] = set()
        while True:
            with self._cv:
                while not self._pending:
                    self._cv.wait()
                channel, vol = self._pending.popitem()
            sink = self.sinks[channel]
            try:
                # pactl-Prozent sind kubisch skaliert, also gehörrichtig
                subprocess.run(["pactl", "set-sink-volume", sink, f"{vol * 100:.0f}%"],
                               check=True, capture_output=True, timeout=3)
                failed.discard(sink)
            except (OSError, subprocess.SubprocessError) as e:
                if sink not in failed:
                    err = getattr(e, "stderr", b"") or b""
                    log.error("Lautstärke für %s nicht gesetzt: %s %s", sink, e,
                              err.decode(errors="replace").strip())
                    failed.add(sink)
