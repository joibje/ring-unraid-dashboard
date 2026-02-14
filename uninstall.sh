#!/bin/bash
# ==============================================
# Ring Unraid Dashboard - Uninstall Script
# ==============================================
# Removes everything. Asks before deleting data.
# ==============================================

echo "=== Ring Unraid Dashboard Uninstaller ==="
echo ""

# ask before doing anything destructive
# nobody likes scripts that delete stuff without asking
read -p "Remove all containers and data? (y/N) " confirm
if [ "$confirm" != "y" ]; then
    echo "Cancelled. Nothing was changed."
    exit 0
fi

# ------------------------------------------
# STEP 1: Stop and remove Docker containers
# ------------------------------------------
echo "Stopping containers..."

# try docker compose first (cleaner)
docker compose down 2>/dev/null || true

# also try removing by name (in case compose doesn't work)
docker stop ring-mqtt ring-mosquitto ring-snapshot-saver 2>/dev/null || true
docker rm ring-mqtt ring-mosquitto ring-snapshot-saver 2>/dev/null || true

# ------------------------------------------
# STEP 2: Remove the dashboard page
# ------------------------------------------
echo "Removing dashboard page..."

# remove from active location
rm -f /usr/local/emhttp/plugins/dynamix/RingCameras.page

# remove from persistent location
rm -f /boot/config/plugins/user.scripts/pages/RingCameras.page

# ------------------------------------------
# STEP 3: Remove data (optional)
# ------------------------------------------
# ask separately because maybe they want to keep their snapshots
read -p "Also remove all snapshot data and configs? (y/N) " confirm_data
if [ "$confirm_data" = "y" ]; then
    echo "Removing data..."
    rm -rf /mnt/user/appdata/ring-unraid
fi

echo ""
echo "Uninstalled. Goodbye!"
