#!/bin/bash
# ==============================================
# Ring Unraid Dashboard - Install Script
# ==============================================
# Run this on your Unraid server and it sets everything up.
# That's it. One script. Done.
# ==============================================

# stop on any error (don't keep going if something breaks)
set -e

# where all the app data lives
APPDATA="/mnt/user/appdata/ring-unraid"

echo "=== Ring Unraid Dashboard Installer ==="
echo ""

# ------------------------------------------
# STEP 1: Create all the folders we need
# ------------------------------------------
echo "Creating directories..."

# mosquitto needs three folders: config, data, and logs
mkdir -p "$APPDATA/mosquitto/config"
mkdir -p "$APPDATA/mosquitto/data"
mkdir -p "$APPDATA/mosquitto/log"

# ring-mqtt stores its auth tokens here
mkdir -p "$APPDATA/ring-mqtt"

# this is where the camera snapshots end up as jpg files
mkdir -p "$APPDATA/snapshots"

# ------------------------------------------
# STEP 2: Set up Mosquitto config
# ------------------------------------------
echo "Setting up Mosquitto config..."

# copy our config file to where mosquitto expects it
cp mosquitto.conf "$APPDATA/mosquitto/config/mosquitto.conf"

# ------------------------------------------
# STEP 3: Create ring-mqtt config (first time only)
# ------------------------------------------
# we only create this if it doesn't exist yet
# if it already exists, the user has already logged in
# and we don't want to blow away their auth token
if [ ! -f "$APPDATA/ring-mqtt/config.json" ]; then
    echo "Creating ring-mqtt config..."

    # figure out this server's IP address
    # we need this for the MQTT connection URL
    SERVER_IP=$(hostname -I | awk '{print $1}')

    # write the config file
    # ring_token is empty - that's on purpose
    # ring-mqtt will fill it in when you log in via the web UI
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

# ------------------------------------------
# STEP 4: Start all Docker containers
# ------------------------------------------
echo "Starting Docker containers..."

# this starts mosquitto, ring-mqtt, and snapshot-saver
# -d means "detached" (run in background)
docker compose up -d

# ------------------------------------------
# STEP 5: Install the Unraid Dashboard page
# ------------------------------------------
echo "Installing dashboard page..."

# copy to the persistent location (survives reboots because /boot is on USB)
cp RingCameras.page /boot/config/plugins/user.scripts/pages/RingCameras.page 2>/dev/null || true

# copy to the active location (this is what Unraid actually serves)
cp RingCameras.page /usr/local/emhttp/plugins/dynamix/RingCameras.page

# ------------------------------------------
# STEP 6: Make it survive reboots
# ------------------------------------------
# Unraid wipes /usr/local/emhttp on every boot
# so we need to add a line to /boot/config/go that copies our page back
if ! grep -q "RingCameras.page" /boot/config/go 2>/dev/null; then
    echo "Adding dashboard page to boot script..."

    # add the copy command after the emhttp start line
    sed -i '/emhttp &/a \\n# Ring Cameras Dashboard\ncp /boot/config/plugins/user.scripts/pages/RingCameras.page /usr/local/emhttp/plugins/dynamix/ 2>/dev/null' /boot/config/go
fi

# ------------------------------------------
# DONE!
# ------------------------------------------
SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "=== Installation complete! ==="
echo ""
echo "Next steps:"
echo "  1. Open http://${SERVER_IP}:55123 in your browser"
echo "  2. Log in with your Ring email, password, and 2FA code"
echo "  3. Snapshots will appear on your Unraid Dashboard under 'Ring Cameras'"
echo ""
echo "Optional: Create a names.json file to give cameras friendly names:"
echo "  echo '{\"DEVICE_ID\": \"Front Door\"}' > $APPDATA/snapshots/names.json"
echo "  Then restart: docker restart ring-snapshot-saver"
echo ""
echo "To find your device IDs, wait for the first snapshots and then:"
echo "  ls $APPDATA/snapshots/*.jpg"
