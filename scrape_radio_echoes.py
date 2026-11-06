import csv
import os
import re
import time
from bs4 import BeautifulSoup
import requests

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_URL = "https://www.radioechoes.com"
MASTER_PAGE_URL = f"{BASE_URL}/?page=series_all"
OUTPUT_CSV = "radio_echoes_shows.csv"
DELAY_BETWEEN_REQUESTS = 2.0  # Seconds to wait between page loads

HEADERS = {
    # Custom User-Agent to clearly identify your script
    "User-Agent": (
        "RadioEchoesScraper/1.0 (Polite research scraper; "
        "respecting rate limits; contact@example.com)"
    )
}


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------
def get_soup(url):
    """Fetches a URL respectfully and returns a BeautifulSoup object."""
    # Delay execution to prevent overloading the server
    time.sleep(DELAY_BETWEEN_REQUESTS)
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        print(f"[!] Error fetching {url}: {e}")
        return None


def get_all_series_links():
    """Scrapes the master series directory for series titles and page links."""
    print("Fetching master series list...")
    soup = get_soup(MASTER_PAGE_URL)
    if not soup:
        return []

    series_list = []
    # Find links pointing to series pages (e.g., ?page=series_details&series_id=...)
    for link in soup.find_all("a", href=re.compile(r"page=series_details")):
        series_name = link.text.strip()
        series_url = BASE_URL + "/" + link["href"].lstrip("/")
        if series_name and series_url not in [s["url"] for s in series_list]:
            series_list.append({"name": series_name, "url": series_url})

    print(f"Found {len(series_list)} total series.")
    return series_list


def scrape_series_episodes(series):
    """Scrapes episode details from an individual series page."""
    soup = get_soup(series["url"])
    if not soup:
        return []

    # Extract genre from page metadata if available
    genre_match = soup.find(text=re.compile(r"Genre:", re.I))
    genre = "Unknown"
    if genre_match and genre_match.parent:
        genre = genre_match.parent.text.replace("Genre:", "").strip()

    episodes = []
    # Find table rows containing episode details
    rows = soup.find_all("tr")
    for row in rows:
        cols = row.find_all("td")
        # Typical episode rows contain: Title, Date, Duration, File Size
        if len(cols) >= 4:
            title = cols[0].text.strip()
            broadcast_date = cols[1].text.strip()
            duration = cols[2].text.strip()
            file_size = cols[3].text.strip()

            # Filter out header rows
            if title.lower() != "title" and file_size:
                episodes.append(
                    {
                        "series_name": series["name"],
                        "genre": genre,
                        "episode_title": title,
                        "broadcast_date": broadcast_date,
                        "duration": duration,
                        "file_size": file_size,
                    }
                )

    return episodes


# ---------------------------------------------------------------------------
# MAIN EXECUTION
# ---------------------------------------------------------------------------
def main():
    # Prepare CSV file with headers
    file_exists = os.path.isfile(OUTPUT_CSV)
    with open(
        OUTPUT_CSV, mode="a", newline="", encoding="utf-8"
    ) as csv_file:
        fieldnames = [
            "series_name",
            "genre",
            "episode_title",
            "broadcast_date",
            "duration",
            "file_size",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        all_series = get_all_series_links()

        print("\nStarting episode scraping (this will take several hours)...")
        for index, series in enumerate(all_series, 1):
            print(
                f"[{index}/{len(all_series)}] Scraping series: {series['name']}"
            )

            episodes = scrape_series_episodes(series)
            for ep in episodes:
                writer.writerow(ep)

            # Flush output buffer periodically to save progress
            csv_file.flush()

    print(f"\nDone! Metadata saved to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
