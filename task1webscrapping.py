


import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}

CLASS_ODI = 2          # StatsGuru: 1=Tests, 2=ODIs, 3=T20Is
NUM_PAGES = 5           # how many pages of ~50 players each to pull
DELAY_SECONDS = 1.5     # be polite, don't hammer the server


def scrape_stats_page(stat_type, page):
    """
    stat_type: "batting" or "bowling"
    Returns a list of row-dicts scraped from one StatsGuru results page.
    """
    url = (
        "https://stats.espncricinfo.com/ci/engine/stats/index.html"
        f"?class={CLASS_ODI};template=results;type={stat_type};page={page}"
    )
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    tables = soup.find_all("table", class_="engineTable")
    if not tables:
        return []

    # The actual stats table is the one with the most rows
    stats_table = max(tables, key=lambda t: len(t.find_all("tr")))

    header_cells = stats_table.find_all("th")
    headers = [th.get_text(strip=True) for th in header_cells]

    rows = []
    for tr in stats_table.find_all("tr", class_="data1"):
        cells = tr.find_all("td")
        values = [td.get_text(strip=True) for td in cells]
        if not values:
            continue

        # First column is usually the player name, often a link
        name_tag = cells[0].find("a")
        if name_tag:
            values[0] = name_tag.get_text(strip=True)

        row = dict(zip(headers, values))
        rows.append(row)

    return rows


def scrape_all(stat_type, num_pages):
    all_rows = []
    for page in range(1, num_pages + 1):
        print(f"Scraping ODI {stat_type} - page {page}...")
        try:
            rows = scrape_stats_page(stat_type, page)
        except requests.RequestException as e:
            print(f"  Failed on page {page}: {e}")
            continue

        if not rows:
            print(f"  No more rows found, stopping at page {page}.")
            break

        all_rows.extend(rows)
        time.sleep(DELAY_SECONDS)

    return pd.DataFrame(all_rows)


def main():
    batting_df = scrape_all("batting", NUM_PAGES)
    print(f"\nScraped {len(batting_df)} players (batting)")

    bowling_df = scrape_all("bowling", NUM_PAGES)
    print(f"Scraped {len(bowling_df)} players (bowling)\n")

    # Prefix columns so we know which side they came from after merging
    # (both tables have overlapping column names like "Mat", "Ave" etc.)
    batting_df = batting_df.add_prefix("bat_")
    bowling_df = bowling_df.add_prefix("bowl_")

    # The player name column becomes bat_Player / bowl_Player after prefixing
    batting_df = batting_df.rename(columns={"bat_Player": "Player"})
    bowling_df = bowling_df.rename(columns={"bowl_Player": "Player"})

    # Outer join so players who only appear in one list aren't dropped
    combined_df = pd.merge(batting_df, bowling_df, on="Player", how="outer")

    combined_df.to_csv("odi_player_stats.csv", index=False)
    print(f"Saved {len(combined_df)} players to odi_player_stats.csv")
    print(combined_df.head())


if __name__ == "__main__":
    main()