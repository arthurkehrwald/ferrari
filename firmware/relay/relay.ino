// Firmware für den Arduino Pro Micro (ATmega32u4, 5 V / 16 MHz): 16 Relais.
// Protokoll: docs/protocol.md. Aufspielen: tools/flash_relay.sh
//
// Sicherheit:
//  - Beim Start sind alle Relais aus, bevor die Pins zu Ausgängen werden.
//  - Kommt 1 s lang kein "R", gehen alle Relais aus, die nicht in der Keep-Maske stehen
//    (z. B. der Fernseher). Die Keep-Maske ist nach dem Start 0.
//  - Kurzschlüsse zwischen Ventilatorwicklungen schließt die Verdrahtung aus,
//    deshalb ist hier jede Maske erlaubt.

#define VERSION 1
#define TIMEOUT_MS 1000

// Die meisten Relaisboards mit Optokopplern schalten bei LOW. Sonst auf 0 setzen.
#define ACTIVE_LOW 1

// Relais-Kanal 0..15 -> Arduino-Pin. D0/D1 (RX/TX) bleiben frei.
const uint8_t PINS[16] = {2, 3, 4, 5, 6, 7, 8, 9, 10, 16, 14, 15, A0, A1, A2, A3};

const uint8_t ON_LEVEL = ACTIVE_LOW ? LOW : HIGH;
const uint8_t OFF_LEVEL = ACTIVE_LOW ? HIGH : LOW;

uint16_t mask = 0;
uint16_t keep = 0;
unsigned long lastRx = 0;
bool timedOut = true;  // vor dem ersten "R" nichts melden
char buf[24];
uint8_t len = 0;
bool overflow = false;

void applyMask(uint16_t m) {
  mask = m;
  for (uint8_t i = 0; i < 16; i++) {
    digitalWrite(PINS[i], (m >> i) & 1 ? ON_LEVEL : OFF_LEVEL);
  }
}

void hello() {
  Serial.print(F("HELLO relay "));
  Serial.println(VERSION);
}

void reportMask() {
  char out[8];
  snprintf(out, sizeof out, "R %04X", mask);
  Serial.println(out);
}

// "XXXX" mit genau vier Hex-Ziffern
bool parseMask(const char *s, uint16_t *out) {
  if (strlen(s) != 4) return false;
  char *end;
  unsigned long v = strtoul(s, &end, 16);
  if (*end != '\0') return false;
  *out = (uint16_t)v;
  return true;
}

void handleLine() {
  buf[len] = '\0';
  uint16_t m;
  if (buf[0] == '?' && buf[1] == '\0') {
    hello();
  } else if (buf[0] == 'R' && buf[1] == ' ' && parseMask(buf + 2, &m)) {
    lastRx = millis();  // nur "R" zählt als Heartbeat
    timedOut = false;
    applyMask(m);
    reportMask();
  } else if (buf[0] == 'K' && buf[1] == ' ' && parseMask(buf + 2, &m)) {
    keep = m;
  } else if (len > 0) {
    Serial.println(F("ERR unbekannt"));
  }
}

void setup() {
  for (uint8_t i = 0; i < 16; i++) {
    // Erst Pegel setzen, dann Ausgang: kein kurzes Anziehen beim Start
    digitalWrite(PINS[i], OFF_LEVEL);
    pinMode(PINS[i], OUTPUT);
  }
  Serial.begin(115200);  // Baudrate egal (USB), aber nie 1200: das startet den Bootloader
  hello();
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      if (!overflow) handleLine();
      len = 0;
      overflow = false;
    } else if (c != '\r') {
      if (len < sizeof buf - 1) buf[len++] = c;
      else overflow = true;
    }
  }
  if (!timedOut && millis() - lastRx > TIMEOUT_MS) {
    timedOut = true;
    applyMask(mask & keep);
    Serial.println(F("T"));
    reportMask();
  }
}
