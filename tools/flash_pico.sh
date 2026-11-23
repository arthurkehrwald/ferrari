#!/usr/bin/env bash
# Spielt die Pico-Firmware auf. Auf dem Pi ausführen.
#
#   tools/flash_pico.sh               # nur firmware/pico/main.py kopieren (normaler Fall)
#   tools/flash_pico.sh --micropython # zusätzlich MicroPython selbst (neu) installieren
#
# MicroPython kommt per picotool drauf. Läuft schon MicroPython, wechselt das Skript
# selbst in den Bootloader; sonst den Pico mit gedrückter BOOTSEL-Taste anstecken.
set -euo pipefail

MICROPYTHON=RPI_PICO-20260824-v1.29.0.uf2
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MPREMOTE="$REPO/.venv/bin/mpremote"
DEV=/dev/ferrari-pico
CACHE="$HOME/.cache/ferrari"

systemctl --user stop ferrari 2>/dev/null || true

in_bootloader() { picotool info >/dev/null 2>&1; }

if [[ "${1:-}" == "--micropython" ]] || ! [[ -e $DEV ]]; then
    if ! in_bootloader; then
        if [[ -e $DEV ]]; then
            echo "Wechsle in den Bootloader ..."
            "$MPREMOTE" connect "$DEV" bootloader || true
        fi
        for _ in $(seq 20); do in_bootloader && break; sleep 0.5; done
    fi
    if ! in_bootloader; then
        echo "Kein Pico gefunden. Mit gedrückter BOOTSEL-Taste anstecken und erneut starten." >&2
        exit 1
    fi
    mkdir -p "$CACHE"
    if [[ ! -f "$CACHE/$MICROPYTHON" ]]; then
        curl -fL -o "$CACHE/$MICROPYTHON.part" "https://micropython.org/resources/firmware/$MICROPYTHON"
        mv "$CACHE/$MICROPYTHON.part" "$CACHE/$MICROPYTHON"
    fi
    echo "Installiere $MICROPYTHON ..."
    picotool load -x "$CACHE/$MICROPYTHON"
    for _ in $(seq 20); do [[ -e $DEV ]] && break; sleep 0.5; done
    [[ -e $DEV ]] || { echo "Pico meldet sich nach dem Flashen nicht." >&2; exit 1; }
    sleep 1
fi

echo "Kopiere main.py ..."
"$MPREMOTE" connect "$DEV" cp "$REPO/firmware/pico/main.py" :main.py + reset
echo "Fertig."
