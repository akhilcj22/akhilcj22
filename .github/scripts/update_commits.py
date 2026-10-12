import datetime
import json
import os
import re
import urllib.request

USER = "akhilcj22"
TOKEN = os.environ["GH_TOKEN"]

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
      }
    }
  }
}
"""

now = datetime.datetime.now(datetime.timezone.utc)
year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def contributions_since(start):
    payload = json.dumps({
        "query": QUERY,
        "variables": {"login": USER, "from": start.isoformat(), "to": now.isoformat()},
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.load(resp)
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]


year_count = contributions_since(year_start)
month_count = contributions_since(month_start)

year_label = f"Contributions in {now.year}".replace(" ", "%20")
month_label = f"Contributions in {now.strftime('%B %Y')}".replace(" ", "%20")

block = (
    "<!-- COMMITS:START -->\n"
    f"![{now.year} contributions](https://img.shields.io/badge/{year_label}-{year_count}-0089FF?style=flat)\n"
    f"![{now.strftime('%B')} contributions](https://img.shields.io/badge/{month_label}-{month_count}-2EA44F?style=flat)\n"
    "<!-- COMMITS:END -->"
)

with open("README.md", encoding="utf-8") as f:
    readme = f.read()

readme = re.sub(
    r"<!-- COMMITS:START -->.*?<!-- COMMITS:END -->",
    block,
    readme,
    flags=re.DOTALL,
)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(readme)

print(f"{now.year}: {year_count} contributions | {now.strftime('%B')}: {month_count} contributions")
