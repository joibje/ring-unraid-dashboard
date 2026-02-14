# ==============================================
# Ring Snapshot Saver - Docker Container
# ==============================================
# This builds a tiny Python container that does ONE thing:
# listens for Ring snapshots on MQTT and saves them as jpg files.
# ==============================================

# start with a slim Python image (about 50MB)
# we don't need the full fat one, we're not doing machine learning here
FROM python:3-slim

# set the working directory inside the container
# this is where our code lives
WORKDIR /app

# copy the requirements file first (for Docker layer caching)
# this means if we change saver.py but not requirements.txt,
# Docker won't re-download paho-mqtt every time we rebuild
COPY requirements.txt .

# install our one dependency: paho-mqtt
# --no-cache-dir keeps the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# copy our actual code
COPY saver.py .

# run the saver script
# -u means unbuffered output, so we can see logs in real time
# without -u, Python buffers stdout and you see nothing in docker logs
CMD ["python", "-u", "saver.py"]
