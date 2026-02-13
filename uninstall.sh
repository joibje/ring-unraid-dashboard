#!/bin/bash
# Ring Unraid Dashboard - Uninstall Script

echo "=== Ring Unraid Dashboard Uninstaller ==="
echo ""

read -p "Remove all containers and data? (y/N) " confirm
if [ "$confirm" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

echo "Stopping containers..."
docker compose down 2>/dev/null || true
docker stop ring-mqtt ring-mosquitto ring-snapshot-saver 2>/dev/null || true
docker rm ring-mqtt ring-mosquitto ring-snapshot-saver 2>/dev/null || true

echo "Removing dashboard page..."
rm -f /usr/local/emhttp/plugins/dynamix/RingCameras.page
rm -f /boot/config/plugins/user.scripts/pages/RingCameras.page

read -p "Remove all snapshot data? (y/N) " confirm_data
if [ "$confirm_data" = "y" ]; then
    echo "Removing data..."
    rm -rf /mnt/user/appdata/ring-unraid
fi

echo ""
echo "Uninstalled."
