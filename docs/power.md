# Stromversorgung

Teile: [parts.md](parts.md), Pins: [pins.md](pins.md).

## Überblick

```
230 V ── Kaltgerätebuchse ── Notaus ──┬── Pi-Netzteil (27 W, USB-C) ── Pi 5 ── GPIO 17 ──┐
         (Schalter, Sicherung)        │                                                 │ steuert
                                      ├── Netzrelais ──┬── 5-V-Netzteil RS-150-5 ── Sicherungsverteiler ── 5-V-Verbraucher
                                      │                └── Verstärker (2.1)
                                      └── Relaiskontakte des 16er-Boards ── Ventilatoren, Fernseher,
                                                                            später Strobos, Nebelmaschine, Diskokugel
```

- **Notaus:** trennt alles vom Netz.
- **An/Aus-Knopf:** schaltet den Pi (Taster an den Lötpads `J2` des Pi 5). Alles andere
  folgt ihm:
  - Läuft der Pi, zieht er über GPIO 17 das **Netzrelais** an. Das schaltet das RS-150-5
    und den Verstärker ein.
  - Ist der Pi aus, fällt das Netzrelais ab. Dann fehlt dem 16er-Relaisboard die
    Spulenspannung, also sind auch Ventilatoren und Fernseher aus. Pico und Pro Micro hängen
    am USB des Pi und gehen mit ihm aus.
  - Der Verstärker hängt am geschalteten Zweig, damit es beim Ausschalten des DAC nicht in den
    Lautsprechern knallt.
- **Solange der Pi läuft, die Software aber nicht:** Das Netzrelais bleibt an. Die
  Verbraucher schalten sich selbst ab:
  - Die LEDs gehen aus, wenn der Pico 2 s keinen Heartbeat bekommt.
  - Die Relais schalten nach 1 s ab, außer dem Fernseher.
  - Die LED-Matrix behält ihr letztes Bild. Die Software löscht sie beim Beenden. Nach einem
    Absturz bleibt das Bild stehen, bis der Dienst neu startet.

### Netzrelais

- **Modul:** einkanaliges Relaismodul mit Transistor- oder Optokopplereingang, das schon mit
  3,3 V schaltet (High-aktiv). Spule aus dem 5-V-Pin des Pi (Pin 2 oder 4), Steuereingang an
  GPIO 17 (Pin 11), GND an Pin 6. Es darf **nicht** vom RS-150-5 versorgt werden, das es ja
  selbst einschaltet.
- **Kontakt:** mindestens 16 A / 250 V AC, möglichst zweipolig (Phase und Neutralleiter).
  Beim Einschalten zieht das RS-150-5 kurz bis zu 40 A, der Verstärker
  zusätzlich. Ein normales 10-A-Relais verträgt das nicht dauerhaft, die Kontakte können
  verschweißen. Alternative: ein Halbleiterrelais (SSR) mit Nullspannungsschaltung, ≥ 25 A.
- **Einschalten beim Booten:** `gpio=17=op,dh` in `config.txt`. Die Firmware setzt den Pin
  damit schon vor Linux auf High, das Netzteil läuft also, bevor die Software startet.
- **Ausschalten beim Herunterfahren:** `POWER_OFF_ON_HALT=1` im EEPROM des Pi
  (`sudo rpi-eeprom-config --edit`). Dann schaltet der Pi beim Herunterfahren 3,3 V und die
  GPIOs ganz ab, und das Relais fällt sicher ab. Ohne diese Einstellung ist nicht garantiert,
  dass GPIO 17 im ausgeschalteten Zustand Low ist. Das muss mit dem echten Aufbau geprüft
  werden.

## 5-V-Netzteil: Mean Well RS-150-5

5 V, 26 A (130 W), Schraubklemmen, passiv gekühlt, Ausgangsspannung einstellbar 4,75 – 5,5 V.

- **Eingangsschalter auf 230 V stellen**, bevor es zum ersten Mal ans Netz geht. In der
  Stellung 115 V wird es an 230 V zerstört.
- **Ausgang auf 5,1 V einstellen** (Poti neben den Klemmen, mit Multimeter an den Klemmen
  messen). Das gleicht den Spannungsabfall auf den Leitungen aus. Mehr als 5,3 V vertragen die
  WS2812 nicht.
- **FG (Klemme 3) an den Schutzleiter.**
- **Schutz bei Überlast und Kurzschluss:** Ab 110 – 150 % Last schaltet es im Hiccup-Modus ab
  und läuft nach Behebung des Fehlers von selbst wieder an. Das ersetzt keine Sicherungen
  pro Abzweig (siehe unten).
- **Wärme:** Bei 5 V liefert es ab 40 °C Umgebung weniger Leistung, bei 70 °C noch 50 %. Bei
  der erwarteten Last von etwa 50 % reicht das bis 70 °C. Es braucht trotzdem Luft und darf
  nicht unter Polster oder in eine geschlossene Kiste.

### Strombedarf

| Verbraucher | Normalbetrieb | Schlimmster Fall |
|---|---|---|
| LED-Streifen: 10 × 60 WS2812B, nur Rot (≈ 20 mA pro LED), Helligkeit auf 30 % begrenzt | ≈ 3,6 A | 12 A (alle voll rot) |
| 2 Matrix-Module MAX7219 4-in-1 | ≈ 0,5 – 1 A | 2 A |
| Relaisboard, 16 Spulen à ≈ 75 mA | ≈ 0,3 A | 1,2 A |
| HF-Modulator (Wert prüfen) | ≈ 0,3 A | 0,5 A |
| 74HCT245, 74AHCT125 | vernachlässigbar | |
| **Summe** | **≈ 5 – 6 A** | **≈ 16 A** |

Weil nur Rot genutzt wird, reicht das Netzteil sogar ohne Helligkeitsbegrenzung. Mit Weiß
wären es im schlimmsten Fall 36 A. Deshalb setzt die Pico-Firmware Grün und Blau fest auf 0
(ab Meilenstein 6, siehe [decisions.md](decisions.md)).

### Verteilung

- **Sicherung pro Abzweig** in einem Flachsicherungsverteiler (Kfz-Teil):

  | Abzweig | Sicherung | Leitung |
  |---|---|---|
  | LED-Leitung 0 – 4 (je zwei Streifen) | je 3 A | 1,5 mm² |
  | Matrix-Module | 3 A | 0,75 mm² |
  | Relaisboard (JD-VCC) | 2 A | 0,75 mm² |
  | HF-Modulator | 1 A | 0,5 mm² |
  | Logik (Pegelwandler) | 1 A | 0,5 mm² |

  Ohne Sicherungen schaltet das Netzteil erst bei etwa 30 A ab. Ein Kurzschluss in einer
  dünnen Leitung würde sie bis dahin verschmoren.
- **Netzteil → Verteiler:** mindestens 2,5 mm², kurz halten.
- **LED-Streifen** am Anfang einspeisen, beide Streifen eines Paars an derselben Stelle.
  Ab etwa 2 m pro Streifen auch am Ende. Ein Elko mit 1000 µF (≥ 6,3 V) pro Einspeisepunkt
  schützt die ersten LEDs vor Spannungsspitzen beim Einschalten.
- **Gemeinsame Masse:** Netzteil-Minus, 74HCT245, 74AHCT125, Pico und Pi müssen verbunden
  sein, sonst funktionieren die Datenleitungen nicht. Sternförmig an einem Punkt (am Verteiler),
  nicht als Kette über die Verbraucher.
- **HF-Modulator:** Analoges Video ist empfindlich gegen Störungen auf der Versorgung. Falls
  auf dem Fernseher Streifen erscheinen, sobald die LEDs laufen, hilft ein LC-Filter vor dem
  Modulator (Drossel ≈ 100 µH, ≥ 1 A, und Elko ≈ 470 µF). Erst einmal ohne testen.

## Pi 5: eigenes Netzteil

Der Pi bekommt das offizielle 27-W-Netzteil (5,1 V, 5 A, USB-C mit PD) und nicht das RS-150-5:
- **Spannungseinbrüche:** Der Pi 5 meldet schon bei kleinen Einbrüchen Unterspannung. Schnell
  wechselnde LED-Last und schaltende Relais erzeugen genau solche Einbrüche.
- **USB-Strom:** Nur mit PD-Aushandlung gibt er an den USB-Ports 1,6 A frei. Sonst sind es
  600 mA, und an den Ports hängen Lenkrad, Pico, Pro Micro und CD-Laufwerk.
- **Audio:** LED- und Relaisstörungen gelangen nicht über die Versorgung in den DAC.

Wenn der Pi doch ans RS-150-5 soll: eigene dicke Leitung direkt von den Klemmen, Spannung auf
5,1 – 5,2 V, `usb_max_current_enable=1` in `config.txt` und `PSU_MAX_CURRENT=5000` im EEPROM.

## 230-V-Seite

- **Netzklemmen abdecken.** Beim RS-150 liegen sie offen. Zugentlastung an allen Netzleitungen,
  Schutzleiter an Netzteil-FG und an alle berührbaren Metallteile (Alurohre!).
- **Relaisboard:** Die Kontakte schalten 230 V (Ventilatoren, Fernseher). Bei billigen Boards ist
  der Abstand zwischen 230-V-Leiterbahnen und Logik knapp. Deshalb das Board in ein
  geschlossenes Gehäuse und 230-V- und Kleinspannungsleitungen getrennt führen.
- **Notaus:** rastender Pilzkopfschalter, zweipolig (Phase und Neutralleiter), für 230 V und
  mindestens den Gesamtstrom (≥ 10 A).
- Wer so etwas noch nicht verdrahtet hat, sollte die 230-V-Seite von einer Elektrofachkraft
  prüfen lassen.

## Offen

- Betriebsspannung der Ventilatoren (5 V, 12 V oder 230 V). Bei 12 V braucht es ein weiteres
  Netzteil. Bei 5 V müssen sie in die Rechnung oben.
- Stromaufnahme des HF-Modulators nachmessen.
- Versorgung von Strobos, Nebelmaschine und Diskokugel (vermutlich 230 V über die freien Relais).
- Prüfen, dass das Netzrelais nach dem Herunterfahren wirklich abfällt.
