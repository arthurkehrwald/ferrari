#!/usr/bin/env bash
# Richtet einen frischen Raspberry Pi 5 (Raspberry Pi OS Lite 64-bit, Bookworm oder neuer)
# für das Ferrari-Projekt ein. Idempotent: kann mehrfach ausgeführt werden.
#
#   cd ~/ferrari && ./setup/setup.sh
#
# Optional:
#   HOTSPOT=1 HOTSPOT_PASSWORD=... ./setup/setup.sh   # WLAN-Hotspot für SSH (siehe unten)
#
# Nicht Teil dieses Skripts: Overlay-FS (setup/harden.sh, erst ganz am Schluss).
set -euo pipefail

if [[ $EUID -eq 0 ]]; then
    echo "Bitte als normaler Benutzer ausführen (nutzt sudo selbst)." >&2
    exit 1
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="$(id -un)"
ARDUINO_CLI_VERSION=1.5.1
CONFIG=/boot/firmware/config.txt
MARK_BEGIN="# >>> ferrari >>>"
MARK_END="# <<< ferrari <<<"

log() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

log "Pakete installieren"
sudo apt-get update
sudo apt-get -y full-upgrade
sudo apt-get -y install \
    git acl alsa-utils rsync curl \
    python3-venv python3-pygame python3-yaml python3-serial \
    pipewire pipewire-pulse pipewire-alsa wireplumber pulseaudio-utils \
    picotool

log "Benutzergruppen"
sudo usermod -aG input,dialout,audio,video,render,cdrom "$USER_NAME"

log "Raspberry Pi DAC Pro (rpi-dacpro) in $CONFIG"
# Eingebautes Audio aus, Pi 5 hat ohnehin keine Klinkenbuchse.
sudo sed -i 's/^dtparam=audio=on/dtparam=audio=off/' "$CONFIG"
sudo sed -i "/^$MARK_BEGIN\$/,/^$MARK_END\$/d" "$CONFIG"
sudo tee -a "$CONFIG" >/dev/null <<EOF
$MARK_BEGIN
dtoverlay=rpi-dacpro
# Hardware-Watchdog des SoC
dtparam=watchdog=on
$MARK_END
EOF

log "udev-Regeln"
sudo install -m 644 "$REPO/setup/udev/99-ferrari.rules" /etc/udev/rules.d/99-ferrari.rules
sudo udevadm control --reload
sudo udevadm trigger

log "Hardware-Watchdog in systemd"
sudo mkdir -p /etc/systemd/system.conf.d
printf '[Manager]\nRuntimeWatchdogSec=15\n' | sudo tee /etc/systemd/system.conf.d/10-ferrari-watchdog.conf >/dev/null

log "PipeWire auch ohne Login-Session"
sudo loginctl enable-linger "$USER_NAME"

log "PipeWire-Routing (virtuelle Sinks, HDMI-Audio aus)"
sudo install -D -m 644 "$REPO/setup/pipewire/50-ferrari.conf" /etc/pipewire/pipewire.conf.d/50-ferrari.conf
sudo install -D -m 644 "$REPO/setup/wireplumber/50-ferrari.conf" /etc/wireplumber/wireplumber.conf.d/50-ferrari.conf
systemctl --user restart pipewire pipewire-pulse wireplumber || echo "PipeWire-Neustart fehlgeschlagen, greift nach dem Reboot"

log "Python-venv"
python3 -m venv --system-site-packages "$REPO/.venv"
if [[ -f "$REPO/requirements.txt" ]]; then
    "$REPO/.venv/bin/pip" install -r "$REPO/requirements.txt"
fi

log "arduino-cli $ARDUINO_CLI_VERSION (Firmware für den Pro Micro)"
mkdir -p "$HOME/.local/bin"
if ! "$HOME/.local/bin/arduino-cli" version 2>/dev/null | grep -q "Version: $ARDUINO_CLI_VERSION"; then
    curl -fsSL "https://github.com/arduino/arduino-cli/releases/download/v$ARDUINO_CLI_VERSION/arduino-cli_${ARDUINO_CLI_VERSION}_Linux_ARM64.tar.gz" \
        | tar -xz -C "$HOME/.local/bin" arduino-cli
fi
"$HOME/.local/bin/arduino-cli" core update-index
"$HOME/.local/bin/arduino-cli" core install arduino:avr

log "Persistentes Datenverzeichnis"
# Wird von harden.sh bei Bedarf durch eine eigene Partition ersetzt.
sudo mkdir -p /var/lib/ferrari
sudo chown "$USER_NAME": /var/lib/ferrari

log "systemd-Benutzerdienst installieren (noch nicht aktiviert)"
# Früher ein Systemdienst; der läuft vor PipeWire los und wird deshalb entfernt.
if [[ -f /etc/systemd/system/ferrari.service ]]; then
    sudo systemctl disable --now ferrari.service || true
    sudo rm /etc/systemd/system/ferrari.service
    sudo systemctl daemon-reload
fi
sed -e "s|@REPO@|$REPO|g" "$REPO/setup/systemd/ferrari.service" \
    | sudo tee /etc/systemd/user/ferrari.service >/dev/null
systemctl --user daemon-reload
echo "Autostart aktivieren:  systemctl --user enable --now ferrari"

if [[ "${HOTSPOT:-0}" == "1" ]]; then
    log "WLAN-Hotspot"
    : "${HOTSPOT_PASSWORD:?HOTSPOT_PASSWORD setzen (mindestens 8 Zeichen)}"
    SSID="${HOTSPOT_SSID:-ferrari}"
    sudo nmcli connection delete ferrari-hotspot 2>/dev/null || true
    sudo nmcli connection add type wifi ifname wlan0 con-name ferrari-hotspot ssid "$SSID" \
        autoconnect yes wifi.mode ap wifi.band bg ipv4.method shared \
        wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$HOTSPOT_PASSWORD"
    echo "Hotspot '$SSID' eingerichtet. Achtung: wlan0 kann dann kein anderes WLAN mehr nutzen."
else
    echo
    echo "Hotspot übersprungen (HOTSPOT=1 zum Aktivieren). Für die Entwicklung besser am Heim-WLAN lassen."
fi

log "Fertig"
echo "Jetzt neu starten (DAC-Overlay, Gruppen):  sudo reboot"
echo "Danach prüfen:"
echo "  aplay -l                      # DAC Pro muss auftauchen"
echo "  wpctl status                  # PipeWire sieht den DAC"
echo "  ls -l /dev/ferrari-*          # Lenkrad, Pico, Pro Micro"
echo "  .venv/bin/python -m tools.monitor   # alle Eingänge live"
