"""Persistente Daten (Zähler, Highscore, Lautstärken), atomar als JSON geschrieben."""
from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULTS = {
    "stall_count": 0,
    "turkey_highscore": 0,
    "volume": {"music": 0.5, "effects": 0.5},
}


def atomic_write(path: Path, data: bytes):
    """Erst Temp-Datei im selben Verzeichnis, fsync, dann rename und Verzeichnis-fsync."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    dfd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


class Store:
    """Hält den Zustand im Speicher und schreibt verzögert, wenn sich etwas ändert."""

    def __init__(self, path: Path, save_delay_s: float = 2.0, defaults: dict | None = None):
        self.path = Path(path)
        self.save_delay_s = save_delay_s
        self.data = json.loads(json.dumps(defaults or DEFAULTS))  # tiefe Kopie
        self._dirty_since: float | None = None
        self._load()

    def _load(self):
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            log.info("%s existiert noch nicht, nehme Standardwerte", self.path)
            return
        except (OSError, ValueError) as e:
            log.error("%s nicht lesbar (%s), nehme Standardwerte", self.path, e)
            return
        if isinstance(loaded, dict):
            _merge(self.data, loaded)

    def get(self, *keys):
        v = self.data
        for k in keys:
            v = v[k]
        return v

    def set(self, *keys_and_value):
        *keys, value = keys_and_value
        d = self.data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        if d.get(keys[-1]) != value:
            d[keys[-1]] = value
            if self._dirty_since is None:
                self._dirty_since = time.monotonic()

    def tick(self, now: float | None = None):
        """Regelmäßig aufrufen; schreibt, wenn die Verzögerung abgelaufen ist."""
        now = time.monotonic() if now is None else now
        if self._dirty_since is not None and now - self._dirty_since >= self.save_delay_s:
            self.flush()

    def flush(self):
        if self._dirty_since is None:
            return
        try:
            atomic_write(self.path, json.dumps(self.data, indent=2).encode())
            self._dirty_since = None
        except OSError as e:
            log.error("Speichern nach %s fehlgeschlagen: %s", self.path, e)
            self._dirty_since = time.monotonic()  # später erneut versuchen


def _merge(dst: dict, src: dict):
    """Übernimmt nur bekannte Schlüssel mit passendem Typ."""
    for k, v in src.items():
        if k not in dst:
            continue
        if isinstance(dst[k], dict) and isinstance(v, dict):
            _merge(dst[k], v)
        elif type(dst[k]) is type(v) or isinstance(dst[k], float) and isinstance(v, int):
            dst[k] = v
