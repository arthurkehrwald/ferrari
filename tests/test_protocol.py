import pytest

from ferrari import protocol as p


@pytest.mark.parametrize("line,msg", [
    ("HELLO pico 1", p.Hello("pico", 1)),
    ("READY", p.Ready()),
    ("ERR CFG: kaputt", p.Error("CFG: kaputt")),
    ("B 3 1", p.Digital(3, True)),
    ("B 0 0\r", p.Digital(0, False)),
    ("E 1 -4", p.Encoder(1, -4)),
    ("A 0 4095", p.Analog(0, 4095)),
    ("S 0101 12 4000", p.Snapshot((False, True, False, True), (12, 4000))),
    ("S -", p.Snapshot((), ())),
    ("R 1F0A", p.RelayState(0x1F0A)),
    ("T", p.RelayTimeout()),
])
def test_parse(line, msg):
    assert p.parse(line) == msg


@pytest.mark.parametrize("line", ["", "B 1 2", "E x 1", "R 123", "S 012", "Traceback (most", "READY 1"])
def test_parse_rejects(line):
    with pytest.raises(p.ParseError):
        p.parse(line)


def test_encode():
    assert p.relay_set(0x1005) == b"R 1005\n"
    assert p.relay_keep(1 << 12) == b"K 1000\n"
    assert p.pico_config({"a": [1, 2]}) == b'CFG {"a":[1,2]}\n'
    assert p.pico_leds(b"\x01\xff") == b"L 01ff\n"
    with pytest.raises(ValueError):
        p.relay_set(0x10000)


def test_fan_bits():
    ch = (3, 4, 5)
    assert p.fan_bits(ch, 0) == 0
    assert p.fan_bits(ch, 1) == 1 << 3
    assert p.fan_bits(ch, 2) == 1 << 3 | 1 << 4
    assert p.fan_bits(ch, 3) == 1 << 3 | 1 << 4 | 1 << 5
    with pytest.raises(ValueError):
        p.fan_bits(ch, 4)
