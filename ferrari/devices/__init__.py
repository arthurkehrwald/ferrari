"""Eingabe- und Ausgabegeräte. Jedes Gerät läuft in einem eigenen Thread, verbindet sich
nach dem Abstecken selbst neu und legt Ereignisse in eine gemeinsame Queue."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Connected:
    device: str


@dataclass(frozen=True)
class Lost:
    device: str
    reason: str


@dataclass(frozen=True)
class ButtonPressed:
    name: str


@dataclass(frozen=True)
class SwitchChanged:
    name: str
    on: bool


@dataclass(frozen=True)
class EncoderTurned:
    name: str
    steps: int  # Rohschritte (4 pro Raststufe bei üblichen Drehgebern)


@dataclass(frozen=True)
class AnalogChanged:
    name: str
    value: float  # 0..1


@dataclass(frozen=True)
class WheelButton:
    index: int
    pressed: bool
