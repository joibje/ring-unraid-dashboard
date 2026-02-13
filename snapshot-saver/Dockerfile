FROM python:3-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY saver.py .
CMD ["python", "-u", "saver.py"]
