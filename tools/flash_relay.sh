#!/usr/bin/env bash
# Kompiliert die Relais-Firmware und spielt sie auf den Pro Micro. Auf dem Pi ausführen.
#
# arduino-cli löst den Bootloader per 1200-Baud-Reset selbst aus. Klappt das nicht
# (z. B. bei kaputter Firmware): RST zweimal kurz gegen GND tippen und sofort starten.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLI="$HOME/.local/bin/arduino-cli"
# Pro-Micro-Klone mit 16 MHz laufen als "Arduino Micro" (gleiche Pinbelegung, USB-ID 2341:8037)
FQBN=arduino:avr:micro
DEV=/dev/ferrari-relay

systemctl --user stop ferrari 2>/dev/null || true

"$CLI" compile --fqbn "$FQBN" "$REPO/firmware/relay"
[[ -e $DEV ]] || { echo "$DEV fehlt. Ist der Pro Micro angesteckt?" >&2; exit 1; }
"$CLI" upload --fqbn "$FQBN" -p "$(readlink -f "$DEV")" "$REPO/firmware/relay"
echo "Fertig."
