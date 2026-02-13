import paho.mqtt.client as mqtt
import os
import time
import re
import json

MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/snapshots")

# Auto-discovered camera names from ring-mqtt
camera_names = {}

def sanitize_name(name):
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)

def on_connect(client, userdata, flags, rc, properties=None):
    ts = time.strftime("%H:%M:%S")
    print(ts + " - Connected to MQTT broker (rc=" + str(rc) + ")")
    client.subscribe("ring/+/camera/+/snapshot/image")
    client.subscribe("ring/+/camera/+/info/state")
    print(ts + " - Subscribed to snapshot and info topics")

def on_message(client, userdata, msg):
    parts = msg.topic.split("/")

    # Learn camera names from info topics
    # Topic: ring/<location>/camera/<device_id>/info/state
    if "/info/state" in msg.topic and len(parts) >= 4 and msg.payload:
        device_id = parts[3]
        try:
            info = json.loads(msg.payload)
            # ring-mqtt includes device name in the log prefix [Name]
            # but info state has other useful data
        except Exception:
            pass
        return

    # Save snapshot images
    # Topic: ring/<location>/camera/<device_id>/snapshot/image
    if "/snapshot/image" in msg.topic and len(parts) >= 4 and msg.payload:
        device_id = parts[3]
        friendly_name = camera_names.get(device_id, device_id)
        filepath = os.path.join(SNAPSHOT_DIR, friendly_name + ".jpg")
        with open(filepath, "wb") as f:
            f.write(msg.payload)
        timestamp_path = os.path.join(SNAPSHOT_DIR, friendly_name + "_timestamp.txt")
        with open(timestamp_path, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
        size_kb = len(msg.payload) / 1024
        ts = time.strftime("%H:%M:%S")
        print(ts + " - Saved " + friendly_name + ".jpg (" + str(int(size_kb)) + " KB)")

        # Save camera list for the dashboard
        save_camera_list()

def save_camera_list():
    """Write a JSON file listing all known cameras for the dashboard."""
    cameras = {}
    for f in os.listdir(SNAPSHOT_DIR):
        if f.endswith(".jpg"):
            name = f[:-4]
            ts_file = os.path.join(SNAPSHOT_DIR, name + "_timestamp.txt")
            ts = ""
            if os.path.exists(ts_file):
                with open(ts_file) as fh:
                    ts = fh.read().strip()
            cameras[name] = {"timestamp": ts, "size": os.path.getsize(os.path.join(SNAPSHOT_DIR, f))}
    with open(os.path.join(SNAPSHOT_DIR, "cameras.json"), "w") as f:
        json.dump(cameras, f)

def load_name_map():
    """Load optional camera name mapping from names.json."""
    names_file = os.path.join(SNAPSHOT_DIR, "names.json")
    if os.path.exists(names_file):
        try:
            with open(names_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

# Load user-defined name mappings (device_id -> friendly name)
camera_names = load_name_map()
if camera_names:
    print("Loaded camera name mappings: " + str(camera_names))

print("Ring Snapshot Saver starting...")
while True:
    try:
        client.connect(MQTT_HOST, MQTT_PORT)
        client.loop_forever()
    except Exception as e:
        print("Connection error: " + str(e) + ", retrying in 10s...")
        time.sleep(10)
