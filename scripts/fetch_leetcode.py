#!/usr/bin/env python3
"""
Fetch real LeetCode problem-solving stats from LeetCode's public,
unauthenticated GraphQL endpoint (the same one the profile page itself uses)
and write data/leetcode.json with solved counts by difficulty, streak info,
and a daily submission calendar (for the heatmap-style grid).

No login, no session cookie -- just the public GraphQL schema.
Run daily by .github/workflows/update-profile-art.yml.

NOTE: leetcode.com is reachable from GitHub Actions' runners (full internet
access) but may not be reachable from every sandboxed dev environment -- if
you get a connection error running this locally, check your network/proxy.
"""
import datetime
import json
import os
import sys

import requests

USERNAME = os.environ.get("LEETCODE_USER", "YOUR_LEETCODE_USERNAME")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "leetcode.json")
URL = "https://leetcode.com/graphql"

QUERY = """
query userProfile($username: String!) {
  matchedUser(username: $username) {
    username
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
      }
    }
    userCalendar {
      streak
      totalActiveDays
      submissionCalendar
    }
  }
}
"""


def fetch():
    resp = requests.post(
        URL,
        json={"query": QUERY, "variables": {"username": USERNAME}},
        headers={
            "User-Agent": "profile-readme-bot/1.0",
            "Content-Type": "application/json",
            "Referer": f"https://leetcode.com/{USERNAME}/",
        },
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()

    user = payload.get("data", {}).get("matchedUser")
    if not user:
        print(f"no such LeetCode user: {USERNAME}", file=sys.stderr)
        sys.exit(1)
    return user


def build_data(user):
    counts = {d["difficulty"]: d["count"] for d in user["submitStatsGlobal"]["acSubmissionNum"]}
    total = counts.get("All", 0)
    easy = counts.get("Easy", 0)
    medium = counts.get("Medium", 0)
    hard = counts.get("Hard", 0)

    cal = user["userCalendar"]
    raw_calendar = json.loads(cal["submissionCalendar"] or "{}")
    # keys are unix-day timestamps (strings) -> submission count that day
    days = []
    for ts, count in sorted(raw_calendar.items(), key=lambda kv: int(kv[0])):
        date = datetime.datetime.utcfromtimestamp(int(ts)).strftime("%Y-%m-%d")
        days.append({"date": date, "count": count})

    return {
        "username": USERNAME,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_solved": total,
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "streak": cal.get("streak", 0),
        "total_active_days": cal.get("totalActiveDays", 0),
        "days": days,
    }


if __name__ == "__main__":
    user = fetch()
    data = build_data(user)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(
        f"wrote {OUT_PATH}: {data['total_solved']} solved "
        f"(E{data['easy']}/M{data['medium']}/H{data['hard']}), "
        f"streak {data['streak']}, active days {data['total_active_days']}"
    )
