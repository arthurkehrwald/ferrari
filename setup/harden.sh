#!/usr/bin/env bash
# Schreibschutz für das Root-Dateisystem (Overlay-FS). Erst ausführen, wenn alles läuft!
#
# Voraussetzung: eine ext4-Partition mit dem Label "ferrari-data" für persistente Daten
# (Abwürg-Zähler, Highscore, Lautstärken). Anlegen, z. B. mit gparted am PC, bevor das
# Root-Dateisystem die ganze SD-Karte füllt:
#   - Root auf ca. 12 GB verkleinern, dahinter eine ext4-Partition "ferrari-data" mit ~1 GB.
#   - Achtung: Ein frisch geflashtes Image vergrößert das Root-FS beim ersten Start.
#     Die Partition also vor dem ersten Start oder auf einer Kopie des Systems anlegen
#     und den Start danach prüfen.
#
# Rückgängig: sudo raspi-config nonint disable_overlayfs && sudo reboot
set -euo pipefail

if ! blkid -L ferrari-data >/dev/null 2>&1; then
    echo "Keine Partition mit Label 'ferrari-data' gefunden. Abbruch." >&2
    exit 1
fi

sudo mkdir -p /var/lib/ferrari
if ! grep -q 'LABEL=ferrari-data' /etc/fstab; then
    echo 'LABEL=ferrari-data /var/lib/ferrari ext4 defaults,noatime,commit=5 0 2' | sudo tee -a /etc/fstab >/dev/null
fi
sudo mount -a
sudo chown "$(id -un)": /var/lib/ferrari

# Overlay-FS aktivieren, /boot/firmware ebenfalls schreibgeschützt
sudo raspi-config nonint enable_overlayfs
sudo raspi-config nonint enable_bootro
echo "Neustart nötig:  sudo reboot"
