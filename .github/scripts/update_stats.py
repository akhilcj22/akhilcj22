"""Generate assets/github-stats.svg with all-time contributions and lines of code changed."""
import json
import os
import time
import urllib.request

TOKEN = os.environ["GH_TOKEN"]
USER = os.environ.get("STATS_USER", "akhilcj22")
# Repos whose total changed lines exceed this are skipped (vendored/build files skew the count).
MAX_REPO_LINES = int(os.environ.get("MAX_REPO_LINES", "150000"))
EXCLUDED = {r.strip().lower() for r in os.environ.get("EXCLUDED", "").split(",") if r.strip()}


def request(url, data=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode() if data else None,
        headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read() or "null")


def graphql(query):
    return request("https://api.github.com/graphql", {"query": query})[1]["data"]


def total_contributions():
    created = graphql('{user(login:"%s"){createdAt}}' % USER)["user"]["createdAt"]
    total = 0
    for year in range(int(created[:4]), time.gmtime().tm_year + 1):
        data = graphql(
            '{user(login:"%s"){contributionsCollection(from:"%d-01-01T00:00:00Z",to:"%d-12-31T23:59:59Z")'
            "{contributionCalendar{totalContributions}}}}" % (USER, year, year)
        )
        total += data["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    return total


def repositories():
    repos, owned_cursor, contrib_cursor = set(), None, None
    while True:
        data = graphql(
            """{user(login:"%s"){
              repositories(first:100,isFork:false,after:%s){pageInfo{hasNextPage endCursor} nodes{nameWithOwner}}
              repositoriesContributedTo(first:100,includeUserRepositories:false,
                contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY,PULL_REQUEST_REVIEW],after:%s)
                {pageInfo{hasNextPage endCursor} nodes{nameWithOwner}}}}"""
            % (USER, json.dumps(owned_cursor), json.dumps(contrib_cursor))
        )["user"]
        for key in ("repositories", "repositoriesContributedTo"):
            repos |= {n["nameWithOwner"] for n in data[key]["nodes"] if n}
        owned, contrib = data["repositories"]["pageInfo"], data["repositoriesContributedTo"]["pageInfo"]
        if not (owned["hasNextPage"] or contrib["hasNextPage"]):
            return repos
        owned_cursor = owned["endCursor"] or owned_cursor
        contrib_cursor = contrib["endCursor"] or contrib_cursor


def lines_changed(repo):
    for _ in range(6):  # stats are computed lazily and return 202 until ready
        try:
            status, data = request(f"https://api.github.com/repos/{repo}/stats/contributors")
        except Exception:
            return 0
        if status == 200 and isinstance(data, list):
            break
        time.sleep(3)
    else:
        return 0
    return sum(
        w["a"] + w["d"]
        for author in data
        if (author.get("author") or {}).get("login") == USER
        for w in author["weeks"]
    )


def total_lines():
    total = 0
    for repo in sorted(repositories()):
        if repo.lower() in EXCLUDED:
            continue
        changed = lines_changed(repo)
        if changed <= MAX_REPO_LINES:
            total += changed
    return total


SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="360" height="64" viewBox="0 0 360 64" fill="none" stroke="#848d97" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" font-family="-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif" font-size="14">
  <g transform="translate(2,6)">
    <path d="M9 3H3.5A1.5 1.5 0 0 0 2 4.5v9A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V9"/>
    <path d="M10 8l4-4M11 3h4v4" transform="translate(-1,0)"/>
    <path d="M6 12l2-2.5 1.5 1.5 2-3" stroke-width="1.2"/>
  </g>
  <text x="30" y="19" fill="#848d97" stroke="none">All-time contributions</text>
  <text x="358" y="19" fill="#848d97" stroke="none" text-anchor="end">{contributions:,}</text>
  <g transform="translate(2,38)">
    <path d="M8 2v7M4.5 5.5h7"/>
    <path d="M4.5 13.5h7"/>
  </g>
  <text x="30" y="51" fill="#848d97" stroke="none">Lines of code changed</text>
  <text x="358" y="51" fill="#848d97" stroke="none" text-anchor="end">{lines:,}</text>
</svg>
"""

if __name__ == "__main__":
    contributions, lines = total_contributions(), total_lines()
    os.makedirs("assets", exist_ok=True)
    with open("assets/github-stats.svg", "w", encoding="utf-8") as f:
        f.write(SVG.format(contributions=contributions, lines=lines))
    print(f"contributions={contributions} lines={lines}")
