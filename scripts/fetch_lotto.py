"""
Fetch latest Korean Lotto (6/45) draw results from 동행복권 API
and append to lotto_draws.csv.

Usage: python scripts/fetch_lotto.py
"""

import csv
import json
import os
import time
import urllib.request

API_URL = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo="
CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lotto_draws.csv")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*",
}


def get_last_round():
    """Read CSV and return the last draw number."""
    last = 0
    if not os.path.exists(CSV_PATH):
        return last
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].isdigit():
                last = int(row[0])
    return last


def fetch_draw(draw_no):
    """Fetch a single draw from the API. Returns dict or None."""
    url = API_URL + str(draw_no)
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("returnValue") == "success":
                return data
    except Exception as e:
        print(f"  Error fetching draw #{draw_no}: {e}")
    return None


def main():
    last_round = get_last_round()
    print(f"Last stored draw: #{last_round}")

    next_draw = last_round + 1
    new_count = 0
    consecutive_fails = 0

    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        while consecutive_fails < 3:
            print(f"Fetching draw #{next_draw}...", end=" ")
            data = fetch_draw(next_draw)

            if data is None:
                print("not available")
                consecutive_fails += 1
                time.sleep(2)
                continue

            nums = [
                data["drwtNo1"], data["drwtNo2"], data["drwtNo3"],
                data["drwtNo4"], data["drwtNo5"], data["drwtNo6"],
            ]
            bonus = data["bnusNo"]

            writer.writerow([next_draw] + nums + [bonus])
            f.flush()
            print(f"OK -> {nums} + {bonus}")

            new_count += 1
            consecutive_fails = 0
            next_draw += 1
            time.sleep(1)

    print(f"\nDone. {new_count} new draws added. Total: {last_round + new_count}")


if __name__ == "__main__":
    main()
