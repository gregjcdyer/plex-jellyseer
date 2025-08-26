# Plex Watchlist → Jellyseerr Sync

This project automatically syncs your **Plex Watchlist** with **Jellyseerr**, requesting new movies/shows every 10 minutes.

It runs inside a Docker container with a cron scheduler, so you don’t need to install Python or dependencies on your host machine.

---

## ✨ Features

- Fetches your Plex **personal watchlist**
- Searches Jellyseerr for each title
- Skips items that are already requested or available
- Automatically submits new requests
- Runs every **10 minutes** inside the container

---

## 📦 Requirements

- Docker & Docker Compose installed
- Plex account & server token
- Jellyseerr instance with API key

---

## ⚙️ Configuration

Edit the environment variables in `docker-compose.yml`:

```yaml
environment:
  - PLEX_URL=http://your-plex-server:32400
  - PLEX_TOKEN=your_plex_token_here
  - PLEX_USERNAME=your_plex_username
  - PLEX_PASSWORD=your_plex_password
  - JELLYSEERR_URL=http://your-jellyseerr-server:5055
  - JELLYSEERR_API=your_jellyseerr_api_key_here
```

## 🚀 Running locally

```bash
# Install deps
pip install plexapi requests

# Run once
python app.py
```

## 🚀 Running with Docker (Scheduled)

1. Build and start the container:

```
docker-compose up --build -d
```

2. Check logs:

```
docker logs -f plex-to-jellyseerr
```

3. or inside the container:

```
docker exec -it plex-to-jellyseerr tail -f /var/log/cron.log
```
