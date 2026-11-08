# Der Plan

Ein "Auto" für ein Festival. Es ist eine einfache Konstruktion aus Holz und Alurohren. Es hat eine Sitzbank und ein Lenkrad, aber keinen Motor und keine Räder. Man kann sich reinsetzen und Musik hören. Es gibt allerlei Gimmicks.

## Eingabegeräte

- __Lenkrad und Pedale__: Ein Rennsimulator Kit (Thrustmaster T80) dient zur Steuerung des Autos. Am Lenkrad befinden sich zahlreiche Knöpfe, darunter zwei zur Schaltung des Gangs.
- __Zündungsschalter__: Ein Schalter in Form eines Schlosses, der mit dem "Autoschlüssel" bedient wird.
- __Mittelkonsole__: Eine Menge Schalter, Drehpotentiometer und Knöpfe. Die Funktionen der einzelnen Bedienelemente wird im zugehörigen Textabschnitt erklärt.
- __CD-Laufwerk__: Zum Abspielen von Musik. Zusammen mit Lautstärkeregler und Knöpfen zum Pausieren, Überspringen, einen Track zurück gehen und Stoppen der Wiedergabe in der Mittelkonsole platziert.
- __Bluetooth__: Man kann sich per Bluetooth verbinden, um Musik von seinem Handy anstelle des CD-Laufwerks abzuspielen. Wichtig: Motorgeräusche und andere Töne werden weiterhin ausgegeben.

## Ausgabegeräte

- Vier __Ventilatoren__ erzeugen Fahrtwind. Sie werden über ein Relaisboard gesteuert, sodass jeder Ventilator ein und ausgeschaltet und die Geschwindigkeit in drei Stufen angepasst werden kann. Das Relaisboard benötigt 12 digitale GPIO Pins. Falls die Pins am Pi knapp werden, könnte es nötig werden, einen Arduino dazwischen zu schalten.
- __Induktive Lautsprecher__ unter der Sitzbank spielen Musik ab und machen Motor- und Fahrgeräusche
- Ein monochromer __Röhrenfernseher__ mit 6 Zoll Bildiagonale und PAL Auflösung
- __Externe Lautsprecher__: Optional kann per 3.5 mm Klinke ein externes Lautsprechersystem angeschlossen werden. Ein Schalter entscheidet, auf welchen Lautsprechern die Musik abgespielt wird. Alles andere wird immer auf den integrierten Lautsprechern abgespielt.
- Mehrere __LED-Streifen__ mit einzeln steuerbaren LEDs hängen über der Motorhaube im rechten Winkel zur Sitzbank.
- Eine __Nebelmaschine__, als Auspuff getarnt
- Vier __Stroboskope__, zwei vorne in weiß, zwei hinten in rot
- Eine __Diskokugel__, motorisiert und beleuchtet

## Steuerung

Die zentrale Kontrolleinheit des Autos ist ein Raspberry Pi 5 mit 4 GB RAM. Der Pi hat einen Audio DAC Hat für besseren Sound. An den Pi sind alle Eingabe- und Ausgabegeräte direkt oder indirekt angeschlossen. Eine Software auf dem Pi liest die Eingabegeräte, simuliert ein rudimentäres virtuelles Auto (Geschwindigkeit, Drehzahl) und steuert dementsprechend die Ausgabegeräte. Die Software hat mehrere Modi.

### Standbymodus

Keine Motorengeräusche. Die Ventilatoren drehen nicht. Musik läuft weiterhin. Die Mittelkonsole und das CD Laufwerk bleiben aktiv. Auf dem Röhrenfernseher läuft ein Video in Endlosschleife. Wenn die Pedale betätigt werden, informiert der Fernseher, dass der Motor mit dem Schlüssel gestartet werden muss.

Dieser Modus wird aktiviert:

- Nach dem Start des Pis
- Nach längerer Inaktivität der Pedale
- Wenn der Zündungsschalter in einem anderen Modus betätigt wird
- Wenn der Motor abgewürgt wurde

### Fahrtmodus

Dieser Modus wird aktiviert, wenn des Zündschalter im Standby Modus betätigt wird.

Auf Basis der Eingabegeräte wird ein virtueller Ferrari mit Verbrennungsmotor und manueller Gangschaltung rudimentär simuliert. Mit den beiden Gangschaltern am Lenkrad lässt sich ein Gang einstellen. Das Gaspedal erhöht die virtuelle Geschwindigkeit des Autos. Das Bremspedal verringert sie. Aus Geschwindigkeit und Gang ergibt sich eine Drehzahl. Bei zu geringer Drehzahl wird der Motor abgewürgt. Die Reifen können bei abrupten Lenkmanövern, starker Beschleunigung oder Bremsen die Haftung verlieren. Mit zurückgelegter Distanz füllt sich ein "Nitro-Meter". Wenn das Nitro voll ist, kann man es aktivieren. Dadurch wird die Leistung des Motors für eine kurze Zeit erhöht.

Die integrierten Lautsprecher erzeugen Fahrtgeräusche basierend auf Geschwindigkeit, Gang, Drehzahl, und Reifenhaftung (Quietschgeräusche). Dazu gehören _nicht_ Fahrtwindgeräusche. Dafür sind die Ventilatoren da. Sie drehen sich je nach Geschwindigkeit schneller oder langsamer. Der Röhrenfernseher zeigt folgendes an:

- Geschwindigkeit in km/h als Zahl in der Mitte
- Drehzahl als Zahl und als Balken, der sich zu einer hohen maximalen Drehzahl füllt
- Ventilatorgeschwindigkeit mit einem Ventilatorsymbol und drei Balken
- Nitro-Meter als Balken

Wenn die Drehzahl gefährlich niedrig ist, blinken die LED-Streifen und der Röhrenfernseher. Auf dem Fernseher wird außerdem fett der Text "SCHALTEN!" angezeigt. Wird dennoch der Motor abgewürgt, zählt die Software mit und zeigt auf dem Bildschirm an, zum wievielten mal das jetzt schon passiert ist. Bei einer runden Anzahl (10*x) wird ein Konfettieffekt eingeblendet und eine Partytröte ist zu hören. Dann geht der Motor aus und das Auto wechselt in den Standby-Modus. Nitro kann mit einem Schalter in der Mittelkonsole aktiviert werden, sobald es verfügbar ist. Dann geht die Nebelmaschine im Auspuff an bis das Nitro verbraucht ist. Realitätsgetreues Fahrverhalten oder authentischer Motorsound sind unwichtig. Es sollte dennoch eindrucksvoll sein.

### Super-Turbo-Truthahn-Kicker-Modus

Eine Hommage an das Easter-Egg aus __DOOM__. Dieser Modus wird aktiviert, wenn der entsprechende Knopf in der Mittelkonsole betätigt wird. Der Fahrtmodus wird dabei gegebenenfalls pausiert. Nach dem Spiel wird der vorherige Modus wiederhergestellt. Es handelt sich um ein primitives 2D-Arcadespiel, bei dem man mit den Pedalen Truthähne treten muss. Auf dem Bildschirm erscheint ein Truthahn, eine Punktzahl und ein Balken, der die verbleibende Zeit anzeigt. Davor ein Paar gebeugte Beine. Wenn man fest genug in eins der Pedale tritt, streckt sich das entsprechende Bein aus und der der Truthahn wird getreten. Nach x Tritten stirbt der Truthahn und ein neuer erscheint. Ziel ist es, den Highscore zu knacken, bevor die Zeit ausläuft. Die Grafik und der Ton ist sehr einfach gehalten:
- Zwei Sprites für die Beine (ausgestreckt, gebeugt). Für die andere Seite gespiegelt.
- Drei Sprites für den Truthahn (normal, getreten, tot). Bei einem Tritt wird kurz das getreten Sprite angezeigt.
- Kurzer 8-bit loop im Hintergrund
- Soundeffekte: Treten, Truthahngeschrei, Punkte bekommen, Game Over, Highscore geknackt

### Modusübergreifende Funktionen

- Die Strobo-Scheinwerfer kennen drei Betriebsarten, die per Mittelkonsole umgeschaltet werden:
    - Aus
    - An: Konstante Helligkeit
    - Strobo: An und aus im Takt zur Musik
- Die Diskokugel macht einfach ihr Ding und kann nur an und ausgeschaltet werden.



## Meilensteine

1. Fahrsimulation ohne Ton mit Pedal und Lenkrad
2. Ventilatoren
3. Fahrtgeräusche erzeugen und über Pi an integrierte Lautsprecher ausgeben
4. Musik per CD-Laufwerk abspielen
5. Röhrenfernseher
6. LED Streifen
7. Externer Lautsprecheranschluss
8. Bluetooth
9. Super-Turbo-Truthahn-Kicker
10. Stroboskope
11. Nitro und Nebelmaschine
12. Diskokugel

## Offene Fragen

- Was für Stroboskope kommen zum Einsatz und wie werden sie gesteuert? LED-Stroboskope lassen sich oft farblich einstellen und es gibt welche mit integriertem Mikrofon, die zwischen Strobo und konstanter Beleuchtung umgeschaltet werden können. Allerdings mit einer Infrarot-Fernbedienung. Muss ich die Fernbedienung mit einer Infrarot-LED imitieren oder gibt es eine bessere Alternative?
- Was für eine Nebelmaschine und wie wird sie gesteuert?
- Wie werden Motor und Beleuchtung der Diskokugel an und ausgeschaltet?
- Wie funktioniert die Bluetooth-Verbindung und das Umschalten zwischen internen und externen Lautsprechern?
- Wie werden die LED-Streifen angesteuert?