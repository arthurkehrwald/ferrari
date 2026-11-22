#!/usr/bin/env python3
"""Live input test for a Thrustmaster T80 (044f:b668) via raw HID.

Shows steering, both pedals, D-pad and every pressed button, live.
Needs read access to the wheel's hidraw node, which is root-only by default:
    sudo setfacl -m u:$USER:r /dev/hidrawN      (the script prints N)

Layout (report ID 1, 64 bytes), found by experiment:
    byte 5 low nibble  D-pad (0-7 = directions clockwise from up, 8 = centred)
    byte 5 high nibble + bytes 6.. : button bits
    bytes 43-44        steering (16-bit little-endian)
    bytes 45-46        throttle (16-bit LE, 65535 = released, towards 0 = pressed)
    bytes 47-48        brake    (16-bit LE, 65535 = released, towards 0 = pressed)
    bytes 8, 9         mirror L2 / R2 as 0 or 255 (they are digital buttons 6 and 7)

Run:  python3 t80_test.py        Quit with Ctrl+C.
"""
import glob
import os
import select
import sys
import time

HAT = {0: "up", 1: "up-right", 2: "right", 3: "down-right",
       4: "down", 5: "down-left", 6: "left", 7: "up-left", 8: "-"}
BUTTON_BYTES = range(5, 8)  # bytes 5-7 hold the button bits; 8 and 9 only mirror L2/R2
STEER_MAX = 65535


def find_node():
    for h in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
        try:
            if "T80" in open(h + "/device/uevent").read():
                return "/dev/" + os.path.basename(h)
        except OSError:
            pass
    sys.exit("T80 not found. Is it plugged in?")


def bar(frac, width=24):
    n = max(0, min(width, round(frac * width)))
    return "#" * n + "." * (width - n)


def pressed_buttons(rep):
    """Return sorted bit numbers set in the button area (hat nibble excluded)."""
    out = []
    for bi, b in enumerate(BUTTON_BYTES):
        for bit in range(8):
            if bi == 0 and bit < 4:
                continue  # low nibble of byte 5 is the D-pad
            if rep[b] >> bit & 1:
                out.append(bi * 8 + bit - 4)
    return out


def main():
    node = find_node()
    try:
        fd = os.open(node, os.O_RDONLY | os.O_NONBLOCK)
    except PermissionError:
        sys.exit(f"No read access to {node}. Run:  sudo setfacl -m u:$USER:r {node}")
    print(f"Reading {node}. Ctrl+C to quit.\n")
    seen = set()
    try:
        while True:
            if not select.select([fd], [], [], 0.5)[0]:
                continue
            try:
                rep = os.read(fd, 64)
            except BlockingIOError:
                continue
            if len(rep) < 48 or rep[0] != 1:
                continue
            steer = rep[43] | rep[44] << 8
            thr = 65535 - (rep[45] | rep[46] << 8)
            brk = 65535 - (rep[47] | rep[48] << 8)
            btns = pressed_buttons(rep)
            seen.update(btns)
            line = (f"steer {steer:5d} [{bar(steer / STEER_MAX)}]  "
                    f"throttle {thr:5d} [{bar(thr / 65535, 10)}]  "
                    f"brake {brk:5d} [{bar(brk / 65535, 10)}]  "
                    f"dpad {HAT.get(rep[5] & 0x0f, '?'):<10} "
                    f"buttons {btns if btns else '-'}")
            print("\r\x1b[K" + line, end="", flush=True)
    except KeyboardInterrupt:
        print(f"\n\nButtons seen this session: {sorted(seen) or 'none'}")


if __name__ == "__main__":
    main()
