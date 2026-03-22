"""
Fetch latest Korean Lotto (6/45) draw results and append to lotto_draws.csv.

Data sources (tried in order):
  1. dhlottery.co.kr official JSON API
  2. Naver mobile search scraping (fallback)

Usage: python scripts/fetch_lotto.py
"""

import csv
import json
import os
import re
import time
import requests

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lotto_draws.csv")
NAVER_SEARCH = "https://m.search.naver.com/search.naver?query="
DHLOTTERY_API = "https://www.dhlottery.co.kr/common.do?method=getLottoNumber&drwNo="


def get_last_round():
    """Returns (last_round, last_numbers) where last_numbers is [n1..n6, bonus]."""
    last = 0
    last_nums = []
    if not os.path.exists(CSV_PATH):
        return last, last_nums
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].isdigit():
                last = int(row[0])
                if len(row) >= 8:
                    last_nums = [int(x) for x in row[1:8]]
    return last, last_nums


def fetch_draw_from_dhlottery(session, draw_no):
    """Fetch from official dhlottery.co.kr JSON API. Returns (numbers[6], bonus) or None."""
    url = DHLOTTERY_API + str(draw_no)
    try:
        r = session.get(url, timeout=15, allow_redirects=False)
        if r.status_code != 200:
            return None

        try:
            data = r.json()
        except (json.JSONDecodeError, ValueError):
            return None

        if data.get("returnValue") != "success":
            return None

        nums = [
            data["drwtNo1"], data["drwtNo2"], data["drwtNo3"],
            data["drwtNo4"], data["drwtNo5"], data["drwtNo6"],
        ]
        bonus = data["bnusNo"]

        if all(1 <= n <= 45 for n in nums + [bonus]) and len(set(nums)) == 6:
            return nums, bonus

        return None
    except Exception as e:
        print(f"dhlottery error: {e}")
        return None


def fetch_draw_from_naver(session, draw_no):
    """Search Naver for lotto results. Returns (numbers[6], bonus) or None."""
    query = f"로또 {draw_no}회 당첨번호"
    url = NAVER_SEARCH + requests.utils.quote(query)

    try:
        r = session.get(url, timeout=15)
        if r.status_code != 200:
            return None

        # Extract ball numbers: <span class="...ball...">NN</span>
        balls = re.findall(r'class="[^"]*ball[^"]*"[^>]*>(\d{1,2})<', r.text)

        if len(balls) >= 7:
            nums = [int(x) for x in balls[:6]]
            bonus = int(balls[6])
            if all(1 <= n <= 45 for n in nums + [bonus]) and len(set(nums)) == 6:
                return nums, bonus

        return None
    except Exception as e:
        print(f"naver error: {e}")
        return None


def fetch_draw(session, draw_no):
    """Try dhlottery API first, then Naver as fallback."""
    result = fetch_draw_from_dhlottery(session, draw_no)
    if result is not None:
        print("[dhlottery] ", end="")
        return result

    time.sleep(1)
    result = fetch_draw_from_naver(session, draw_no)
    if result is not None:
        print("[naver] ", end="")
        return result

    return None


def main():
    last_round, last_nums = get_last_round()
    print(f"Last stored draw: #{last_round}")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "application/json, text/html, */*",
    })

    # Warm up session with dhlottery main page (sets cookies)
    try:
        session.get("https://www.dhlottery.co.kr/", timeout=10)
    except Exception:
        pass

    next_draw = last_round + 1
    new_count = 0
    prev_nums = last_nums  # track previous round's numbers for duplicate detection

    with open(CSV_PATH, "a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        consecutive_fails = 0
        while consecutive_fails < 3:
            print(f"Fetching draw #{next_draw}... ", end="")
            result = fetch_draw(session, next_draw)

            if result is None:
                print(" - not available")
                consecutive_fails += 1
                time.sleep(3)
                continue

            nums, bonus = result
            fetched = nums + [bonus]

            # Guard: Naver shows previous round's numbers for undrawn rounds.
            # If the numbers are identical to the previous round, skip.
            if prev_nums and fetched == prev_nums:
                print(f" - same as previous round (not drawn yet)")
                consecutive_fails += 1
                time.sleep(3)
                continue

            writer.writerow([next_draw] + nums + [bonus])
            f.flush()
            print(f"OK -> {nums} + {bonus}")

            new_count += 1
            consecutive_fails = 0
            prev_nums = fetched
            next_draw += 1
            time.sleep(3)

    print(f"\nDone. {new_count} new draws added. Total: {last_round + new_count}")


if __name__ == "__main__":
    main()
