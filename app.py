import os
import requests
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

PLEX_URL        = os.getenv("PLEX_URL")
PLEX_TOKEN      = os.getenv("PLEX_TOKEN")
PLEX_USERNAME   = os.getenv("PLEX_USERNAME")
PLEX_PASSWORD   = os.getenv("PLEX_PASSWORD")
JELLYSEERR_URL  = os.getenv("JELLYSEERR_URL")
JELLYSEERR_API  = os.getenv("JELLYSEERR_API")


def get_plex_watchlist():
    plex = PlexServer(PLEX_URL, PLEX_TOKEN)
    account = MyPlexAccount(PLEX_USERNAME, PLEX_PASSWORD)
    return account.watchlist()


def jellyseerr_search(query):
    url = f"{JELLYSEERR_URL}/api/v1/search"
    headers = {"X-Api-Key": JELLYSEERR_API}
    params = {"query": query}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()


def jellyseerr_media_status(tmdb_id, media_type):
    """Check if media is already requested/available in Jellyseerr"""
    url = f"{JELLYSEERR_URL}/api/v1/media/{tmdb_id}"
    headers = {"X-Api-Key": JELLYSEERR_API}
    r = requests.get(url, headers=headers)
    if r.status_code == 404:
        return None  # Not in Jellyseerr yet
    r.raise_for_status()
    data = r.json()
    return data.get("status")


def jellyseerr_request(media_type, tmdb_id):
    url = f"{JELLYSEERR_URL}/api/v1/request"
    headers = {"X-Api-Key": JELLYSEERR_API, "Content-Type": "application/json"}
    payload = {"mediaType": media_type, "mediaId": tmdb_id}
    r = requests.post(url, headers=headers, json=payload)
    r.raise_for_status()
    return r.json()


def sync_watchlist_to_jellyseerr():
    watchlist = get_plex_watchlist()

    for item in watchlist:
        title = item.title
        year = getattr(item, "year", None)
        print(f"🔎 Searching for: {title} ({year})")

        results = jellyseerr_search(title)

        if not results.get("results"):
            print(f"❌ No match found in Jellyseerr for {title}")
            continue

        match = results["results"][0]
        tmdb_id = match.get("id")
        media_type = match.get("mediaType")

        print(f"✅ Found match: {match.get('title')} ({media_type}, TMDB {tmdb_id})")

        # Check if already requested/available
        status = jellyseerr_media_status(tmdb_id, media_type)
        if status and status not in ("UNKNOWN", "UNKNOWN_ERROR"):
            print(f"⏩ Skipping {title} — already {status}")
            continue

        # Otherwise, request it
        try:
            res = jellyseerr_request(media_type, tmdb_id)
            print(f"📩 Requested: {res}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Failed to request {title}: {e}")


if __name__ == "__main__":
    sync_watchlist_to_jellyseerr()
