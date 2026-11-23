from ferrari.devices.wheel import parse_report


def report(steer=32768, thr=65535, brk=65535, b5=0x08, b6=0, b7=0):
    rep = bytearray(64)
    rep[0] = 1
    rep[5], rep[6], rep[7] = b5, b6, b7
    rep[43:45] = steer.to_bytes(2, "little")
    rep[45:47] = thr.to_bytes(2, "little")
    rep[47:49] = brk.to_bytes(2, "little")
    return bytes(rep)


def test_released():
    st = parse_report(report())
    assert abs(st.steer) < 0.01 and st.throttle == 0 and st.brake == 0
    assert st.dpad == 8 and not st.buttons


def test_full_and_buttons():
    st = parse_report(report(steer=0, thr=0, brk=32767, b5=0x12, b6=0x01))
    assert st.steer == -1
    assert st.throttle == 1
    assert 0.49 < st.brake < 0.51
    assert st.dpad == 2
    assert st.buttons == {0, 4}


def test_deadzone():
    st = parse_report(report(thr=65535 - 500), deadzone=0.03)
    assert st.throttle == 0


def test_wrong_report():
    assert parse_report(b"\x02" + bytes(63)) is None
    assert parse_report(b"\x01") is None
