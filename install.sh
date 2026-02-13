#!/bin/bash
# Ring Unraid Dashboard - Install Script
# Run this on your Unraid server

set -e

APPDATA="/mnt/user/appdata/ring-unraid"

echo "=== Ring Unraid Dashboard Installer ==="
echo ""

# Create directories
echo "Creating directories..."
mkdir -p "$APPDATA/mosquitto/config"
mkdir -p "$APPDATA/mosquitto/data"
mkdir -p "$APPDATA/mosquitto/log"
mkdir -p "$APPDATA/ring-mqtt"
mkdir -p "$APPDATA/snapshots"

# Copy mosquitto config
echo "Setting up Mosquitto config..."
cp mosquitto.conf "$APPDATA/mosquitto/config/mosquitto.conf"

# Create ring-mqtt config if not exists
if [ ! -f "$APPDATA/ring-mqtt/config.json" ]; then
    echo "Creating ring-mqtt config..."
    SERVER_IP=$(hostname -I | awk '{print $1}')
    cat > "$APPDATA/ring-mqtt/config.json" << EOF
{
  "mqtt_url": "mqtt://${SERVER_IP}:1883",
  "mqtt_options": "",
  "livestream_user": "",
  "livestream_pass": "",
  "disarm_code": "",
  "enable_cameras": true,
  "enable_modes": false,
  "enable_panic": false,
  "snapshot_mode": "interval",
  "snapshot_interval": 300,
  "location_ids": [],
  "ring_token": ""
}
EOF
fi

# Start containers
echo "Starting Docker containers..."
docker compose up -d

# Install dashboard page
echo "Installing dashboard page..."
cp RingCameras.page /boot/config/plugins/user.scripts/pages/RingCameras.page 2>/dev/null || true
cp RingCameras.page /usr/local/emhttp/plugins/dynamix/RingCameras.page

# Add to boot script if not already there
if ! grep -q "RingCameras.page" /boot/config/go 2>/dev/null; then
    echo "Adding dashboard page to boot script..."
    sed -i '/emhttp &/a \\n# Ring Cameras Dashboard\ncp /boot/config/plugins/user.scripts/pages/RingCameras.page /usr/local/emhttp/plugins/dynamix/ 2>/dev/null' /boot/config/go
fi

SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Next steps:"
echo "1. Open http://${SERVER_IP}:55123 in your browser"
echo "2. Log in with your Ring email, password, and 2FA code"
echo "3. Snapshots will appear on your Unraid Dashboard under 'Ring Cameras'"
echo ""
echo "Optional: Create a names.json file to give cameras friendly names:"
echo "  echo '{\"DEVICE_ID\": \"Front Door\"}' > $APPDATA/snapshots/names.json"
echo "  Then restart: docker restart ring-snapshot-saver"
