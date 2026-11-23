# Technische Entscheidungen

Was in Meilenstein 0 entschieden wurde, warum, und was daraus für die weiteren Meilensteine
folgt. Pins: [pins.md](pins.md), Protokoll: [protocol.md](protocol.md).

## Aufbau der Software

```
ferrari/            Python-Paket, Start mit  python -m ferrari
  __main__.py       Hauptschleife (50 Hz): Ereignisse verarbeiten, Watchdog melden
  config.py         config.yaml -> Dataclasses, mit Prüfung und Fehlermeldungen mit Pfad
  persist.py        Zähler, Highscore, Lautstärken als JSON, atomar und verzögert geschrieben
  protocol.py       Kodieren und Dekodieren der Zeilen zu Pico und Pro Micro, Relaismasken
  audio.py          Lautstärke der virtuellen Sinks über pactl
  sdnotify.py       sd_notify für den systemd-Watchdog, ohne Abhängigkeit
  devices/          Lenkrad (hidraw), Pico und Pro Micro (seriell), je ein Thread
firmware/pico/      MicroPython
firmware/relay/     Arduino (C++)
tools/              monitor.py, flash_pico.sh, flash_relay.sh, deploy.sh
tests/              pytest, läuft auf PC und Pi
```

### Threads und Ereignisse

Jedes Gerät läuft in einem eigenen Thread. Der Thread verbindet sich selbst neu, wenn das Gerät
fehlt oder abgesteckt wird (Versuch jede Sekunde), und legt Ereignisse (`ButtonPressed`,
`SwitchChanged`, `EncoderTurned`, `AnalogChanged`, `WheelButton`, `Connected`, `Lost`) in eine
gemeinsame Queue. Die Hauptschleife ist der einzige Ort mit Programmlogik.

- **Lenkrad und Pedale** sind ein Zustand und kein Ereignisstrom: `wheel.state` wird bei jedem
  HID-Report atomar ersetzt und von der Hauptschleife gelesen. Nur Lenkradknöpfe erzeugen
  Ereignisse. Beim Abstecken wird der Zustand auf „alles losgelassen“ gesetzt.
- **Ausgaben** (Relais, Pico-Ausgänge, LEDs) laufen über Methoden der Gerätethreads
  (`relay.set_fan()`, `pico.set_output()`, `pico.send_leds()`). Sie sind threadsicher, und den
  gewünschten Zustand stellen die Threads nach einem Neuverbinden selbst wieder her.
- Die Hauptschleife meldet sich bei jedem Durchlauf beim systemd-Watchdog. Hängt sie, startet
  systemd den Dienst nach 10 s neu. Das ist getestet.

**Für die nächsten Meilensteine:** Die Modi (Standby, Fahrt, Truthahn, Pong) kommen in die
Hauptschleife oder in eigene Module, die sie pro Tick aufruft. pygame braucht ohnehin eine
Schleife im Hauptthread; die bestehende 50-Hz-Schleife sollte dafür zur pygame-Schleife werden
(`clock.tick(fps)` statt `queue.get(timeout)`). Blockierende Arbeit (pactl, Dateizugriffe,
CD lesen) gehört in Threads, sonst ruckelt die Anzeige und der Watchdog schlägt zu.

### Konfiguration

- **Eine Datei, eine Quelle:** Auch die Pico-Pinbelegung steht in `config.yaml`. Der Pi schickt
  sie beim Verbinden per `CFG` an den Pico. Eine neue Belegung braucht also nur einen Neustart
  der Software, kein Flashen.
- **Die Relais-Pins** sind dagegen fest in der Firmware. Grund: Beim Einschalten muss der Pro Micro
  die Relais sofort sicher abschalten, bevor der Pi überhaupt da ist. In `config.yaml` steht nur,
  welches Gerät an welchem der 16 Kanäle hängt.
- Die Prüfung sammelt alle Fehler und nennt den Pfad (`pico.analog.pong_left: GP5 hat keinen ADC`).
  Mit falscher Konfiguration startet das Programm nicht (Exit-Code 2).
- Neue Abschnitte (Fahrphysik, Fernseher, …) kommen erst mit ihren Meilensteinen dazu. Dafür
  jeweils eine Dataclass in `config.py` ergänzen und in `_parse()` lesen.

### Persistenz

- JSON in `/var/lib/ferrari/state.json`. Geschrieben wird über eine Temp-Datei, fsync und rename,
  danach wird auch das Verzeichnis gesynct. Ein Stromausfall hinterlässt also entweder die alte
  oder die neue Datei.
- Geschrieben wird frühestens 2 s nach der letzten Änderung (`persist.save_delay_s`). Schnelles
  Drehen am Lautstärkeregler erzeugt so nur einen Schreibvorgang. Beim Beenden wird sofort
  geschrieben.
- Eine kaputte Datei oder unbekannte Schlüssel führen zu Standardwerten statt zu einem Absturz.
- **Zurücksetzen** (laut Plan nur per SSH): Dienst stoppen, Datei bearbeiten oder löschen,
  Dienst starten.

## Mikrocontroller

### Protokoll

Zeilenbasiertes ASCII statt eines Binärprotokolls: Man kann es mit `screen` oder einem
Zehnzeiler mitlesen und von Hand testen, und Fehlermeldungen von MicroPython landen lesbar im Log.
Die Bandbreite reicht für alles außer möglicherweise den LED-Frames (siehe unten).

Beide Seiten prüfen die Gegenseite: Der Pi konfiguriert und schaltet nur, wenn `HELLO` den
richtigen Gerätetyp und die richtige Protokollversion meldet. Bei inkompatiblen Änderungen am
Protokoll also `PICO_PROTOCOL` bzw. `RELAY_PROTOCOL` in `protocol.py` und `VERSION` in der
Firmware gemeinsam erhöhen.

### Pico: MicroPython

- **Warum MicroPython:** Es ist dieselbe Sprache wie auf dem Pi, und Updates gehen vom Pi aus per
  `mpremote`, ohne BOOTSEL-Taste. `tools/flash_pico.sh --micropython` schickt den Pico per
  Software in den Bootloader und installiert MicroPython neu (Version im Skript festgelegt).
- **Taster** werden jede Millisekunde abgefragt und in Software entprellt (`debounce_ms`).
  **Drehgeber** laufen über Hardware-Interrupts mit Quadratur-Tabelle. Der Pico meldet Rohschritte,
  der Pi rechnet in Raststufen um (`encoder_steps_per_detent`).
- **Analogwerte** werden alle 20 ms gelesen, geglättet (exponentiell) und nur bei Änderungen über
  `analog_deadband` gemeldet. Die Anschläge (0 und 4095) sind trotz Glättung erreichbar. Offene
  ADC-Eingänge ohne Poti schwanken stark und erzeugen viele Meldungen. Deshalb protokolliert die
  Hauptschleife `AnalogChanged` nur im Debug-Log.
- **Snapshot jede Sekunde:** Er dient als Heartbeat und gleicht verlorene Ereignisse aus. Der erste
  Snapshot nach dem Verbinden wird still übernommen: Die Stellung des Zündschlosses beim Start
  löst nichts aus, wie im Plan gefordert.
- Der Pi ignoriert nach einem `CFG` eine Sekunde lang weitere `HELLO`s. Sonst wurde der Pico beim
  Verbinden mehrfach konfiguriert, weil mehrere `?`-Anfragen gleichzeitig unterwegs waren.
- **Kein Watchdog auf dem Pico:** `mpremote` unterbricht das Programm für Updates, ein Watchdog
  würde den Pico dabei neu starten. Bei einer Python-Exception meldet die Firmware `ERR Absturz`
  und startet neu.

**Offen für Meilenstein 6 (LEDs):** Das Format `L <hex>` ist vorläufig. In MicroPython wird
stdin Byte für Byte gelesen. Ein ganzer Frame mit 300 LEDs sind 1800 Hex-Zeichen, und das ist
für 50 fps vermutlich zu langsam. Zwei Möglichkeiten:
- **Der Pi rendert, schnellere Übertragung:** Binär übertragen und in größeren Blöcken lesen
  (z.B. `machine.USBDevice` oder `sys.stdin.buffer.readinto`).
- **Der Pico rendert selbst:** Der Pi schickt nur Parameter (Geschwindigkeit, Modus, Farbe).
  Das braucht viel weniger Bandbreite, und die Animation bleibt flüssig, auch wenn der Pi kurz
  hängt. Dafür liegt dann Logik in der Firmware.

Dort wird auch der PIO-Treiber gebaut, und dort muss die Firmware die Helligkeitsgrenze
(`brightness` aus `CFG`) selbst erzwingen.

### Pro Micro: Arduino

- **Firmware:** Kompiliert als `arduino:avr:micro`. Der Klon meldet sich als Arduino Micro
  (2341:8037), Pinbelegung und 16 MHz passen. arduino-cli liegt in `~/.local/bin` und wird von
  `setup.sh` installiert.
- **Generische Firmware:** Sie setzt nur 16-Bit-Masken. Weil die Relaiskette Kurzschlüsse in der
  Hardware ausschließt, muss sie nichts über Ventilatoren wissen. Die Umrechnung von Stufe zu
  Relais steht in `protocol.fan_bits()`.
- **Mindestdauer pro Stufe** (gegen Relaisklappern) ist noch nicht umgesetzt. Sie gehört in
  Meilenstein 2 auf die Pi-Seite, zusammen mit einer Hysterese an den Geschwindigkeitsschwellen.
- **Failsafe:** Kommt 1 s lang kein `R`, gehen alle Relais aus, außer denen in der Keep-Maske.
  Die Keep-Maske ist `keep_on_timeout` in `config.yaml`, aktuell nur der Fernseher. Das ist
  getestet: Wenn die Software hängt oder neu startet, gehen die Ventilatoren aus, das Bild bleibt.
- **Polarität:** Die Firmware nimmt ein active-low Relaisboard an. Das ist eine Compile-Zeit-
  Konstante und keine Einstellung, damit sie schon vor dem ersten Kontakt zum Pi stimmt.
- **Kein Watchdog:** Bei manchen Caterina-Bootloadern von Klonen führt ein Watchdog-Reset zu einer
  Boot-Schleife im Bootloader, und die Firmware ist sehr einfach.

## Audio

### Zwei virtuelle Sinks

`ferrari-music` und `ferrari-effects` sind PipeWire-Loopbacks
([setup/pipewire/50-ferrari.conf](../setup/pipewire/50-ferrari.conf)) und leiten auf den
Standard-Ausgang weiter. Die Lautstärke wird am Sink gesetzt, nicht im Programm, das abspielt.

**Für die nächsten Meilensteine:** Jeder Ton muss auf den richtigen Sink:
- Prozesse, die über PulseAudio ausgeben, bekommen `PULSE_SINK=ferrari-music` bzw.
  `ferrari-effects` als Umgebungsvariable, z.B. ein CD-Player wie mpv. Auch SDL/pygame gibt
  meist über den PulseAudio-Treiber aus und beachtet dann `PULSE_SINK`.
- Über PipeWire direkt geht es mit `target.object`, über ALSA mit dem PipeWire-Gerät und
  `PIPEWIRE_NODE`.
- Effekte und Motorsound kommen aus demselben Python-Prozess, die Musik aus einem eigenen. Das
  passt gut: Der Python-Prozess setzt `PULSE_SINK=ferrari-effects` vor der Initialisierung des
  Mixers, der CD-Player bekommt `ferrari-music`.

### Dauerhaft laufende Sinks

PipeWire verwirft Lautstärkeänderungen an einem Loopback-Sink, solange er im Ruhezustand
(SUSPENDED) ist. Das wurde in dieser Session beobachtet: `pactl` meldete Erfolg, der Wert blieb
bei 100 %. Deshalb haben beide Sinks `node.always-process = true`.

Folgen:
- Der DAC bleibt ständig aktiv. Das ist gewollt: kein Knacken beim Aufwachen und keine
  Verzögerung beim ersten Motorgeräusch.
- Es kostet etwas CPU. Auf dem Pi 5 war in `top` nichts zu sehen.

### Weitere Audio-Einstellungen

- **Feste Rate 48 kHz**, 256 Samples pro Zyklus (5,3 ms). Die CD (44,1 kHz) wird umgerechnet,
  dafür gibt es kein hörbares Umschalten der Rate. Braucht der Motorsound kürzere Latenz, wird
  die Zyklusgröße verkleinert. Wenn es knackt, vergrößert man sie.
- **HDMI-Audio ist abgeschaltet**
  ([setup/wireplumber/50-ferrari.conf](../setup/wireplumber/50-ferrari.conf)), sonst würde Ton an
  den Fernseher gehen.
- **Ohne DAC** hängen sich die beiden Sinks gegenseitig hintereinander, weil es keinen anderen
  Ausgang gibt. Das ist harmlos, aber Hörtests sind erst mit DAC möglich.
- **Pegel des DAC:** Muss beim ersten Test mit DAC auf 100 % bzw. 0 dB gestellt werden. Geregelt
  wird ausschließlich an den virtuellen Sinks.
- **Lautstärken nach dem Neustart:** Das Programm setzt sie beim Start aus `state.json`. Den
  eigenen Speicher von WirePlumber in `~/.local/state` würde das Overlay-FS ohnehin bei jedem
  Neustart verwerfen.
- Die Lautstärke wird asynchron per `pactl` gesetzt. Schnelles Drehen fasst ein eigener Thread zu
  einem Aufruf pro Sink zusammen, die Hauptschleife blockiert nie. Die Prozentwerte von `pactl`
  sind kubisch skaliert und damit ungefähr gehörrichtig.

### Getestet mit simulierten Drehgebern

| Drehung | Erwartet | Ergebnis |
|---|---|---|
| Musik +5 Raststufen | 50 % → 65 % | 65 % |
| Effekte −3 Raststufen | 50 % → 41 % | 41 % |
| Musik zweimal eine halbe Raststufe | zusammen eine Stufe: 68 % | 68 % |
| Effekte −100 Raststufen | bleibt bei 0 % | 0 % |

Nach 2 s wird gespeichert. Nach einem Neustart setzt das Programm die gespeicherten Werte wieder,
auch wenn die Sinks zwischendurch verstellt wurden.

## System auf dem Pi

- **Benutzerdienst statt Systemdienst:** `ferrari.service` liegt in `/etc/systemd/user/` und läuft
  dank linger ohne Login. Grund: PipeWire ist ein Benutzerdienst, ein Systemdienst kann nicht
  sauber darauf warten. `setup.sh` entfernt den alten Systemdienst.
- **Logs:** `journalctl _SYSTEMD_USER_UNIT=ferrari.service`. `journalctl --user -u ferrari` findet
  nichts, weil das Journal nicht dauerhaft gespeichert wird. Das passt zum späteren Overlay-FS.
- **Autostart** ist noch nicht aktiviert: `systemctl --user enable --now ferrari`. Solange der
  Dienst läuft, belegt er die seriellen Schnittstellen exklusiv. Monitor und Flash-Skripte
  brauchen sie frei; die Flash-Skripte stoppen den Dienst selbst.
- **Display:** `SDL_VIDEODRIVER=kmsdrm` ist gesetzt, aber ungetestet. Offen ist, ob ein
  Benutzerdienst ohne Login-Sitzung DRM-Master werden darf. Das muss zu Beginn von Meilenstein 5
  geprüft werden, notfalls mit einem udev-/seat-Workaround oder doch als Systemdienst mit
  `XDG_RUNTIME_DIR`.
- **DAC-Overlay** ist jetzt `rpi-dacpro` (passend zum Raspberry Pi DAC Pro). Der HAT hat ein EEPROM,
  würde also auch automatisch erkannt.
- **udev:**
  - feste Namen `/dev/ferrari-wheel`, `/dev/ferrari-pico`, `/dev/ferrari-relay`
  - Bootloader-Zugriff für `picotool` ohne root (Gruppe plugdev)
  - Die Pico-Regel greift erst mit MicroPython (Vendor-ID 2e8a); die alte Pinscape-Firmware hatte 1209.

### Entwicklungsablauf

- Am PC entwickeln, mit `tools/deploy.sh` per rsync auf den Pi bringen. Der Pi braucht keinen
  Schreibzugriff auf das GitHub-Repository und braucht auch keinen.
- Nach einem `deploy.sh` weicht der Klon auf dem Pi vom letzten Commit ab. Zum Aufräumen auf dem
  Pi: `git fetch && git reset --hard origin/master`.
- **Tests:** `.venv/bin/python -m pytest` auf dem Pi. Am PC braucht es eine venv mit
  `requirements-dev.txt`, pyyaml und pyserial.
- `t80_test.py` ist entfernt. `tools/monitor.py` zeigt Lenkrad, Pedale, alle Konsoleneingänge und
  die Relais live an und kann Relais schalten.

## Offene Punkte aus Meilenstein 0

- **DAC** fehlt noch (höhere Stiftleiste). Danach: Hörtest, DAC-Pegel auf 100 %, prüfen, dass
  der DAC Standard-Ausgang ist und beide Sinks darauf weiterleiten.
- **Ab- und Wiederanstecken im laufenden Betrieb:** Das Neuverbinden ist bisher nur über
  Neustarts getestet (Watchdog-Test), noch nicht durch echtes Abstecken.
- **Konsole** ist noch nicht verdrahtet: Raststufen der Drehgeber, Entprellzeit und Glättung der
  Potis mit echter Hardware prüfen.
- **Relaisboard** ist noch nicht angeschlossen: Polarität prüfen (active-low?).
