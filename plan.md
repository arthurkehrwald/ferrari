# Der Plan

Ein "Auto" für ein Festival. Es ist eine einfache Konstruktion aus Holz und Alurohren. Es hat eine Sitzbank und ein Lenkrad, aber keinen Motor und keine Räder. Man kann sich reinsetzen und Musik hören. Es gibt allerlei Gimmicks. Das Auto steht unter einem Zeltdach.

## Eingabegeräte

- __Lenkrad und Pedale__: Ein Rennsimulator Kit (Thrustmaster T80, PC-Modus, funktioniert unter Linux) dient zur Steuerung des Autos. Pedale: Gas und Bremse, keine Kupplung. Am Lenkrad befinden sich zwei Schaltwippen (hoch-/runterschalten) und zahlreiche weitere Knöpfe (siehe Modusübergreifende Funktionen).
- __Zündschloss__: Ein Schlüsselschalter, der nach dem Drehen in seiner Stellung bleibt. Die Software wertet jeden Wechsel der Schalterstellung (egal in welche Richtung) als eine Betätigung, wie einen kurzen Tastendruck. Die Stellung beim Booten spielt keine Rolle.
- __Mittelkonsole__: Schalter, Taster und Inkrementalgeber, siehe Tabelle unten.
- __CD-Laufwerk__: USB-Laufwerk zum Abspielen handelsüblicher Audio-CDs. Ausgeworfen wird über die Taste am Laufwerk.
- __Bluetooth__: Der Pi meldet sich als Bluetooth-Lautsprecher (A2DP-Sink), sodass man Musik vom Handy anstelle des CD-Laufwerks abspielen kann. Wichtig: Motorgeräusche und andere Töne werden weiterhin ausgegeben.

### Mittelkonsole

| # | Element | Typ | Pins | Funktion |
|---|---|---|---|---|
| 1 | Play/Pause | Taster | 1 | Musik |
| 2 | Nächster Track | Taster | 1 | Musik |
| 3 | Vorheriger Track | Taster | 1 | Musik |
| 4 | Stopp | Taster | 1 | Musik |
| 5 | Musik-Lautstärke | Inkrementalgeber (A/B) | 2 | Lautstärke der Musik (CD und Bluetooth) |
| 6 | Effekt-Lautstärke | Inkrementalgeber (A/B) | 2 | Lautstärke von allem außer Musik |
| 7 | Quelle CD / Bluetooth | Kippschalter | 1 | Musikquelle |
| 8 | Musik intern / extern | Kippschalter | 1 | Audio-Routing |
| 9 | Nitro | Taster | 1 | Fahrtmodus |
| 10 | Truthahn-Kicker | Taster | 1 | Startet das Spiel |
| 11 | Bluetooth-Pairing | Taster | 1 | Bluetooth |
| 12 | Bluetooth-Pairing-LED | LED (Ausgang) | 1 | Leuchtet/blinkt während Pairing erlaubt ist |
| 13 | Zündschloss *(nicht in der Konsole)* | Schlüsselschalter | 1 | Modus |
| | __Summe__ | | __15__ | 14 Eingänge, 1 Ausgang |
| 14 | *später:* Strobo-Modus | Schalter, 3 Stellungen | 2 | Aus / An / Strobo |
| 15 | *später:* Diskokugel | Kippschalter | 1 | An / Aus |
| | __Summe mit späteren Elementen__ | | __18__ | |

Pinverteilung: Die Mittelkonsole und die LED-Streifen hängen an einem Raspberry Pi Pico, der per USB-Seriell mit dem Pi verbunden ist. Der Pico hat 26 GPIOs: 18 für die Mittelkonsole (inklusive der späteren Elemente), bis zu 8 für die Datenleitungen der LED-Streifen. Werden je zwei Streifen verkettet, bleiben Pins frei. Die Relais hängen an einem Arduino Pro Micro, ebenfalls per USB. Die GPIOs des Pi 5 werden nur vom DAC-HAT belegt und sind von der Konsolenverkabelung getrennt.

## Ausgabegeräte

- Vier __Ventilatoren__ erzeugen Fahrtwind. Sie blasen alle geradeaus. Jeder Ventilator kann aus oder auf einer von drei Stufen laufen. Gesteuert werden sie über ein Relaisboard mit 16 Relais, das an einem Arduino Pro Micro hängt (USB-Seriell zum Pi). 12 Relais sind für die Ventilatoren, 4 bleiben frei für Strobos, Nebelmaschine und Diskokugel. Sicherheitsregeln:
    - Pro Ventilator darf nie mehr als ein Stufenrelais gleichzeitig an sein (Kurzschluss zwischen den Wicklungen). Das wird im Arduino-Code erzwungen, wenn möglich auch in der Verdrahtung.
    - Beim Start und bei Verbindungsverlust zum Pi (kein Heartbeat für z.B. 1 s) schaltet der Arduino alle Relais aus.
    - Eine Stufe bleibt für eine Mindestdauer eingeschaltet, damit die Relais nicht klappern.
- __Exciter__ (Körperschallwandler) unter der Sitzbank, angeschlossen über DAC-HAT und Verstärker. Sie machen Motor- und Fahrgeräusche und spielen alle Effekte ab, optional auch Musik (siehe Audio-Routing).
- __Externe Lautsprecher__: Optional kann über eine USB-Soundkarte (3,5 mm Klinke) ein externes Lautsprechersystem angeschlossen werden. Darauf läuft nur Musik.
- Ein monochromer __Röhrenfernseher__ mit 6 Zoll Bilddiagonale, angeschlossen über einen HDMI-HF-Adapter. Wegen der geringen Größe und des Zeilensprungs: große Schrift, dicke Linien, keine dünnen waagerechten Linien.
- 5 bis 8 __LED-Streifen__ mit je 60 einzeln steuerbaren LEDs (5 V) hängen über der Motorhaube im rechten Winkel zur Sitzbank. Sie werden vom Pi Pico über dessen PIO-Hardware gesteuert, sodass das Auslesen der Mittelkonsole nicht gestört wird. Weil der Pico mit 3,3 V arbeitet, kommt ein Pegelwandler (z.B. 74HCT245, 8 Kanäle) zwischen Pico und Datenleitungen. Die maximale Helligkeit ist in der Konfiguration begrenzt.
- *Später:* Eine __Nebelmaschine__, als Auspuff getarnt
- *Später:* Vier __Stroboskope__, zwei vorne in weiß, zwei hinten in rot
- *Später:* Eine __Diskokugel__, motorisiert und beleuchtet

## Audio

### Routing

| Ausgang | Hardware | Inhalt |
|---|---|---|
| Intern | DAC-HAT → Verstärker → Exciter | Motor, Fahrgeräusche, Effekte, Spiel; Musik, wenn Schalter auf "intern" |
| Extern | USB-Soundkarte → 3,5 mm Klinke | Musik, wenn Schalter auf "extern" |

Falls die Exciter mit Musik schlecht klingen, läuft Musik grundsätzlich nur extern und der Schalter entfällt.

- Der Regler __Musik-Lautstärke__ steuert die Musik (CD und Bluetooth), der Regler __Effekt-Lautstärke__ alles andere.
- Beide Lautstärken werden gespeichert und gelten auch nach einem Neustart.
- Mischen und Routen übernimmt PipeWire.

### Musikquelle

Der Kippschalter CD/Bluetooth bestimmt, welche Quelle zu hören ist. Die andere ist stumm. Beim Umschalten auf Bluetooth wird die CD pausiert.

### CD-Spieler

- Beim Einlegen einer CD startet die Wiedergabe automatisch, sofern die Quelle auf CD steht.
- __Play/Pause__: Wiedergabe starten oder an der aktuellen Stelle pausieren.
- __Nächster/Vorheriger Track__: Track wechseln.
- __Stopp__: Wiedergabe beenden und auf Track 1 zurücksetzen.
- Am Ende der CD wird auf Track 1 zurückgesetzt und pausiert. Mit Play startet sie neu.

### Bluetooth

- Pairing ist nur nach Druck auf den __Pairing-Taster__ möglich.
- Auf Knopfdruck wird ein verbundenes Handy getrennt und Pairing für 30 Sekunden erlaubt. Die Pairing-LED zeigt das an.
- Pairing-Anfragen werden in diesem Zeitfenster automatisch angenommen, ohne PIN.
- Es ist immer höchstens ein Handy verbunden.

## Steuerung

Die zentrale Kontrolleinheit des Autos ist ein Raspberry Pi 5 mit 4 GB RAM. Der Pi hat einen Audio DAC Hat für besseren Sound. An den Pi sind alle Eingabe- und Ausgabegeräte direkt oder indirekt angeschlossen. Eine Software auf dem Pi liest die Eingabegeräte, simuliert ein rudimentäres virtuelles Auto (Geschwindigkeit, Drehzahl) und steuert dementsprechend die Ausgabegeräte. Die Software hat mehrere Modi.

### Software-Stack

- __Python__ als Programmiersprache
- __pygame__ für die Bildschirmausgabe
- __PipeWire__ zum Mischen und Routen des Audios und als Bluetooth-Empfänger
- __Motorsound__ aus Samples, die je nach Drehzahl in der Tonhöhe verschoben und überblendet werden
- __Mikrocontroller__: Pi Pico (Mittelkonsole und LEDs) und Arduino Pro Micro (Relais) sind per USB-Seriell angebunden, mit einem einfachen Protokoll und Heartbeat. Der Arduino Uno bleibt als Ersatzteil übrig.

### Konfiguration

Alle Einstellungen stehen in einer YAML-Datei. Dazu gehören:
- Timings und Timeouts
- Fahrphysik: Beschleunigung, Bremsen, Luftwiderstand, Übersetzungen, Drehzahlgrenzen, Nitro-Dauer und -Leistung
- Geschwindigkeitsschwellen für die Ventilatorstufen
- LED-Farben, -Helligkeit und Impulsgeschwindigkeit
- Spieldauer, Tritte pro Truthahn und Schwellwerte der Pedale
- Soundlisten der Lenkradknöpfe
- Pin-Belegung

### Persistente Daten

Folgendes wird gespeichert:
- der Abwürg-Zähler
- der Truthahn-Highscore (nur die Zahl)
- die beiden Lautstärken

Zurücksetzen lassen sich die Zähler nur über SSH oder mit Maus und Tastatur, nicht am Auto selbst.

### Robustheit

- Schreibgeschütztes Root-Dateisystem (Overlay-FS), damit Stromausfälle die SD-Karte nicht beschädigen. Persistente Daten liegen auf einer separaten beschreibbaren Partition und werden atomar geschrieben.
- Autostart per systemd, automatischer Neustart bei Absturz, Watchdog.
- Lenkrad, Pico, Pro Micro, CD-Laufwerk und Soundkarte werden wieder erkannt, wenn sie ab- und wieder angesteckt werden.
- Wartungszugang per SSH über einen WLAN-Hotspot des Pi.

### Standbymodus

- Keine Motorengeräusche, die Ventilatoren drehen nicht.
- Musik läuft weiterhin, die Mittelkonsole und das CD-Laufwerk bleiben aktiv.
- Auf dem Röhrenfernseher läuft ein Video in Endlosschleife. Wenn die Pedale betätigt werden, informiert der Fernseher, dass der Motor mit dem Schlüssel gestartet werden muss.
- Die LED-Streifen zeigen dieselben Lichtimpulse wie beim Fahren, nur sehr langsam.

Dieser Modus wird aktiviert:

- Nach dem Start des Pis
- Wenn die Pedale im Fahrtmodus 1 Minute lang nicht betätigt werden. Dann ist ein Abstellgeräusch zu hören.
- Wenn das Zündschloss im Fahrtmodus betätigt wird. Dann ist ein Abstellgeräusch zu hören.
- Wenn der Motor abgewürgt wurde

### Fahrtmodus

Dieser Modus wird aktiviert, wenn das Zündschloss im Standbymodus betätigt wird. Dabei ist ein Anlassgeräusch zu hören. Das Auto startet im Leerlauf.

Auf Basis der Eingabegeräte wird ein virtueller Ferrari mit Verbrennungsmotor und manueller Gangschaltung rudimentär simuliert. Realitätsgetreues Fahrverhalten oder authentischer Motorsound sind unwichtig. Es sollte dennoch eindrucksvoll sein.

__Gänge__: N (Leerlauf), dann 1 bis 6. Es gibt keinen Rückwärtsgang. Mit den Schaltwippen wird sequenziell hoch- und runtergeschaltet.

__Simulation__:
- Das Gaspedal erhöht die Geschwindigkeit, das Bremspedal verringert sie. Ohne Gas wird das Auto durch Roll- und Luftwiderstand langsam langsamer.
- Im Leerlauf folgt die Drehzahl frei dem Gaspedal (Hochdrehen im Stand), mindestens aber der Leerlaufdrehzahl.
- Im Gang ergibt sich die Drehzahl aus Geschwindigkeit und Übersetzung.
- Im 1. Gang gibt es unterhalb einer Geschwindigkeitsschwelle eine automatische "schleifende Kupplung": Die Drehzahl fällt nicht unter die Leerlaufdrehzahl, sodass man anfahren kann.
- __Drehzahlbegrenzer__: Bei maximaler Drehzahl wird die Leistung kurz unterbrochen. Der Motorsound stottert und auf dem Fernseher steht "HOCHSCHALTEN!".
- Die Reifen können bei abrupten Lenkmanövern, starker Beschleunigung oder starkem Bremsen die Haftung verlieren. Dann sind Quietschgeräusche zu hören.

__Abwürgen__:
- Wenn in einem Gang (nicht im Leerlauf) die Drehzahl gefährlich niedrig ist, blinken die LED-Streifen und der Röhrenfernseher. Auf dem Fernseher wird außerdem fett "RUNTERSCHALTEN!" angezeigt.
- Fällt die Drehzahl unter die Abwürgschwelle, wird der Motor abgewürgt.
- Die Software zählt mit und zeigt auf dem Bildschirm an, zum wievielten Mal das jetzt schon passiert ist.
- Bei einer runden Anzahl (10·x) wird ein Konfettieffekt eingeblendet und eine Partytröte ist zu hören.
- Dann geht der Motor aus und das Auto wechselt in den Standbymodus.

__Nitro__:
- Mit zurückgelegter Distanz füllt sich ein Nitro-Meter. Während Nitro aktiv ist, füllt es sich nicht.
- Wenn das Nitro voll ist, kann man es mit dem Nitro-Taster aktivieren. Dann ist die Leistung des Motors für kurze Zeit erhöht.
- *Später*: Solange Nitro aktiv ist, läuft die Nebelmaschine im Auspuff.

__Ton__: Die Exciter erzeugen Fahrtgeräusche basierend auf Geschwindigkeit, Gang, Drehzahl und Reifenhaftung. Dazu gehören _nicht_ Fahrtwindgeräusche, dafür sind die Ventilatoren da.

__Ventilatoren__: Sie drehen sich je nach Geschwindigkeit schneller oder langsamer. Die Schwellen für die Stufen stehen in der Konfiguration.

__Röhrenfernseher__:
- Geschwindigkeit in km/h als Zahl in der Mitte
- Eingelegter Gang (N, 1 bis 6)
- Drehzahl als Zahl und als Balken, der sich zu einer hohen maximalen Drehzahl füllt
- Ventilatorgeschwindigkeit mit einem Ventilatorsymbol und drei Balken
- Nitro-Meter als Balken
- Abwürg-Zähler
- Warnungen ("RUNTERSCHALTEN!", "HOCHSCHALTEN!")

__LED-Streifen__:
- Lichtimpulse laufen von vorne zum Fahrer hin, ihre Geschwindigkeit hängt von der virtuellen Geschwindigkeit ab.
- Bei Nitro wird invertiert, welche LEDs an und welche aus sind, damit es insgesamt deutlich heller wird. Bei Nitro blinkt nichts, damit es nicht mit der Drehzahlwarnung verwechselt wird.
- Bei gefährlich niedriger Drehzahl blinken die Streifen. Das hat Vorrang vor allem anderen.

### Super-Turbo-Truthahn-Kicker-Modus

Eine Hommage an das Easter-Egg aus __DOOM__. Alle Grafiken und Sounds werden selbst gemacht.

__Aktivierung__:
- Der Modus wird aus dem Standby- oder Fahrtmodus mit dem Truthahn-Taster gestartet.
- Der Fahrtmodus wird dabei eingefroren: Motorsound stumm, Ventilatoren aus.
- Während des Spiels werden der Truthahn-Taster und das Zündschloss ignoriert. Wurde das Zündschloss während des Spiels betätigt, geht es danach im Standbymodus weiter.
- Sonst wird nach dem Spiel der vorherige Modus wiederhergestellt. Die Pedale werden dann ignoriert, bis sie einmal losgelassen wurden, damit das Auto nicht plötzlich losspringt.
- Das Spiel kann nicht abgebrochen werden.

__Spiel__:
- Es handelt sich um ein primitives 2D-Arcadespiel, bei dem man mit den Pedalen Truthähne treten muss.
- Auf dem Bildschirm erscheinen ein Truthahn, eine Punktzahl und ein Balken, der die verbleibende Zeit anzeigt (ca. 30 Sekunden). Davor ein Paar gebeugte Beine.
- Wenn man fest genug in eins der Pedale tritt (obere Schwelle), streckt sich das entsprechende Bein aus und der Truthahn wird getreten.
- Ein neuer Tritt mit diesem Pedal zählt erst, nachdem es losgelassen wurde (untere Schwelle).
- Nach x Tritten stirbt der Truthahn und ein neuer erscheint.
- Ziel ist es, den Highscore zu knacken, bevor die Zeit ausläuft.
- Die LED-Streifen blinken bei jedem Tritt.

Die Grafik und der Ton sind sehr einfach gehalten:
- Zwei Sprites für die Beine (ausgestreckt, gebeugt). Für die andere Seite gespiegelt.
- Drei Sprites für den Truthahn (normal, getreten, tot). Bei einem Tritt wird kurz das Getreten-Sprite angezeigt.
- Kurzer 8-Bit-Loop im Hintergrund. Er läuft nur, wenn über CD oder Bluetooth gerade keine Musik spielt.
- Soundeffekte: Treten, Truthahngeschrei, Punkte bekommen, Game Over, Highscore geknackt

### Modusübergreifende Funktionen

- Am Lenkrad sind zahlreiche Knöpfe, die keine sinnvolle Funktion haben. Jedem Knopf wird eine Liste aus Soundeffekten zugeordnet, die bei wiederholtem Drücken nacheinander abgespielt werden. Die Zuordnung steht in der Konfiguration.
- Musiksteuerung und Bluetooth-Pairing funktionieren in allen Modi.
- *Später:* Die Strobo-Scheinwerfer kennen drei Betriebsarten, die per Mittelkonsole umgeschaltet werden:
    - Aus
    - An: Konstante Helligkeit
    - Strobo: An und aus im Takt zur Musik (Beat-Erkennung in der Software)
- *Später:* Die Diskokugel macht einfach ihr Ding und kann nur an- und ausgeschaltet werden.

## Meilensteine

0. Grundgerüst: Konfiguration (YAML), Pin-Plan, Protokoll zu Pico und Pro Micro, Audio-Routing mit beiden Ausgängen in PipeWire. Entwicklung zunächst mit HDMI-Monitor.
1. Fahrsimulation ohne Ton mit Pedal und Lenkrad
2. Ventilatoren
3. Fahrtgeräusche erzeugen und über Pi an integrierte Lautsprecher ausgeben
4. Musik per CD-Laufwerk abspielen
5. Röhrenfernseher
6. LED-Streifen
7. Externer Lautsprecheranschluss
8. Bluetooth
9. Super-Turbo-Truthahn-Kicker
10. Stroboskope
11. Nitro und Nebelmaschine
12. Diskokugel

## Offene Fragen

- Klingt Musik über die Exciter gut genug? Falls nicht, läuft Musik nur extern (Test steht aus).
- Führen Vibrationen zu Aussetzern beim CD-Laufwerk? Falls ja, die CD beim Einlegen komplett in den RAM einlesen (Test steht aus).
- LED-Streifen: Bekommt jeder Streifen eine eigene Datenleitung am Pico oder werden je zwei verkettet? In welcher Farbe leuchten die Impulse?
- Welcher DAC-HAT genau und welche GPIOs belegt er?
- Soll der Nitro-Taster eine LED haben, die anzeigt, dass Nitro verfügbar ist?
- Was für Stroboskope kommen zum Einsatz und wie werden sie gesteuert? LED-Stroboskope lassen sich oft farblich einstellen und es gibt welche mit integriertem Mikrofon, die zwischen Strobo und konstanter Beleuchtung umgeschaltet werden können. Allerdings mit einer Infrarot-Fernbedienung. Muss ich die Fernbedienung mit einer Infrarot-LED imitieren oder gibt es eine bessere Alternative?
- Was für eine Nebelmaschine und wie wird sie gesteuert? (Aufheizzeit, heiße Düse, Rauchmelder im Zelt beachten)
- Wie werden Motor und Beleuchtung der Diskokugel an- und ausgeschaltet?
