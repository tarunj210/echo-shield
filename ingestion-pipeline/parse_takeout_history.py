import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup


def extract_video_id(url: str | None) -> str | None:
    if not url:
        return None

    parsed = urlparse(url)

    if parsed.hostname in {"www.youtube.com", "youtube.com", "m.youtube.com"}:
        return parse_qs(parsed.query).get("v", [None])[0]

    if parsed.hostname == "youtu.be":
        return parsed.path.strip("/")

    return None


def clean_title(title: str | None) -> str | None:
    if not title:
        return None

    title = title.replace("Watched ", "")
    return " ".join(title.split()).strip()


def parse_json_watch_history(file_path: str, profile_id: str) -> list[dict]:
    path = Path(file_path)
    data = json.loads(path.read_text(encoding="utf-8"))

    events = []

    for item in data:
        title_url = item.get("titleUrl")
        video_id = extract_video_id(title_url)

        if not video_id:
            continue

        watched_at = item.get("time")

        if not watched_at:
            continue

        events.append({
            "profile_id": profile_id,
            "video_id": video_id,
            "watched_at": watched_at,
            "source": "google_takeout_youtube_json",
            "raw_title": clean_title(item.get("title")),
            "raw_url": title_url,
        })

    return events


def parse_html_watch_history(file_path: str, profile_id: str) -> list[dict]:
    """
    Parses Google Takeout YouTube watch-history.html.

    Typical HTML entries look like:
    Watched <a href="https://www.youtube.com/watch?v=abc123">Video title</a><br>
    <a href="https://www.youtube.com/channel/...">Channel</a><br>
    Jun 1, 2026, 10:30:00 PM GMT+10
    """
    path = Path(file_path)
    html = path.read_text(encoding="utf-8", errors="ignore")

    soup = BeautifulSoup(html, "lxml")

    events = []

    # Google Takeout often stores each history item inside div.content-cell
    content_cells = soup.select("div.content-cell")

    if not content_cells:
        # fallback: parse all links if structure is different
        content_cells = soup.find_all("div")

    for cell in content_cells:
        links = cell.find_all("a", href=True)

        video_link = None

        for link in links:
            href = link.get("href")
            if extract_video_id(href):
                video_link = link
                break

        if not video_link:
            continue

        video_url = video_link.get("href")
        video_id = extract_video_id(video_url)
        raw_title = clean_title(video_link.get_text(" ", strip=True))

        text = cell.get_text("\n", strip=True)

        watched_at = extract_timestamp_from_html_text(text)

        if not watched_at:
            continue

        events.append({
            "profile_id": profile_id,
            "video_id": video_id,
            "watched_at": watched_at,
            "source": "google_takeout_youtube_html",
            "raw_title": raw_title,
            "raw_url": video_url,
        })

    return events


def extract_timestamp_from_html_text(text: str) -> str | None:
    """
    Extract timestamp line from Google Takeout HTML text.

    Examples:
    Jun 1, 2026, 10:30:00 PM GMT+10
    1 Jun 2026, 22:30:00 GMT+10
    11 Jun 2026, 10:30:00 pm AEST

    We return the raw timestamp string first.
    It will be normalised in load_watch_history.py.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # Usually the timestamp is the last meaningful line in the cell.
    for line in reversed(lines):
        if re.search(r"\d{4}", line) and re.search(r"\d{1,2}:\d{2}:\d{2}", line):
            return line

    return None


def parse_watch_history(file_path: str, profile_id: str = "profile_self") -> list[dict]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Could not find watch history file: {file_path}")

    suffix = path.suffix.lower()

    if suffix == ".json":
        return parse_json_watch_history(file_path, profile_id)

    if suffix in {".html", ".htm"}:
        return parse_html_watch_history(file_path, profile_id)

    raise ValueError(f"Unsupported file type: {suffix}. Expected .json or .html")