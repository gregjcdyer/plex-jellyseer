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


def get_server_info(service):
    """Return (server_id, is4k) for the default server of 'radarr' or 'sonarr', or (None, False)."""
    url = f"{JELLYSEERR_URL}/api/v1/settings/{service}"
    headers = {"X-Api-Key": JELLYSEERR_API}
    try:
        r = requests.get(url, headers=headers)
        if not r.ok:
            print(f"[{service}] settings fetch failed {r.status_code}: {r.text[:200]}")
            return None, False
        servers = r.json()
        if not isinstance(servers, list) or not servers:
            return None, False
        # Prefer default server; fall back to first
        server = next((s for s in servers if s.get("isDefault")), servers[0])
        return server["id"], bool(server.get("is4k", False))
    except Exception as e:
        print(f"[{service}] exception: {e}")
        return None, False


def jellyseerr_request(media_type, tmdb_id, seasons=None, server_id=None, is4k=False):
    url = f"{JELLYSEERR_URL}/api/v1/request"
    headers = {"X-Api-Key": JELLYSEERR_API, "Content-Type": "application/json"}
    payload = {"mediaType": media_type, "mediaId": int(tmdb_id), "is4k": is4k}
    if media_type == "tv":
        payload["seasons"] = seasons if seasons else [1]
    if server_id is not None:
        payload["serverId"] = server_id
    r = requests.post(url, headers=headers, json=payload)
    if not r.ok:
        print(f"Request failed {r.status_code}: {r.text}")
    r.raise_for_status()
    return r.json()


def jellyseerr_approve(request_id):
    url = f"{JELLYSEERR_URL}/api/v1/request/{request_id}/approve"
    headers = {"X-Api-Key": JELLYSEERR_API}
    r = requests.post(url, headers=headers)
    if not r.ok:
        print(f"Approval failed {r.status_code}: {r.text}")
    r.raise_for_status()
    return r.json()


def pick_best_match(results, year):
    if year:
        for r in results:
            date = r.get("releaseDate") or r.get("firstAirDate") or ""
            if date.startswith(str(year)):
                return r
    return results[0]


def sync_watchlist_to_jellyseerr():
    watchlist = get_plex_watchlist()
    print(f"Found {len(watchlist)} items in Plex watchlist")

    radarr_id, radarr_4k = get_server_info("radarr")
    sonarr_id, sonarr_4k = get_server_info("sonarr")
    print(f"Using Radarr server ID: {radarr_id} (4k={radarr_4k}), Sonarr server ID: {sonarr_id} (4k={sonarr_4k})")

    for item in watchlist:
        title = item.title
        year = getattr(item, "year", None)
        print(f"Searching for: {title} ({year})")

        results = jellyseerr_search(title)

        if not results.get("results"):
            print(f"No match found in Jellyseerr for {title}")
            continue

        match = pick_best_match(results["results"], year)
        tmdb_id = match.get("id")
        media_type = match.get("mediaType")
        display_title = match.get("title") or match.get("name", "(unknown)")

        print(f"Found match: {display_title} ({media_type}, TMDB {tmdb_id})")

        # mediaInfo is included in search results — status 5=AVAILABLE, 4=PARTIALLY_AVAILABLE, 3=PROCESSING, 2=PENDING
        media_info = match.get("mediaInfo") or {}
        status = media_info.get("status", 1)  # 1 = UNKNOWN (not yet in Jellyseerr)
        if status and status > 1:
            print(f"Skipping {title} — already has status {status}")
            continue

        # Otherwise, request and approve it
        try:
            seasons = None
            server_id = None
            if media_type == "tv":
                num_seasons = match.get("numberOfSeasons") or 1
                seasons = list(range(1, num_seasons + 1))
                server_id = sonarr_id
                is4k = sonarr_4k
            elif media_type == "movie":
                server_id = radarr_id
                is4k = radarr_4k
            res = jellyseerr_request(media_type, tmdb_id, seasons, server_id, is4k)
            try:
                jellyseerr_approve(res["id"])
                print(f"Requested and approved: {display_title} ({media_type})")
            except requests.exceptions.RequestException as e:
                print(f"Request created but approval failed for {title} (may auto-approve): {e}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to request {title}: {e}")


if __name__ == "__main__":
    sync_watchlist_to_jellyseerr()
