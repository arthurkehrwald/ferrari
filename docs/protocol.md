# Protokoll zu den Mikrocontrollern

Beide Controller hängen per USB-Seriell (CDC) am Pi. Die Baudrate ist bedeutungslos, darf aber
nie 1200 sein: Beim Pro Micro löst das den Bootloader aus.

Jede Nachricht ist eine ASCII-Zeile mit `\n` am Ende (`\r` wird ignoriert). Unbekannte Zeilen
werden ignoriert und auf dem Pi als Warnung protokolliert. So tauchen auch Fehlermeldungen von
MicroPython im Log auf.

Umsetzung: [ferrari/protocol.py](../ferrari/protocol.py), [firmware/pico/main.py](../firmware/pico/main.py),
[firmware/relay/relay.ino](../firmware/relay/relay.ino).

## Pico (Mittelkonsole, LEDs), Protokollversion 1

### Ablauf

1. Der Pi öffnet `/dev/ferrari-pico` und schickt `?`.
2. Der Pico antwortet `HELLO pico 1`. Ohne Konfiguration wiederholt er das jede Sekunde.
3. Der Pi prüft die Version und schickt `CFG {...}`.
4. Der Pico richtet die Pins ein und antwortet `READY`, gefolgt von einem Snapshot `S`.
   Den ersten Snapshot übernimmt der Pi still als Ausgangszustand. Die Stellung des
   Zündschlosses beim Start löst also nichts aus.
5. Danach meldet der Pico Änderungen, jede Sekunde einen Snapshot, und der Pi schickt
   alle 0,25 s `P`.

Schickt der Pico `HELLO`, obwohl er schon konfiguriert war (Neustart, Verbindungsverlust),
konfiguriert der Pi ihn neu.

### Pi → Pico

| Nachricht | Bedeutung |
|---|---|
| `?` | Bitte um `HELLO` |
| `CFG <json>` | Pinbelegung und Parameter, siehe unten |
| `P` | Heartbeat |
| `O <i> 0\|1` | Ausgang `i` schalten (Reihenfolge wie `outputs`) |
| `L <hex>` | LED-Frame: RGB-Bytes aller LEDs, Leitung für Leitung. *Vorläufig, wird mit Meilenstein 6 festgelegt.* |

`CFG` enthält nur Pinnummern und Zahlen. Die Namen kennt nur der Pi, die Indizes in den
Nachrichten entsprechen der Reihenfolge in den Listen:

```json
{"inputs": [0, 1, ...], "encoders": [[11, 12], [13, 14]], "analog": [26, 27],
 "outputs": [28], "leds": [[18, 60], ...], "brightness": 76, "debounce_ms": 15,
 "smoothing": 0.2, "deadband": 24, "timeout_ms": 2000}
```

`inputs` sind erst die Taster, dann die Schalter aus `config.yaml`.

### Pico → Pi

| Nachricht | Bedeutung |
|---|---|
| `HELLO pico <version>` | Kennung |
| `READY` | Konfiguration übernommen |
| `ERR <text>` | Fehler (ungültige Konfiguration, Absturz mit anschließendem Neustart) |
| `B <i> 0\|1` | Digitaleingang `i` hat sich geändert (entprellt; 1 = gedrückt / geschlossen) |
| `E <i> <delta>` | Drehgeber `i` hat sich um `delta` Rohschritte bewegt (meist 4 pro Raststufe) |
| `A <i> <wert>` | Analogeingang `i`, geglättet, 0 – 4095 |
| `S <bits> <a0> <a1> ...` | Snapshot: alle Digitaleingänge als `0`/`1`-Folge (`-` wenn keine), dann alle Analogwerte |

Kommt länger als `timeout_ms` nichts vom Pi, schaltet der Pico Ausgänge und LEDs ab. Meldet
der Pi sich wieder, schickt der Pico `HELLO` und wird neu konfiguriert. Umgekehrt baut der Pi
die Verbindung neu auf, wenn 2 s lang nichts vom Pico kommt.

## Pro Micro (Relais), Protokollversion 1

| Richtung | Nachricht | Bedeutung |
|---|---|---|
| Pi → | `?` | Bitte um `HELLO` |
| Pi → | `R <hex4>` | Alle 16 Relais setzen (Bit `n` = Kanal `n`, 1 = an). Dient auch als Heartbeat, alle 0,2 s. |
| Pi → | `K <hex4>` | Keep-Maske: diese Kanäle behalten bei Timeout ihren Zustand (Fernseher) |
| → Pi | `HELLO relay <version>` | Kennung, beim Start und auf `?` |
| → Pi | `R <hex4>` | Bestätigt den aktuellen Zustand nach jedem `R` |
| → Pi | `T` | Timeout: 1 s kein `R`, alle Kanäle außerhalb der Keep-Maske sind aus. Danach folgt `R <hex4>` mit dem neuen Zustand. |
| → Pi | `ERR unbekannt` | Zeile nicht verstanden |

Nach dem Einschalten sind alle Relais aus und die Keep-Maske ist 0. Der Pi schickt nach
`HELLO` zuerst `K`, dann `R`. Nur `R` zählt als Heartbeat.
