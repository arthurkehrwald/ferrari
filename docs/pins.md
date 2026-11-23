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
- **LED-Streifen:** Fünf Leitungen reichen für fünf Streifen. Für mehr werden Streifen verkettet
  (`count` der Leitung = Summe der LEDs). Bei 8 Streifen also drei Leitungen mit je 120 und zwei mit je 60 LEDs.
  Der 74HCT245 braucht 5 V Versorgung, `DIR` fest auf High, `OE` fest auf GND.
- **Pull-downs an den Eingängen des 74HCT245** (je 10 kΩ gegen GND). Bis die Firmware läuft,
  sind die Pico-Pins offen, und Störungen würden als zufällige LED-Daten durchgereicht.
- **LED-Strom:** 60 LEDs ziehen bei vollem Weiß bis zu 3,6 A. `max_brightness` begrenzt das.
  Ab Meilenstein 6 erzwingt auch die Pico-Firmware diese Grenze (sie bekommt sie per CFG).

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

Die GPIO-Leiste gehört allein dem DAC Pro (I²S an GPIO 18 – 21, I²C an GPIO 2/3).
