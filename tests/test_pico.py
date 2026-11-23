import queue

from ferrari import config, protocol
from ferrari.devices import ButtonPressed, Connected, EncoderTurned, SwitchChanged
from ferrari.devices.pico import Pico


def make():
    cfg = config.load()
    q = queue.Queue()
    pico = Pico(cfg.pico, q)
    sent = []
    pico.send = lambda data: sent.append(data) or True
    return cfg, pico, q, sent


def drain(q):
    out = []
    while not q.empty():
        out.append(q.get())
    return out


def configure(pico, cfg, inputs="", analog=(0, 0)):
    pico.on_message(protocol.Hello("pico", protocol.PICO_PROTOCOL))
    pico.on_message(protocol.Ready())
    bits = inputs or "0" * len(cfg.pico.digital_inputs)
    pico.on_message(protocol.Snapshot(tuple(c == "1" for c in bits), analog))


def test_handshake_sends_config():
    cfg, pico, q, sent = make()
    pico.on_message(protocol.Hello("pico", protocol.PICO_PROTOCOL))
    assert sent[-1].startswith(b"CFG ")
    pico.on_message(protocol.Ready())
    assert Connected("pico") in drain(q)


def test_stacked_hellos_send_config_once():
    cfg, pico, q, sent = make()
    pico.on_message(protocol.Hello("pico", protocol.PICO_PROTOCOL))
    pico.on_message(protocol.Hello("pico", protocol.PICO_PROTOCOL))
    assert sum(d.startswith(b"CFG ") for d in sent) == 1
    pico.on_message(protocol.Ready())
    # Nach READY bedeutet HELLO: Pico neu gestartet, also neu konfigurieren
    pico.on_message(protocol.Hello("pico", protocol.PICO_PROTOCOL))
    assert sum(d.startswith(b"CFG ") for d in sent) == 2


def test_wrong_firmware_is_not_configured():
    _, pico, _, sent = make()
    pico.on_message(protocol.Hello("pinscape", 3))
    assert not sent


def test_first_snapshot_is_silent_then_events():
    cfg, pico, q, _ = make()
    names = cfg.pico.digital_inputs
    ign = names.index("ignition")
    bits = ["0"] * len(names)
    bits[ign] = "1"   # Zündschloss steht beim Start auf "an": darf nichts auslösen
    configure(pico, cfg, "".join(bits))
    drain(q)
    pico.on_message(protocol.Digital(names.index("play"), True))
    pico.on_message(protocol.Digital(names.index("play"), False))
    pico.on_message(protocol.Digital(ign, False))
    pico.on_message(protocol.Encoder(0, -4))
    assert drain(q) == [ButtonPressed("play"), SwitchChanged("ignition", False),
                        EncoderTurned("music_volume", -4)]


def test_snapshot_catches_missed_change():
    cfg, pico, q, _ = make()
    configure(pico, cfg)
    drain(q)
    bits = ["0"] * len(cfg.pico.digital_inputs)
    bits[cfg.pico.digital_inputs.index("fans")] = "1"
    pico.on_message(protocol.Snapshot(tuple(c == "1" for c in bits), (0, 0)))
    assert drain(q) == [SwitchChanged("fans", True)]


def test_events_before_ready_are_ignored():
    _, pico, q, _ = make()
    pico.on_message(protocol.Digital(0, True))
    assert drain(q) == []
