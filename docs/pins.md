# Pin-Plan

Maßgeblich ist [config.yaml](../config.yaml). Diese Datei erklärt die Belegung und die Grenzen.
Änderungen an der Pico-Belegung brauchen kein neues Flashen: Der Pi schickt die Pins beim
Verbinden an den Pico.

## Raspberry Pi Pico (Mittelkonsole und LED-Streifen)

Alle Eingänge schalten gegen GND, der Pico hat interne Pull-ups. Taster und Schalter also
zwischen Pin und GND anschließen, ohne externe Widerstände.

| Pin | Element | Typ |
|---|---|---|
| GP0 | Play/Pause | Taster |
| GP1 | Nächster Track | Taster |
| GP2 | Vorheriger Track | Taster |
| GP3 | Stopp | Taster |
| GP4 | Auswerfen | Taster |
| GP5 | Nitro | Taster |
| GP6 | Truthahn-Kicker | Taster |
| GP7 | Pong-Start/Stop | Taster |
| GP8 | Ventilatoren An/Aus | Schalter |
| GP9 | Alt-Sound | Schalter |
| GP10 | Zündschloss | Schlüsselschalter |
| GP11, GP12 | Musik-Lautstärke | Drehgeber A, B (C an GND) |
| GP13, GP14 | Effekt-Lautstärke | Drehgeber A, B (C an GND) |
| GP15, GP16 | *später:* Strobo-Modus | Schalter, 3 Stellungen (zwei Kontakte) |
| GP17 | *später:* Diskokugel | Schalter |
| GP18 – GP22 | LED-Datenleitungen 0 – 4 | über 74HCT245 |
| GP26 | Pong links | Schiebepoti (Schleifer) |
| GP27 | Pong rechts | Schiebepoti (Schleifer) |
| GP28 | Nitro-LED (optional) | Ausgang |

Bilanz: 26 nutzbare GPIOs, davon 15 Digitaleingänge (18 mit den späteren), 2 analoge
Eingänge, 1 Ausgang und 5 LED-Leitungen. Damit ist alles belegt.

Einschränkungen:
- **ADC nur an GP26 – GP28.** GP29 ist auf dem Board intern belegt (Spannungsmessung).
- **GP23 – GP25 sind nicht herausgeführt** (Spannungsregler, VBUS-Erkennung, Onboard-LED).
- **Potis** zwischen 3V3 (Pin 36) und AGND (Pin 33) anschließen, nicht an 5 V. Lange
  Leitungen zur Acrylglasplatte: verdrillt oder abgeschirmt führen, die Firmware glättet
  zusätzlich (`analog_smoothing`, `analog_deadband`).
- **LED-Streifen:** Zehn Streifen mit je 60 LEDs, je zwei Rücken an Rücken. Die beiden Streifen
  eines Paars hängen **parallel** an derselben Datenleitung und zeigen dasselbe, `count` bleibt 60.
  Jeder Streifen bekommt einen eigenen 330-Ω-Widerstand in der Datenleitung, nah am Streifen.
  Sollen die Seiten getrennt leuchten, müssten die Streifen verkettet werden (`count` = 120).
  Der 74HCT245 braucht 5 V Versorgung, `DIR` fest auf High, `OE` fest auf GND.
- **Pull-downs an den Eingängen des 74HCT245** (je 10 kΩ gegen GND). Bis die Firmware läuft,
  sind die Pico-Pins offen, und Störungen würden als zufällige LED-Daten durchgereicht.
- **LED-Strom:** Genutzt wird nur Rot (≈ 20 mA pro LED). Eine Leitung mit zwei Streifen zieht
  damit höchstens 2,4 A, bei `max_brightness` 0,3 etwa 0,7 A. Ab Meilenstein 6 erzwingt die
  Pico-Firmware die Helligkeitsgrenze und setzt Grün und Blau fest auf 0. Versorgung und
  Sicherungen: [power.md](power.md).

## Arduino Pro Micro (Relais)

Die Kanalnummern sind fest in der Firmware ([relay.ino](../firmware/relay/relay.ino)) auf die Pins
verteilt. Welches Gerät an welchem Kanal hängt, steht in `config.yaml` unter `relay`.

| Kanal | Pin | Gerät |
|---|---|---|
| 0, 1, 2 | 2, 3, 4 | Ventilator 1 (an/aus, Stufe 1 / weiter, Stufe 2 / 3) |
| 3, 4, 5 | 5, 6, 7 | Ventilator 2 |
| 6, 7, 8 | 8, 9, 10 | Ventilator 3 |
| 9, 10, 11 | 16, 14, 15 | Ventilator 4 |
| 12 | A0 | Fernseher |
| 13 | A1 | frei (Strobos) |
| 14 | A2 | frei (Nebelmaschine) |
| 15 | A3 | frei (Diskokugel) |

- RX/TX (D0/D1) bleiben frei. Die Verbindung zum Pi läuft über das native USB.
- Die Firmware geht von einem **active-low** Relaisboard aus (Relais zieht bei LOW an), wie bei
  den meisten Boards mit Optokopplern. Sonst `ACTIVE_LOW` in relay.ino auf 0 setzen.
- Pro Micro in der **5-V/16-MHz-Version**. Ein 3,3-V-Board kann die Eingänge eines 5-V-Relaisboards
  nicht sicher schalten.
- Relaisspulen nicht aus dem Pro Micro versorgen: 16 Relais brauchen gut 1 A an JD-VCC.

### Verdrahtung eines Ventilators

Relais in Ruhe = Kontakt NC. Jede Schaltkombination legt höchstens eine Wicklung an Spannung.

```
Phase ── R1 ──NC── (aus)
          └──NO── R2 ──NC── Stufe 1
                   └──NO── R3 ──NC── Stufe 2
                            └──NO── Stufe 3
```

| Stufe | R1 | R2 | R3 |
|---|---|---|---|
| 0 | aus | aus | aus |
| 1 | an | aus | aus |
| 2 | an | an | aus |
| 3 | an | an | an |

## Raspberry Pi 5

| GPIO | Verwendung |
|---|---|
| 2, 3 | DAC Pro (I²C) |
| 18 – 21 | DAC Pro (I²S) |
| 10 (MOSI), 11 (SCLK), 8 (CE0) | LED-Matrix über SPI0 und 74AHCT125 |
| 17 (Pin 11) | Netzrelais für RS-150-5 und Verstärker (High = an), siehe [power.md](power.md) |

### LED-Matrix

Zwei MAX7219-Module „4 in 1“ (je 32×8), hintereinander: DOUT des ersten an DIN des zweiten,
CLK und CS parallel. Ergibt 64×8 Pixel. Versorgung mit 5 V aus dem RS-150-5, nicht vom Pi
([power.md](power.md)). SPI muss in `config.txt` aktiviert werden (`dtparam=spi=on`), das kommt
mit der Software für die Matrix ins Setup-Skript.

Der MAX7219 braucht bei 5 V mindestens 3,5 V als High. Deshalb ein SN74AHCT125N (DIP-14) als
Pegelwandler, versorgt mit 5 V:

| Pin | Funktion | Anschluss |
|---|---|---|
| 14 | VCC | 5 V, 100 nF nach GND direkt am Chip |
| 7 | GND | GND (gemeinsam mit Pi und Netzteil) |
| 1, 4, 10 | 1OE, 2OE, 3OE | GND (Ausgänge immer aktiv) |
| 2 → 3 | 1A → 1Y | GPIO 10 (MOSI) → DIN |
| 5 → 6 | 2A → 2Y | GPIO 11 (SCLK) → CLK |
| 9 → 8 | 3A → 3Y | GPIO 8 (CE0) → CS |
| 12, 13 | 4A, 4OE (unbenutzt) | beide an GND |
| 11 | 4Y | offen |

- Bei mehr als etwa 30 cm vom Pegelwandler zur Matrix: 47 – 100 Ω in Reihe direkt an den
  Ausgängen (Pins 3, 6, 8).
- Beim Booten liegen undefinierte Pegel an. Das ist harmlos: Der MAX7219 startet dunkel und
  zeigt erst nach der Initialisierung etwas an.
- Günstige Module haben oft MAX7219-Klone. Bei Fehlern den SPI-Takt senken (z.B. 1 MHz).
  Manche Chargen haben gedreht oder gespiegelt eingelötete Matrizen, das gleicht die Software aus.
