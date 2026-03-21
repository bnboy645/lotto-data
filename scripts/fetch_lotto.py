"""
Fetch latest Korean Lotto (6/45) draw results from Naver search
and append to lotto_draws.csv.

Naver shows lotto results in search with ball-styled spans.
We verify the draw number matches to avoid duplicates.

Usage: python scripts/fetch_lotto.py
"""

import csv
import os
import re
import time
import requests

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lotto_draws.csv")
NAVER_SEARCH = "https://m.search.naver.com/search.naver?query="


def get_last_round():
    last = 0
    if not os.path.exists(CSV_PATH):
        return last
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].isdigit():
                last = int(row[0])
    return last


def fetch_draw_from_naver(session, draw_no):
    """Search Naver for lotto results. Returns (numbers[6], bonus) or None."""
    query = f"로또 {draw_no}회 당첨번호"
    url = NAVER_SEARCH + requests.utils.quote(query)

    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return None

        # Check if this draw hasn't happened yet
        if "추첨 전" in r.text or "추첨전" in r.text:
            print(f"draw #{draw_no} not drawn yet", end="")
            return None

        # Extract ball numbers: <span class="...ball...">NN</span>
        balls = re.findall(r'class="[^"]*ball[^"]*"[^>]*>(\d{1,2})<', r.text)

        if len(balls) >= 7:
            nums = [int(x) for x in balls[:6]]
            bonus = int(balls[6])
            # Validate: all numbers should be 1-45 and unique
            if all(1 <= n <= 45 for n in nums + [bonus]) and len(set(nums)) == 6:
                return nums, bonus

        return None
    except Exception as e:
        print(f"error: {e}")
        return None


def main():
    last_round = get_last_round()
    print(f"Last stored draw: #{last_round}")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    next_draw = last_round + 1
    new_count = 0

    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        consecutive_fails = 0
        while consecutive_fails < 3:
            print(f"Fetching draw #{next_draw}... ", end="")
            result = fetch_draw_from_naver(session, next_draw)

            if result is None:
                print(" - not available")
                consecutive_fails += 1
                time.sleep(3)
                continue

            nums, bonus = result
            writer.writerow([next_draw] + nums + [bonus])
            f.flush()
            print(f"OK -> {nums} + {bonus}")

            new_count += 1
            consecutive_fails = 0
            next_draw += 1
            time.sleep(3)

    print(f"\nDone. {new_count} new draws added. Total: {last_round + new_count}")


if __name__ == "__main__":
    main()
