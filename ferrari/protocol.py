"""Zeilenprotokoll zu Pico und Pro Micro. Beschreibung: docs/protocol.md.

Nur Kodieren und Dekodieren, keine Ein-/Ausgabe.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

PICO_PROTOCOL = 1
RELAY_PROTOCOL = 1
MAX_LINE = 4096


# --- Nachrichten von den Mikrocontrollern ----------------------------------------------

@dataclass(frozen=True)
class Hello:
    device: str
    version: int


@dataclass(frozen=True)
class Ready:
    pass


@dataclass(frozen=True)
class Error:
    text: str


@dataclass(frozen=True)
class Digital:
    index: int
    on: bool


@dataclass(frozen=True)
class Encoder:
    index: int
    delta: int


@dataclass(frozen=True)
class Analog:
    index: int
    value: int  # 0..4095


@dataclass(frozen=True)
class Snapshot:
    inputs: tuple[bool, ...]
    analog: tuple[int, ...]


@dataclass(frozen=True)
class RelayState:
    mask: int


@dataclass(frozen=True)
class RelayTimeout:
    pass


class ParseError(ValueError):
    pass


def parse(line: str):
    """Eine empfangene Zeile (ohne Zeilenende) in eine Nachricht übersetzen."""
    parts = line.strip().split()
    if not parts:
        raise ParseError("leere Zeile")
    cmd, args = parts[0], parts[1:]
    try:
        if cmd == "HELLO" and len(args) == 2:
            return Hello(args[0], int(args[1]))
        if cmd == "READY" and not args:
            return Ready()
        if cmd == "ERR":
            return Error(" ".join(args))
        if cmd == "B" and len(args) == 2 and args[1] in ("0", "1"):
            return Digital(int(args[0]), args[1] == "1")
        if cmd == "E" and len(args) == 2:
            return Encoder(int(args[0]), int(args[1]))
        if cmd == "A" and len(args) == 2:
            return Analog(int(args[0]), int(args[1]))
        if cmd == "S" and len(args) >= 1 and set(args[0]) <= {"0", "1", "-"}:
            bits = "" if args[0] == "-" else args[0]
            return Snapshot(tuple(c == "1" for c in bits), tuple(int(a) for a in args[1:]))
        if cmd == "R" and len(args) == 1 and len(args[0]) == 4:
            return RelayState(int(args[0], 16))
        if cmd == "T" and not args:
            return RelayTimeout()
    except ValueError:
        pass
    raise ParseError(f"unbekannte Nachricht: {line!r}")


# --- Nachrichten an die Mikrocontroller ------------------------------------------------

def _line(s: str) -> bytes:
    return (s + "\n").encode("ascii")


def hello_request() -> bytes:
    return _line("?")


def pico_config(fw_config: dict) -> bytes:
    return _line("CFG " + json.dumps(fw_config, separators=(",", ":")))


def pico_heartbeat() -> bytes:
    return _line("P")


def pico_output(index: int, on: bool) -> bytes:
    return _line(f"O {index} {int(on)}")


def pico_leds(rgb: bytes) -> bytes:
    """Ein ganzer LED-Frame: RGB-Bytes aller Leitungen hintereinander."""
    return _line("L " + rgb.hex())


def relay_set(mask: int) -> bytes:
    if not 0 <= mask <= 0xFFFF:
        raise ValueError(mask)
    return _line(f"R {mask:04X}")


def relay_keep(mask: int) -> bytes:
    if not 0 <= mask <= 0xFFFF:
        raise ValueError(mask)
    return _line(f"K {mask:04X}")


# --- Relais-Logik -----------------------------------------------------------------------

def fan_bits(channels: tuple[int, int, int], stage: int) -> int:
    """Relaismaske für einen Ventilator auf Stufe 0..3.

    Verdrahtung (Relais in Ruhe = Kontakt NC):
      Relais 1: aus | an (weiter zu Relais 2)
      Relais 2: Stufe 1 | weiter zu Relais 3
      Relais 3: Stufe 2 | Stufe 3
    Jede Kombination legt höchstens eine Wicklung an Spannung.
    """
    if not 0 <= stage <= 3:
        raise ValueError(stage)
    on = [stage >= 1, stage >= 2, stage >= 3]
    return sum(1 << ch for ch, b in zip(channels, on) if b)
