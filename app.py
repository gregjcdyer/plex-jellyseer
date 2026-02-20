import os
import requests
from urllib.parse import quote
from plexapi.myplex import MyPlexAccount


PLEX_USERNAME   = os.getenv("PLEX_USERNAME")
PLEX_PASSWORD   = os.getenv("PLEX_PASSWORD")
JELLYSEERR_URL  = os.getenv("JELLYSEERR_URL", "").rstrip("/")
JELLYSEERR_API  = os.getenv("JELLYSEERR_API")


def get_plex_watchlist():
    print("Logging into Plex account...")
    account = MyPlexAccount(PLEX_USERNAME, PLEX_PASSWORD)
    print(f"Logged into Plex account: {account.username}")
    return account.watchlist()


def jellyseerr_search(query):
    url = f"{JELLYSEERR_URL}/api/v1/search?query={quote(query)}&language=en&page=1"
    headers = {"X-Api-Key": JELLYSEERR_API}
    r = requests.get(url, headers=headers)
    if not r.ok:
        print(f"Search failed {r.status_code}: {r.text}")
    r.raise_for_status()
    return r.json()


def jellyseerr_request(media_type, tmdb_id, seasons=None):
    url = f"{JELLYSEERR_URL}/api/v1/request"
    headers = {"X-Api-Key": JELLYSEERR_API, "Content-Type": "application/json"}
    payload = {"mediaType": media_type, "mediaId": int(tmdb_id)}
    if media_type == "tv":
        payload["seasons"] = seasons or "all"
    r = requests.post(url, headers=headers, json=payload)
    if not r.ok:
        print(f"Request failed {r.status_code}: {r.text}")
    r.raise_for_status()
    return r.json()


def sync_watchlist_to_jellyseerr():
    watchlist = get_plex_watchlist()
    print(f"Found {len(watchlist)} items in Plex watchlist")

    for item in watchlist:
        title = item.title
        year = getattr(item, "year", None)
        print(f"Searching for: {title} ({year})")

        results = jellyseerr_search(title)

        if not results.get("results"):
            print(f"No match found in Jellyseerr for {title}")
            continue

        match = results["results"][0]
        tmdb_id = match.get("id")
        media_type = match.get("mediaType")

        print(f"Found match: {match.get('title')} ({media_type}, TMDB {tmdb_id})")

        # mediaInfo is included in search results — status 5=AVAILABLE, 4=PARTIALLY_AVAILABLE, 3=PROCESSING, 2=PENDING
        media_info = match.get("mediaInfo") or {}
        status = media_info.get("status", 1)  # 1 = UNKNOWN (not yet in Jellyseerr)
        if status and status > 1:
            print(f"Skipping {title} — already has status {status}")
            continue

        # Otherwise, request it
        try:
            seasons = None
            if media_type == "tv":
                num_seasons = match.get("numberOfSeasons") or 1
                seasons = list(range(1, num_seasons + 1))
            res = jellyseerr_request(media_type, tmdb_id, seasons)
            print(f"Requested: {match.get('title')} ({media_type})")
        except requests.exceptions.RequestException as e:
            print(f"Failed to request {title}: {e}")


if __name__ == "__main__":
    sync_watchlist_to_jellyseerr()
