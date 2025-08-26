FROM python:3.11-slim

# Install deps
RUN pip install --no-cache-dir plexapi requests

# Install cron
RUN apt-get update && apt-get install -y cron && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app.py .

# Pre-create log file
RUN touch /var/log/cron.log