# ==============================================
# Ring Snapshot Saver
# ==============================================
# This thing listens for Ring camera snapshots
# and saves them as jpg files. That's literally it.
# ==============================================

# we need this to talk to the MQTT broker
# MQTT is like a mailbox where ring-mqtt drops off pictures
import paho.mqtt.client as mqtt

# boring stuff we need for files and time
import os      # for saving files to disk
import time    # for timestamps on the snapshots
import re      # for cleaning up camera names (removing weird characters)
import json    # for reading the camera names config file

# ==============================================
# SETTINGS - where to find stuff
# ==============================================

# the MQTT broker hostname - this is the mosquitto container
# if you renamed it in docker-compose, change it here too
MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")

# MQTT port - 1883 is the default, you probably don't need to change this
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))

# where to save the snapshot jpg files
# this folder is mounted from the host via docker volumes
SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "/snapshots")

# ==============================================
# CAMERA NAMES
# ==============================================
# ring-mqtt uses device IDs like "343ea4f040d1" which is ugly
# this dictionary maps those IDs to nice names like "Front Door"
# you can set these in names.json (see README)
camera_names = {}


def sanitize_name(name):
    """
    Takes a camera name and removes any weird characters.
    We only keep letters, numbers, dashes and underscores.
    So "Front Door!!" becomes "Front_Door__"
    This prevents weird filenames that could break stuff.
    """
    # replace anything that isn't a letter/number/dash/underscore with underscore
    return re.sub(r"[^a-zA-Z0-9_-]", "_", name)


def on_connect(client, userdata, flags, rc, properties=None):
    """
    This runs when we successfully connect to the MQTT broker.
    We subscribe to the topics where ring-mqtt publishes snapshots.
    Think of it like tuning into a radio station.
    """
    # just so we know what time stuff happens
    ts = time.strftime("%H:%M:%S")

    # rc=0 means success, anything else is bad
    print(ts + " - Connected to MQTT broker (rc=" + str(rc) + ")")

    # subscribe to ALL camera snapshot images
    # the + signs are wildcards (any location, any camera)
    # topic format: ring/<location_id>/camera/<device_id>/snapshot/image
    client.subscribe("ring/+/camera/+/snapshot/image")

    # also subscribe to camera info so we can learn camera names
    client.subscribe("ring/+/camera/+/info/state")

    # let the human know we're listening
    print(ts + " - Subscribed to snapshot and info topics")
    print(ts + " - Waiting for snapshots to arrive...")


def on_message(client, userdata, msg):
    """
    This runs every time we get a message from MQTT.
    Could be a snapshot image, could be camera info.
    We figure out what it is and deal with it.
    """
    # split the topic into parts so we can extract the camera ID
    # example: "ring/abc123/camera/def456/snapshot/image"
    # becomes: ["ring", "abc123", "camera", "def456", "snapshot", "image"]
    parts = msg.topic.split("/")

    # ---- CAMERA INFO MESSAGES ----
    # these tell us stuff about the camera (battery, wifi, etc)
    # we don't really need these but they're nice to have
    if "/info/state" in msg.topic and len(parts) >= 4 and msg.payload:
        # we could do something with camera info here
        # but honestly we don't need to
        return

    # ---- SNAPSHOT IMAGE MESSAGES ----
    # this is the good stuff - actual camera pictures!
    if "/snapshot/image" in msg.topic and len(parts) >= 4 and msg.payload:

        # grab the device ID from the topic (it's the 4th part, index 3)
        device_id = parts[3]

        # check if we have a friendly name for this camera
        # if not, just use the device ID (ugly but works)
        friendly_name = camera_names.get(device_id, device_id)

        # ---- SAVE THE SNAPSHOT ----

        # build the file path, like "/snapshots/Front_Door.jpg"
        filepath = os.path.join(SNAPSHOT_DIR, friendly_name + ".jpg")

        # write the binary image data to the jpg file
        # "wb" means write-binary (because it's an image, not text)
        with open(filepath, "wb") as f:
            f.write(msg.payload)

        # ---- SAVE THE TIMESTAMP ----

        # save when this snapshot was taken
        # the dashboard reads this to show "last updated: ..."
        timestamp_path = os.path.join(SNAPSHOT_DIR, friendly_name + "_timestamp.txt")
        with open(timestamp_path, "w") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

        # ---- LOG IT ----

        # calculate size in KB so we know the snapshot isn't empty/broken
        size_kb = len(msg.payload) / 1024

        # tell the human what we did
        ts = time.strftime("%H:%M:%S")
        print(ts + " - Saved " + friendly_name + ".jpg (" + str(int(size_kb)) + " KB)")

        # update the camera list file (dashboard uses this)
        save_camera_list()


def save_camera_list():
    """
    Writes a JSON file listing all cameras we've seen.
    The dashboard page reads this to know what to display.
    We rebuild it every time we get a new snapshot.
    Yes, this is a bit wasteful but who cares, it's tiny.
    """
    cameras = {}

    # look at every jpg file in the snapshot folder
    for f in os.listdir(SNAPSHOT_DIR):
        if f.endswith(".jpg"):
            # get the camera name from the filename (minus .jpg)
            name = f[:-4]

            # try to read the timestamp file for this camera
            ts_file = os.path.join(SNAPSHOT_DIR, name + "_timestamp.txt")
            ts = ""
            if os.path.exists(ts_file):
                with open(ts_file) as fh:
                    ts = fh.read().strip()

            # add this camera to our list
            cameras[name] = {
                "timestamp": ts,
                "size": os.path.getsize(os.path.join(SNAPSHOT_DIR, f))
            }

    # write the camera list to cameras.json
    with open(os.path.join(SNAPSHOT_DIR, "cameras.json"), "w") as f:
        json.dump(cameras, f)


def load_name_map():
    """
    Loads camera name mappings from names.json.

    If you create a file called names.json in the snapshots folder
    with contents like:
        {"abc123def456": "Front Door", "789ghi012jkl": "Backyard"}

    Then instead of ugly device IDs, you get nice names.
    This file is optional - if it doesn't exist, no worries.
    """
    names_file = os.path.join(SNAPSHOT_DIR, "names.json")

    # check if the file exists
    if os.path.exists(names_file):
        try:
            # try to read and parse it
            with open(names_file) as f:
                return json.load(f)
        except Exception:
            # if the JSON is broken, just ignore it
            # don't crash over a config file
            pass

    # no file found or it was broken, return empty dict
    return {}


# ==============================================
# MAIN - this is where the magic happens
# ==============================================

# create the MQTT client
# VERSION2 is the newer callback API (paho-mqtt 2.x requires this)
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# tell the client which functions to call when stuff happens
client.on_connect = on_connect    # when we connect to MQTT
client.on_message = on_message    # when we receive a message

# load camera name mappings if the user set them up
camera_names = load_name_map()
if camera_names:
    print("Loaded camera name mappings: " + str(camera_names))
else:
    print("No names.json found - using device IDs as camera names")
    print("(see README for how to set friendly names)")

# let's go!
print("Ring Snapshot Saver starting...")
print("Connecting to MQTT at " + MQTT_HOST + ":" + str(MQTT_PORT) + "...")

# keep trying to connect forever
# if MQTT goes down, we just wait and try again
while True:
    try:
        # connect to the MQTT broker
        client.connect(MQTT_HOST, MQTT_PORT)

        # this blocks forever, processing messages as they come in
        # it only returns if the connection drops
        client.loop_forever()

    except Exception as e:
        # something went wrong (broker down, network issue, etc)
        # just wait 10 seconds and try again
        print("Connection error: " + str(e) + ", retrying in 10s...")
        time.sleep(10)
