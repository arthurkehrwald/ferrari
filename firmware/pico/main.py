# Firmware für den Pi Pico (MicroPython): Mittelkonsole und LED-Streifen.
# Protokoll: docs/protocol.md. Die Pinbelegung kommt per CFG vom Pi (config.yaml).
#
# Aufspielen:  tools/flash_pico.sh
# Ctrl-C über USB (z. B. durch mpremote) stoppt das Programm, damit Updates möglich sind.
import sys
import select
import time
import json
import machine
from machine import Pin, ADC

VERSION = 1
SNAPSHOT_MS = 1000
HELLO_MS = 1000
ADC_MS = 20
MAX_LINE = 4096
ADC_MARGIN = 40  # Rohwerte so nahe an 0 bzw. 4095 gelten als Anschlag

# Quadratur-Tabelle: Index = alter Zustand << 2 | neuer Zustand
_QUAD = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)

ticks = time.ticks_ms
diff = time.ticks_diff


def send(s):
    sys.stdout.write(s + "\n")


class Encoder:
    def __init__(self, a, b):
        self.a = Pin(a, Pin.IN, Pin.PULL_UP)
        self.b = Pin(b, Pin.IN, Pin.PULL_UP)
        self.st = self.a.value() << 1 | self.b.value()
        self.count = 0
        for p in (self.a, self.b):
            p.irq(self._irq, Pin.IRQ_RISING | Pin.IRQ_FALLING, hard=True)

    def _irq(self, _):
        s = self.a.value() << 1 | self.b.value()
        self.count += _QUAD[self.st << 2 | s]
        self.st = s

    def take(self):
        i = machine.disable_irq()
        c = self.count
        self.count = 0
        machine.enable_irq(i)
        return c

    def close(self):
        for p in (self.a, self.b):
            p.irq(handler=None)


class Analog:
    def __init__(self, pin, alpha, deadband):
        self.adc = ADC(Pin(pin))
        self.alpha = alpha
        self.deadband = deadband
        self.ema = self.adc.read_u16() >> 4
        self.sent = self.value()

    def value(self):
        v = (self.ema - ADC_MARGIN) * 4095 // (4095 - 2 * ADC_MARGIN)
        return 0 if v < 0 else 4095 if v > 4095 else int(v)

    def sample(self):
        """Gibt den neuen Wert zurück, wenn er gemeldet werden soll, sonst None."""
        self.ema += self.alpha * ((self.adc.read_u16() >> 4) - self.ema)
        v = self.value()
        if v != self.sent and (abs(v - self.sent) >= self.deadband or v in (0, 4095)):
            self.sent = v
            return v
        return None


class Console:
    def __init__(self, c):
        self.inputs = [Pin(p, Pin.IN, Pin.PULL_UP) for p in c["inputs"]]
        self.stable = [1 - p.value() for p in self.inputs]  # 1 = gedrückt / geschlossen
        self.cand = list(self.stable)
        self.since = [ticks()] * len(self.inputs)
        self.debounce = int(c["debounce_ms"])
        self.encoders = [Encoder(a, b) for a, b in c["encoders"]]
        self.analogs = [Analog(p, float(c["smoothing"]), int(c["deadband"])) for p in c["analog"]]
        self.outputs = [Pin(p, Pin.OUT, value=0) for p in c["outputs"]]
        self.brightness = max(0, min(255, int(c["brightness"])))
        self.timeout = int(c["timeout_ms"])
        self.led_pins = [Pin(p, Pin.OUT, value=0) for p, _ in c["leds"]]
        self.next_adc = ticks()

    def close(self):
        for e in self.encoders:
            e.close()
        for o in self.outputs:
            o.value(0)

    def safe(self):
        """Verbindung zum Pi verloren: Ausgänge und LEDs aus."""
        for o in self.outputs:
            o.value(0)

    def poll(self, now):
        for i, p in enumerate(self.inputs):
            v = 1 - p.value()
            if v != self.cand[i]:
                self.cand[i] = v
                self.since[i] = now
            elif v != self.stable[i] and diff(now, self.since[i]) >= self.debounce:
                self.stable[i] = v
                send("B %d %d" % (i, v))
        for i, e in enumerate(self.encoders):
            c = e.take()
            if c:
                send("E %d %d" % (i, c))
        if diff(now, self.next_adc) >= 0:
            self.next_adc = time.ticks_add(now, ADC_MS)
            for i, a in enumerate(self.analogs):
                v = a.sample()
                if v is not None:
                    send("A %d %d" % (i, v))

    def snapshot(self):
        bits = "".join("1" if v else "0" for v in self.stable) or "-"
        send(" ".join(["S", bits] + [str(a.sent) for a in self.analogs]))

    def command(self, cmd, args):
        if cmd == "O" and len(args) == 2:
            self.outputs[int(args[0])].value(args[1] == "1")
        elif cmd == "L":
            pass  # LED-Ausgabe kommt mit Meilenstein 6
        else:
            send("ERR unbekannt: " + cmd)


def main():
    poll = select.poll()
    poll.register(sys.stdin, select.POLLIN)
    stdin = sys.stdin.buffer
    buf = bytearray()
    console = None
    lost = False
    last_rx = ticks()
    next_hello = ticks()
    next_snap = ticks()
    send("HELLO pico %d" % VERSION)

    while True:
        now = ticks()
        while poll.poll(0):
            ch = stdin.read(1)
            if not ch:
                break
            if ch == b"\n":
                line = bytes(buf).decode().strip()
                buf = bytearray()
                last_rx = now
                if lost:
                    # Pi ist wieder da: neu konfigurieren lassen, damit Ausgänge stimmen
                    lost = False
                    send("HELLO pico %d" % VERSION)
                if not line:
                    continue
                parts = line.split(" ", 1)
                cmd = parts[0]
                if cmd == "?":
                    send("HELLO pico %d" % VERSION)
                elif cmd == "P":
                    pass
                elif cmd == "CFG":
                    if console:
                        console.close()
                        console = None
                    try:
                        console = Console(json.loads(parts[1]))
                        send("READY")
                        console.snapshot()
                        next_snap = time.ticks_add(now, SNAPSHOT_MS)
                    except Exception as e:
                        send("ERR CFG: %r" % e)
                elif console:
                    try:
                        console.command(cmd, parts[1].split() if len(parts) > 1 else [])
                    except Exception as e:
                        send("ERR %s: %r" % (cmd, e))
            elif ch != b"\r":
                if len(buf) < MAX_LINE:
                    buf.extend(ch)

        if console is None:
            if diff(now, next_hello) >= 0:
                next_hello = time.ticks_add(now, HELLO_MS)
                send("HELLO pico %d" % VERSION)
            time.sleep_ms(1)
            continue

        console.poll(now)
        if diff(now, next_snap) >= 0:
            next_snap = time.ticks_add(now, SNAPSHOT_MS)
            console.snapshot()
        if not lost and diff(now, last_rx) > console.timeout:
            lost = True
            console.safe()
        time.sleep_ms(1)


try:
    main()
except KeyboardInterrupt:
    raise
except Exception as e:
    # Absturz: melden und neu starten, statt in der REPL hängen zu bleiben
    try:
        send("ERR Absturz: %r" % e)
        time.sleep(1)
    finally:
        machine.reset()
