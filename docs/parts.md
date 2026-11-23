# Teileliste Elektronik

Alles, was an Elektronik verbaut wird, sortiert nach Baugruppe. Pins: [pins.md](pins.md),
Stromversorgung: [power.md](power.md).

Stand: **ja** = vorhanden, **kaufen** = entschieden, noch nicht da, **?** = unklar oder nicht
erfasst, bitte ergänzen, **offen** = noch nicht entschieden.

## Steuerung

| Teil | Menge | Zweck / Hinweis | Stand |
|---|---|---|---|
| Raspberry Pi 5, 4 GB | 1 | Hauptrechner | ja |
| Aktivkühler für Pi 5 | 1 | | ja |
| microSD-Karte (High Endurance, ≥ 32 GB) | 1 | System, Overlay-FS | ? |
| Offizielles Pi-Netzteil 27 W USB-C | 1 | Eigene Versorgung des Pi, siehe power.md | ? |
| Taster für An/Aus | 1 | an Lötpads `J2` des Pi 5, unter der Tischplatte | ? |
| Raspberry Pi Pico | 1 | Mittelkonsole und LED-Streifen | ja |
| Arduino Pro Micro, 5 V / 16 MHz | 1 | Relais | ja |
| Arduino Uno | 1 | Ersatzteil | ja |
| Micro-USB-**Daten**kabel | 2 | Pico und Pro Micro | ja |

Alle vier USB-Ports des Pi sind belegt: Lenkrad, Pico, Pro Micro, CD-Laufwerk. Für ein
weiteres USB-Gerät braucht es einen aktiven Hub.

## Audio

| Teil | Menge | Zweck / Hinweis | Stand |
|---|---|---|---|
| Raspberry Pi DAC Pro | 1 | | ja |
| Höhere Stiftleiste 2×20 (Stacking Header) und passende Abstandshalter | 1 | DAC passt sonst wegen des Kühlers nicht | kaufen |
| Verstärker und Lautsprecher (2.1-System) | 1 | 2 Mitteltöner, 1 Subwoofer | ? |
| Audiokabel DAC → Verstärker (Cinch oder Klinke) | 1 | | ? |
| USB-CD-Laufwerk | 1 | ohne eigene Auswurftaste | ? |

## Eingabe

| Teil | Menge | Zweck / Hinweis | Stand |
|---|---|---|---|
| Thrustmaster T80 (Lenkrad und Pedale) | 1 | | ja |
| Taster | 8 | Play, Next, Prev, Stopp, Auswerfen, Nitro, Truthahn, Pong | ? |
| Kippschalter, 1 Kontakt | 2 | Ventilatoren An/Aus, Alt-Sound | ? |
| Schlüsselschalter (rastend) | 1 | Zündschloss | ? |
| Drehgeber mit Rastung (z.B. EC11, ohne Taster) | 2 | Lautstärken, 4 Schritte pro Raststufe | ? |
| Schiebepoti linear, 10 kΩ | 2 | Pong, an der Acrylglasplatte | ? |
| LED für Nitro-Taster + Vorwiderstand 330 Ω | 1 | optional. Der Pico liefert nur ≈ 4 mA, für mehr Helligkeit einen Transistor einsetzen | offen |
| *später:* Schalter EIN-AUS-EIN | 1 | Strobo-Modus | offen |
| *später:* Kippschalter | 1 | Diskokugel | offen |
| Verdrillte oder abgeschirmte Leitung | einige m | zu den Potis an der Acrylglasplatte | ? |

## LED-Streifen

| Teil | Menge | Zweck / Hinweis | Stand |
|---|---|---|---|
| WS2812B-Streifen, 5 V, 60 LEDs/m, IP30 | 10 m (10 × 1 m) | je zwei Rücken an Rücken an einer Datenleitung, nur Rot genutzt | kaufen |
| 74HCT245 (DIP-20) + Sockel | 1 | Pegelwandler 3,3 V → 5 V für 5 Datenleitungen | ? |
| Widerstand 10 kΩ | 5 | Pull-downs an den Eingängen des 74HCT245 | ? |
| Widerstand 330 Ω | 10 | je Streifen einer in der Datenleitung, nah am Streifen | ? |
| Keramikkondensator 100 nF | 1 | am 74HCT245 | ? |
| Elko 1000 µF, ≥ 6,3 V | 5 | je Einspeisepunkt eines Streifenpaars | ? |
| Optional: Aluprofil oder Alu-Klebeband | 10 m | Wärmeableitung zwischen den verklebten Streifen | offen |

## LED-Matrix

| Teil | Menge | Zweck / Hinweis | Stand |
|---|---|---|---|
| MAX7219-Matrix-Modul 4-in-1 (32×8, rot) | 2 | hintereinander, 64×8, an SPI0 des Pi | kaufen |
| SN74AHCT125N (DIP-14) + Sockel | 1 | Pegelwandler für DIN, CLK, CS | kaufen |
| Keramikkondensator 100 nF | 1 | am 74AHCT125 | ? |

## Relais und Ausgabe

| Teil | Menge | Zweck / Hinweis | Stand |
|---|---|---|---|
| Relaisboard 16 Kanäle, 5 V, Optokoppler | 1 | Ventilatoren, Fernseher, Reserve | ? |
| Gehäuse für das Relaisboard | 1 | Berührschutz 230 V | ? |
| Ventilatoren mit 3 Stufen | bis 4 | Betriebsspannung offen, siehe power.md | ? |
| Röhrenfernseher 6", monochrom | 1 | | ? |
| HDMI-HF-Modulator | 1 | 5 V | ? |
| Micro-HDMI → HDMI-Kabel, Koaxkabel | je 1 | Pi → Modulator → Fernseher | ? |
| *später:* Stroboskope (2 weiß, 2 rot) | 4 | Ansteuerung offen | offen |
| *später:* Nebelmaschine | 1 | Ansteuerung offen | offen |
| *später:* Diskokugel mit Motor und Licht | 1 | Ansteuerung offen | offen |

## Stromversorgung

| Teil | Menge | Zweck / Hinweis | Stand |
|---|---|---|---|
| Mean Well RS-150-5 (5 V, 26 A) | 1 | alle 5-V-Verbraucher außer dem Pi | kaufen |
| Netzrelais-Modul, 1 Kanal, 5-V-Spule, 3,3-V-Eingang, Kontakt ≥ 16 A / 250 V (oder SSR mit Nullspannungsschaltung ≥ 25 A) | 1 | schaltet RS-150-5 und Verstärker mit dem Pi | kaufen |
| Kaltgerätebuchse mit Schalter und Sicherungshalter + Sicherung 3,15 A träge | 1 | Netzeingang | ? |
| Notaus-Pilzschalter, rastend, 2-polig, ≥ 10 A / 230 V | 1 | rechts von der Mittelkonsole | ? |
| Mehrfachsteckdose oder Verteilung 230 V | 1 | ungeschaltet: Pi-Netzteil, Relaiskontakte. Geschaltet: RS-150-5, Verstärker | ? |
| Flachsicherungsverteiler (≥ 8 Plätze) | 1 | 5-V-Abzweige | ? |
| Flachsicherungen | 6 × 3 A, 1 × 2 A, 2 × 1 A | siehe Tabelle in power.md | ? |
| Leitung 2,5 mm² | ≈ 1 m | Netzteil → Verteiler | ? |
| Leitung 1,5 mm² | je nach Aufbau | zu den LED-Streifen | ? |
| Leitung 0,5 – 0,75 mm² | je nach Aufbau | Matrix, Relais, Modulator, Logik | ? |
| Optional: Drossel ≈ 100 µH (≥ 1 A) + Elko 470 µF | 1 | Filter vor dem HF-Modulator, nur bei Bildstörungen | offen |

## Kleinmaterial

| Teil | Hinweis | Stand |
|---|---|---|
| Lochrasterplatine | für 74HCT245 und 74AHCT125, mit Schraubklemmen | ? |
| Schraubklemmen (Rastermaß 5 mm) | Anschlüsse der Platine | ? |
| Litze für die Konsole, Aderendhülsen, Wago-Klemmen, Schrumpfschlauch | | ? |
| Steckverbinder für die LED-Streifen (z.B. JST-SM 3-polig) | Streifen abnehmbar | offen |
| Kabelbinder, Zugentlastungen | | ? |
| Multimeter | Netzteil einstellen, Spannungsabfall messen | ? |
