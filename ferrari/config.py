"""Lädt config.yaml in typisierte Dataclasses und prüft sie.

Fehler werden gesammelt und mit Pfad gemeldet, z. B.
    pico.buttons.nitro: GP29 ist kein nutzbarer Pin
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

# Auf dem Pico-Board herausgeführte GPIOs. GP23..25 und GP29 sind intern belegt.
PICO_PINS = set(range(0, 23)) | {26, 27, 28}
PICO_ADC_PINS = {26, 27, 28}
RELAY_CHANNELS = 16


class ConfigError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("Fehler in der Konfiguration:\n  " + "\n  ".join(errors))
        self.errors = errors


@dataclass
class PersistConfig:
    path: Path
    save_delay_s: float


@dataclass
class WheelConfig:
    device: str
    pedal_deadzone: float


@dataclass
class LedLine:
    pin: int
    count: int


@dataclass
class PicoConfig:
    device: str
    heartbeat_s: float
    timeout_s: float
    debounce_ms: int
    analog_smoothing: float
    analog_deadband: int
    buttons: dict[str, int]
    switches: dict[str, int]
    encoders: dict[str, tuple[int, int]]
    analog: dict[str, int]
    outputs: dict[str, int]
    led_lines: list[LedLine]
    max_brightness: float

    @property
    def digital_inputs(self) -> list[str]:
        """Reihenfolge der Digitaleingänge im Protokoll (Index = Position)."""
        return list(self.buttons) + list(self.switches)

    def firmware_config(self) -> dict:
        """Das, was per CFG an den Pico geht (nur Pins und Zahlen, keine Namen)."""
        return {
            "inputs": [self.buttons.get(n, self.switches.get(n)) for n in self.digital_inputs],
            "encoders": [list(p) for p in self.encoders.values()],
            "analog": list(self.analog.values()),
            "outputs": list(self.outputs.values()),
            "leds": [[l.pin, l.count] for l in self.led_lines],
            "brightness": round(self.max_brightness * 255),
            "debounce_ms": self.debounce_ms,
            "smoothing": self.analog_smoothing,
            "deadband": self.analog_deadband,
            "timeout_ms": round(self.timeout_s * 1000),
        }


@dataclass
class RelayConfig:
    device: str
    heartbeat_s: float
    timeout_s: float
    fans: list[tuple[int, int, int]]
    tv: int
    keep_on_timeout: list[str]

    def channels_of(self, name: str) -> list[int]:
        if name == "tv":
            return [self.tv]
        if name.startswith("fan") and name[3:].isdigit():
            return list(self.fans[int(name[3:]) - 1])
        raise KeyError(name)

    @property
    def keep_mask(self) -> int:
        mask = 0
        for name in self.keep_on_timeout:
            for ch in self.channels_of(name):
                mask |= 1 << ch
        return mask


@dataclass
class AudioConfig:
    sinks: dict[str, str]
    volume_step: float
    encoder_steps_per_detent: int
    default_volume: dict[str, float]


@dataclass
class Config:
    persist: PersistConfig
    wheel: WheelConfig
    pico: PicoConfig
    relay: RelayConfig
    audio: AudioConfig
    source: Path | None = field(default=None, compare=False)


# --- Hilfsfunktionen zum Lesen mit Fehlersammlung ---------------------------------------

_MISSING = object()


class _Reader:
    def __init__(self):
        self.errors: list[str] = []

    def err(self, path: str, msg: str):
        self.errors.append(f"{path}: {msg}")

    def get(self, d, key: str, path: str, typ, default=_MISSING):
        p = f"{path}.{key}" if path else key
        if not isinstance(d, dict):
            return None
        if key not in d:
            if default is _MISSING:
                self.err(p, "fehlt")
                return None
            return default
        v = d[key]
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if typ is not None and not isinstance(v, typ) or isinstance(v, bool) and typ is not bool:
            self.err(p, f"erwartet {getattr(typ, '__name__', typ)}, ist {v!r}")
            return None
        return v

    def num(self, d, key, path, typ=float, lo=None, hi=None, default=_MISSING):
        v = self.get(d, key, path, typ, default)
        if v is None:
            return None
        if lo is not None and v < lo or hi is not None and v > hi:
            self.err(f"{path}.{key}", f"{v} liegt nicht in [{lo}, {hi}]")
        return v

    def pin(self, v, path, adc=False):
        if isinstance(v, str) and v.upper().startswith("GP") and v[2:].isdigit():
            n = int(v[2:])
        elif isinstance(v, int) and not isinstance(v, bool):
            n = v
        else:
            self.err(path, f"{v!r} ist kein Pin (Format: GP0)")
            return None
        if n not in PICO_PINS:
            self.err(path, f"GP{n} ist kein nutzbarer Pin")
        elif adc and n not in PICO_ADC_PINS:
            self.err(path, f"GP{n} hat keinen ADC (nur GP26..GP28)")
        return n

    def pin_map(self, d, key, path, adc=False, pairs=False, default=_MISSING):
        m = self.get(d, key, path, dict, default)
        out = {}
        for name, v in (m or {}).items():
            p = f"{path}.{key}.{name}"
            if pairs:
                if not (isinstance(v, list) and len(v) == 2):
                    self.err(p, "erwartet [A, B]")
                    continue
                out[name] = (self.pin(v[0], p + "[0]"), self.pin(v[1], p + "[1]"))
            else:
                out[name] = self.pin(v, p, adc)
        return out


def _parse(raw: dict) -> Config:
    r = _Reader()
    if not isinstance(raw, dict):
        raise ConfigError(["Datei ist leer oder kein YAML-Mapping"])

    s = r.get(raw, "persist", "", dict) or {}
    persist = PersistConfig(
        path=Path(r.get(s, "path", "persist", str) or "."),
        save_delay_s=r.num(s, "save_delay_s", "persist", lo=0),
    )

    s = r.get(raw, "wheel", "", dict) or {}
    wheel = WheelConfig(
        device=r.get(s, "device", "wheel", str),
        pedal_deadzone=r.num(s, "pedal_deadzone", "wheel", lo=0, hi=0.5),
    )

    s = r.get(raw, "pico", "", dict) or {}
    leds = r.get(s, "leds", "pico", dict) or {}
    lines = []
    for i, ln in enumerate(r.get(leds, "lines", "pico.leds", list) or []):
        p = f"pico.leds.lines[{i}]"
        if not isinstance(ln, dict):
            r.err(p, "erwartet {pin, count}")
            continue
        lines.append(LedLine(r.pin(ln.get("pin"), p + ".pin"),
                             r.num(ln, "count", p, int, lo=1, hi=1000)))
    pico = PicoConfig(
        device=r.get(s, "device", "pico", str),
        heartbeat_s=r.num(s, "heartbeat_s", "pico", lo=0.01),
        timeout_s=r.num(s, "timeout_s", "pico", lo=0.1),
        debounce_ms=r.num(s, "debounce_ms", "pico", int, lo=0, hi=500),
        analog_smoothing=r.num(s, "analog_smoothing", "pico", lo=0.01, hi=1),
        analog_deadband=r.num(s, "analog_deadband", "pico", int, lo=0, hi=4095),
        buttons=r.pin_map(s, "buttons", "pico", default={}),
        switches=r.pin_map(s, "switches", "pico", default={}),
        encoders=r.pin_map(s, "encoders", "pico", pairs=True, default={}),
        analog=r.pin_map(s, "analog", "pico", adc=True, default={}),
        outputs=r.pin_map(s, "outputs", "pico", default={}),
        led_lines=lines,
        max_brightness=r.num(leds, "max_brightness", "pico.leds", lo=0, hi=1),
    )
    if pico.heartbeat_s and pico.timeout_s and pico.heartbeat_s * 2 > pico.timeout_s:
        r.err("pico.heartbeat_s", "muss höchstens halb so groß sein wie timeout_s")
    # Doppelt belegte Pins und Namen
    used: dict[int, str] = {}
    names: set[str] = set()
    for sect in ("buttons", "switches", "encoders", "analog", "outputs"):
        for name, v in getattr(pico, sect).items():
            if name in names:
                r.err(f"pico.{sect}.{name}", "Name ist schon vergeben")
            names.add(name)
            for n in v if isinstance(v, tuple) else (v,):
                if n is not None:
                    if n in used:
                        r.err(f"pico.{sect}.{name}", f"GP{n} ist schon belegt durch {used[n]}")
                    used[n] = f"{sect}.{name}"
    for i, ln in enumerate(pico.led_lines):
        if ln.pin in used:
            r.err(f"pico.leds.lines[{i}]", f"GP{ln.pin} ist schon belegt durch {used[ln.pin]}")
        used[ln.pin] = f"leds.lines[{i}]"

    s = r.get(raw, "relay", "", dict) or {}
    fans = []
    for i, f in enumerate(r.get(s, "fans", "relay", list) or []):
        if not (isinstance(f, list) and len(f) == 3 and all(isinstance(c, int) for c in f)):
            r.err(f"relay.fans[{i}]", "erwartet drei Kanalnummern")
            continue
        fans.append(tuple(f))
    relay = RelayConfig(
        device=r.get(s, "device", "relay", str),
        heartbeat_s=r.num(s, "heartbeat_s", "relay", lo=0.01),
        timeout_s=r.num(s, "timeout_s", "relay", lo=0.1),
        fans=fans,
        tv=r.num(s, "tv", "relay", int, lo=0, hi=RELAY_CHANNELS - 1),
        keep_on_timeout=r.get(s, "keep_on_timeout", "relay", list, default=[]) or [],
    )
    seen: dict[int, str] = {}
    for name, chans in [(f"fans[{i}]", f) for i, f in enumerate(fans)] + [("tv", (relay.tv,))]:
        for c in chans:
            if c is None:
                continue
            if not 0 <= c < RELAY_CHANNELS:
                r.err(f"relay.{name}", f"Kanal {c} gibt es nicht (0..{RELAY_CHANNELS - 1})")
            elif c in seen:
                r.err(f"relay.{name}", f"Kanal {c} ist schon belegt durch {seen[c]}")
            seen[c] = name
    for name in relay.keep_on_timeout:
        try:
            relay.channels_of(name)
        except (KeyError, IndexError):
            r.err("relay.keep_on_timeout", f"unbekanntes Gerät {name!r} (tv, fan1, ...)")
    if relay.heartbeat_s and relay.heartbeat_s * 2 > 1.0:
        r.err("relay.heartbeat_s", "muss unter 0,5 s liegen (Timeout der Firmware: 1 s)")

    s = r.get(raw, "audio", "", dict) or {}
    sinks = r.get(s, "sinks", "audio", dict) or {}
    vols = r.get(s, "default_volume", "audio", dict) or {}
    for key in ("music", "effects"):
        r.get(sinks, key, "audio.sinks", str)
        r.num(vols, key, "audio.default_volume", lo=0, hi=1)
    audio = AudioConfig(
        sinks=sinks,
        volume_step=r.num(s, "volume_step", "audio", lo=0.001, hi=0.5),
        encoder_steps_per_detent=r.num(s, "encoder_steps_per_detent", "audio", int, lo=1, hi=8),
        default_volume={k: float(v) for k, v in vols.items()
                        if isinstance(v, (int, float)) and not isinstance(v, bool)},
    )

    if r.errors:
        raise ConfigError(r.errors)
    return Config(persist=persist, wheel=wheel, pico=pico, relay=relay, audio=audio)


def load(path: Path | str = DEFAULT_PATH) -> Config:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ConfigError([f"{path}: {e.strerror}"]) from e
    except yaml.YAMLError as e:
        raise ConfigError([f"{path}: {e}"]) from e
    cfg = _parse(raw)
    cfg.source = path
    return cfg
