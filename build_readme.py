from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import re
import sys
import textwrap
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).parent.resolve()
ASSETS = ROOT / "assets"

USERNAME = "YUZHEthefool"
STATS_BASE_URL = (
    "https://github-readme-stats-r4ol293mc-thefoolyuzhe-5613s-projects.vercel.app"
)
VERCEL_BYPASS_SECRET = (
    os.environ.get("VERCEL_AUTOMATION_BYPASS_SECRET")
    or os.environ.get("VERCEL_BYPASS_SECRET")
)
GITHUB_TOKEN = (
    os.environ.get("GITHUB_TOKEN")
    or os.environ.get("GH_TOKEN")
    or os.environ.get("TOKEN")
)
THEME = "tokyonight"
LANGUAGE_WINDOW_DAYS = 365

PROJECTS = [
    {
        "owner": "YUZHEthefool",
        "repo": "Fool",
        "title": "Fool",
        "description": "A modern Rust shell with native AI assistance.",
    },
    {
        "owner": "Zero-kernel",
        "repo": "Zero-os",
        "title": "Zero-OS",
        "description": "A security-first monolithic kernel written in pure Rust.",
    },
    {
        "owner": "YUZHEthefool",
        "repo": "Zero-Compiler",
        "title": "Zero-Compiler",
        "description": "A modern bytecode language and virtual machine.",
    },
    {
        "owner": "Xero-Team",
        "repo": "zpdf",
        "title": "zpdf",
        "description": "PDF tooling from the Xero-Team ecosystem.",
    },
]

TECH_STACK = [
    ("Rust", "000000", "rust", "white"),
    ("C", "00599C", "c", "white"),
    ("Python", "3776AB", "python", "white"),
    ("Go", "00ADD8", "go", "white"),
    ("Linux", "FCC624", "linux", "black"),
    ("Docker", "2496ED", "docker", "white"),
]

LANGUAGE_FALLBACK_COLORS = {
    "Rust": "#f7812b",
    "Python": "#4b9be8",
    "Go": "#73c255",
    "TypeScript": "#f7c843",
    "JavaScript": "#f1e05a",
    "C": "#8b6fe8",
    "C++": "#8b6fe8",
    "C/C++": "#8b6fe8",
    "Shell": "#89e051",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Other": "#a7b0bd",
}

BARE_AMPERSAND = re.compile(
    r"&(?!amp;|lt;|gt;|apos;|quot;|#[0-9]+;|#x[0-9a-fA-F]+;)"
)


def quote(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def params(values: dict[str, str]) -> str:
    return urllib.parse.urlencode(values)


def stats_url() -> str:
    query = params(
        {
            "username": USERNAME,
            "show_icons": "true",
            "theme": THEME,
            "hide_border": "true",
            "card_width": "500",
        }
    )
    return f"{STATS_BASE_URL}/api?{query}"


def typing_url() -> str:
    query = params(
        {
            "font": "Fira Code",
            "size": "32",
            "duration": "2800",
            "pause": "2000",
            "color": "A033FF",
            "center": "true",
            "vCenter": "true",
            "width": "940",
            "lines": "Hi! I'm Thefool 👋;Bridging Gap: AI & Bare Metal;Building Neural Networks;Crafting OS Kernels",
        }
    )
    return f"https://readme-typing-svg.demolab.com?{query}"


def pin_url(project: dict[str, str]) -> str:
    query = params(
        {
            "username": project["owner"],
            "repo": project["repo"],
            "theme": THEME,
            "hide_border": "true",
        }
    )
    return f"{STATS_BASE_URL}/api/pin/?{query}"


def project_slug(project: dict[str, str]) -> str:
    raw = f'{project["owner"]}-{project["repo"]}'.lower()
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")


def sanitize_svg(data: str) -> str:
    data = data.strip().lstrip("\ufeff")
    return BARE_AMPERSAND.sub("&amp;", data)


def is_valid_svg(data: str) -> bool:
    if not data:
        return False
    if "<svg" not in data[:1200].lower():
        return False
    try:
        root = ET.fromstring(data.encode("utf-8"))
    except ET.ParseError:
        return False
    return root.tag.endswith("svg")


def read_existing_svg(path: Path) -> str | None:
    if not path.exists():
        return None
    data = sanitize_svg(path.read_text(encoding="utf-8", errors="replace"))
    return data if is_valid_svg(data) else None


def fallback_svg(title: str, subtitle: str, *, height: int = 180) -> str:
    safe_title = html.escape(title, quote=True)
    safe_subtitle = html.escape(subtitle, quote=True)
    width = 500
    title_y = 42 if height <= 130 else 54
    subtitle_y = 70 if height <= 130 else 92
    footer_y = height - 20 if height <= 130 else height - 34
    subtitle_size = 14 if height <= 130 else 16
    return textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{safe_title}">
          <rect width="{width}" height="{height}" rx="12" fill="#1a1b27"/>
          <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="11" fill="none" stroke="#2f334d"/>
          <text x="28" y="{title_y}" fill="#70a5fd" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="24" font-weight="700">{safe_title}</text>
          <text x="28" y="{subtitle_y}" fill="#c3d3ff" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="{subtitle_size}">{safe_subtitle}</text>
          <text x="28" y="{footer_y}" fill="#7982a9" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12">Generated fallback - waiting for stats API</text>
        </svg>
        """
    ).strip()


def fetch_svg(url: str, target: Path, title: str, subtitle: str, *, height: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = read_existing_svg(target)
    fallback = (
        existing
        if existing and "Generated fallback - waiting for stats API" not in existing
        else fallback_svg(title, subtitle, height=height)
    )

    try:
        headers = {
            "Accept": "image/svg+xml,*/*;q=0.8",
            "User-Agent": "YUZHEthefool-readme-builder/1.0",
        }
        if VERCEL_BYPASS_SECRET:
            headers["x-vercel-protection-bypass"] = VERCEL_BYPASS_SECRET

        request = urllib.request.Request(
            url,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=25) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read(2_000_000).decode("utf-8", errors="replace")

        data = sanitize_svg(data)
        if not is_valid_svg(data):
            raise ValueError(f"response is not a valid SVG ({content_type or 'unknown type'})")

        target.write_text(data + "\n", encoding="utf-8")
        print(f"updated {target.relative_to(ROOT)}")
    except Exception as exc:  # noqa: BLE001 - build should degrade instead of breaking README
        target.write_text(fallback + "\n", encoding="utf-8")
        print(f"using fallback for {target.relative_to(ROOT)}: {exc}", file=sys.stderr)


def graphql_request(query: str, variables: dict[str, object]) -> dict[str, object]:
    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is not set")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "YUZHEthefool-readme-builder/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=35) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def normalize_language(language: str) -> str:
    if language in {"C", "C++"}:
        return "C/C++"
    return language


def fetch_language_stats() -> dict[str, object]:
    since = (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=LANGUAGE_WINDOW_DAYS)
    ).isoformat(timespec="seconds")
    query = """
    query($login: String!, $after: String, $since: GitTimestamp!) {
      user(login: $login) {
        repositories(first: 100, after: $after, ownerAffiliations: OWNER, privacy: PUBLIC, orderBy: {field: PUSHED_AT, direction: DESC}) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            isFork
            isArchived
            defaultBranchRef {
              target {
                ... on Commit {
                  history(since: $since) {
                    totalCount
                  }
                }
              }
            }
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              totalSize
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    """

    after = None
    repos = 0
    total_commits = 0
    language_commits: dict[str, float] = {}
    language_colors: dict[str, str] = {}

    while True:
        data = graphql_request(
            query,
            {"login": USERNAME, "after": after, "since": since},
        )
        repositories = data["user"]["repositories"]
        for repo in repositories["nodes"]:
            if repo["isFork"] or repo["isArchived"]:
                continue
            default_branch = repo.get("defaultBranchRef")
            if not default_branch:
                continue
            commits = int(default_branch["target"]["history"]["totalCount"])
            if commits <= 0:
                continue
            languages = repo.get("languages") or {}
            total_size = int(languages.get("totalSize") or 0)
            if total_size <= 0:
                continue

            repos += 1
            total_commits += commits
            for edge in languages["edges"]:
                language = normalize_language(edge["node"]["name"])
                size = int(edge["size"])
                weighted_commits = commits * (size / total_size)
                language_commits[language] = language_commits.get(language, 0.0) + weighted_commits
                color = (
                    LANGUAGE_FALLBACK_COLORS.get(language)
                    if language == "C/C++"
                    else edge["node"].get("color")
                )
                if color:
                    language_colors[language] = color

        page_info = repositories["pageInfo"]
        if not page_info["hasNextPage"]:
            break
        after = page_info["endCursor"]

    rounded = [
        {
            "name": language,
            "commits": int(round(count)),
            "color": language_colors.get(language)
            or LANGUAGE_FALLBACK_COLORS.get(language)
            or LANGUAGE_FALLBACK_COLORS["Other"],
        }
        for language, count in sorted(
            language_commits.items(), key=lambda item: item[1], reverse=True
        )
    ]

    top = rounded[:5]
    other_commits = sum(item["commits"] for item in rounded[5:])
    if other_commits:
        top.append(
            {
                "name": "Other",
                "commits": other_commits,
                "color": LANGUAGE_FALLBACK_COLORS["Other"],
            }
        )

    normalized_total = sum(item["commits"] for item in top)
    return {
        "languages": top,
        "total_commits": normalized_total or total_commits,
        "repositories": repos,
        "days": LANGUAGE_WINDOW_DAYS,
        "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
    }


def polar_to_cartesian(cx: float, cy: float, radius: float, angle: float) -> tuple[float, float]:
    return cx + radius * math.cos(angle), cy + radius * math.sin(angle)


def donut_segment(
    cx: float,
    cy: float,
    outer_radius: float,
    inner_radius: float,
    start_angle: float,
    end_angle: float,
) -> str:
    if end_angle - start_angle >= math.tau - 0.0001:
        end_angle = start_angle + math.tau - 0.0001
    large_arc = 1 if end_angle - start_angle > math.pi else 0
    x1, y1 = polar_to_cartesian(cx, cy, outer_radius, start_angle)
    x2, y2 = polar_to_cartesian(cx, cy, outer_radius, end_angle)
    x3, y3 = polar_to_cartesian(cx, cy, inner_radius, end_angle)
    x4, y4 = polar_to_cartesian(cx, cy, inner_radius, start_angle)
    return (
        f"M {x1:.2f} {y1:.2f} "
        f"A {outer_radius} {outer_radius} 0 {large_arc} 1 {x2:.2f} {y2:.2f} "
        f"L {x3:.2f} {y3:.2f} "
        f"A {inner_radius} {inner_radius} 0 {large_arc} 0 {x4:.2f} {y4:.2f} Z"
    )


def language_stats_svg(stats: dict[str, object]) -> str:
    languages = stats["languages"]
    total_commits = int(stats["total_commits"]) or 1
    repos = int(stats["repositories"])
    days = int(stats["days"])
    updated = str(stats["updated"])
    dominant = languages[0] if languages else {
        "name": "No data",
        "commits": 0,
        "color": LANGUAGE_FALLBACK_COLORS["Other"],
    }
    dominant_pct = (dominant["commits"] / total_commits * 100) if total_commits else 0

    width = 500
    height = 360
    chart_cx = 130
    chart_cy = 160
    outer_radius = 82
    inner_radius = 55
    row_x = 250
    row_y = 105
    row_gap = 37
    bar_x = 370
    bar_width = 82

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Language Stats by Commits">',
        "<defs>",
        '<filter id="shadow" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity="0.35"/></filter>',
        '<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0f1722"/><stop offset="1" stop-color="#05090f"/></linearGradient>',
        "</defs>",
        '<rect x="1" y="1" width="498" height="358" rx="14" fill="url(#panel)" stroke="#202b38"/>',
        '<text x="24" y="38" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="23" font-weight="700">Language Stats</text>',
        '<text x="205" y="38" fill="#58a6ff" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="16" font-weight="700">(by Commits)</text>',
        '<rect x="356" y="18" width="120" height="28" rx="14" fill="#132235"/>',
        '<text x="373" y="37" fill="#58a6ff" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12" font-weight="700">GraphQL API</text>',
        f'<text x="24" y="66" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="13">Based on {total_commits:,} commits across {repos} repositories - Last 12 months</text>',
        '<rect x="24" y="84" width="452" height="178" rx="12" fill="#071018" stroke="#1b2733"/>',
        '<rect x="24" y="278" width="452" height="54" rx="12" fill="#071018" stroke="#1b2733"/>',
    ]

    angle = -math.pi / 2
    for item in languages:
        pct = item["commits"] / total_commits if total_commits else 0
        next_angle = angle + pct * math.tau
        parts.append(
            f'<path d="{donut_segment(chart_cx, chart_cy, outer_radius, inner_radius, angle, next_angle)}" fill="{item["color"]}" filter="url(#shadow)"/>'
        )
        angle = next_angle

    parts.extend(
        [
            f'<text x="{chart_cx}" y="{chart_cy - 4}" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="17" font-weight="700">{html.escape(str(dominant["name"]))}</text>',
            f'<text x="{chart_cx}" y="{chart_cy + 30}" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="28" font-weight="800">{dominant_pct:.1f}%</text>',
        ]
    )

    for index, item in enumerate(languages):
        y = row_y + index * row_gap
        commits = int(item["commits"])
        pct = commits / total_commits * 100 if total_commits else 0
        bar_fill = min(bar_width, max(2, bar_width * pct / 100))
        name = html.escape(str(item["name"]))
        color = item["color"]
        parts.extend(
            [
                f'<circle cx="{row_x}" cy="{y}" r="6" fill="{color}"/>',
                f'<text x="{row_x + 14}" y="{y + 5}" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="14" font-weight="700">{name}</text>',
                f'<text x="{bar_x - 14}" y="{y + 5}" text-anchor="end" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12">{commits:,}</text>',
                f'<rect x="{bar_x}" y="{y - 5}" width="{bar_width}" height="9" rx="4.5" fill="#202933"/>',
                f'<rect x="{bar_x}" y="{y - 5}" width="{bar_fill:.2f}" height="9" rx="4.5" fill="{color}"/>',
                f'<text x="462" y="{y + 5}" text-anchor="end" fill="{color}" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12" font-weight="700">{pct:.1f}%</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="54" y="306" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="18" font-weight="800">{total_commits:,}</text>',
            '<text x="54" y="323" text-anchor="middle" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Commits</text>',
            f'<text x="178" y="306" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="18" font-weight="800">{repos}</text>',
            '<text x="178" y="323" text-anchor="middle" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Repositories</text>',
            f'<text x="302" y="306" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="18" font-weight="800">{days}</text>',
            '<text x="302" y="323" text-anchor="middle" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Days</text>',
            f'<text x="426" y="306" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="14" font-weight="700">{updated}</text>',
            '<text x="426" y="323" text-anchor="middle" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Updated</text>',
            '<text x="24" y="348" fill="#8f9bad" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Data source: GitHub GraphQL API - commit history weighted by repository languages</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def write_language_stats() -> None:
    target = ASSETS / "language-stats.svg"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(language_stats_svg(fetch_language_stats()) + "\n", encoding="utf-8")
        print(f"updated {target.relative_to(ROOT)}")
    except Exception as exc:  # noqa: BLE001
        fallback = read_existing_svg(target) or language_stats_svg(
            {
                "languages": [
                    {"name": "Rust", "commits": 75, "color": LANGUAGE_FALLBACK_COLORS["Rust"]},
                    {"name": "Python", "commits": 12, "color": LANGUAGE_FALLBACK_COLORS["Python"]},
                    {"name": "Go", "commits": 8, "color": LANGUAGE_FALLBACK_COLORS["Go"]},
                    {"name": "TypeScript", "commits": 3, "color": LANGUAGE_FALLBACK_COLORS["TypeScript"]},
                    {"name": "Other", "commits": 2, "color": LANGUAGE_FALLBACK_COLORS["Other"]},
                ],
                "total_commits": 100,
                "repositories": 0,
                "days": LANGUAGE_WINDOW_DAYS,
                "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
            }
        )
        target.write_text(fallback + "\n", encoding="utf-8")
        print(f"using fallback for {target.relative_to(ROOT)}: {exc}", file=sys.stderr)


def badge(label: str, color: str, logo: str, logo_color: str = "white") -> str:
    return (
        f'<img src="https://img.shields.io/badge/{quote(label)}-{color}'
        f'?style=for-the-badge&logo={quote(logo)}&logoColor={quote(logo_color)}" '
        f'alt="{html.escape(label, quote=True)}" height="32">'
    )


def tech_badges() -> str:
    return "\n".join(
        badge(label, color, logo, logo_color)
        for label, color, logo, logo_color in TECH_STACK
    )


def project_card(project: dict[str, str]) -> str:
    slug = project_slug(project)
    url = f'https://github.com/{project["owner"]}/{project["repo"]}'
    alt = html.escape(f'{project["title"]} repository card', quote=True)
    return textwrap.dedent(
        f"""\
        <a href="{url}">
          <img src="./assets/pin-{slug}.svg" alt="{alt}" width="100%">
        </a>
        """
    ).strip()


def project_cards() -> str:
    return "\n\n".join(project_card(project) for project in PROJECTS)


def project_list() -> str:
    items = []
    for project in PROJECTS[:3]:
        url = f'https://github.com/{project["owner"]}/{project["repo"]}'
        items.append(
            f'- **[{project["title"]}]({url})** - {project["description"]}'
        )
    return "\n".join(items)


def indent_block(value: str, prefix: str) -> str:
    return value.replace("\n", f"\n{prefix}")


def render_readme() -> str:
    generated_at = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    projects_md = indent_block(project_list(), "        ")
    tech_md = indent_block(tech_badges(), "        ")
    project_cards_md = indent_block(project_cards(), "        ")

    return textwrap.dedent(
        f"""\
        <!--
        This README is generated by build_readme.py.
        Edit build_readme.py for structural changes, then run: uv run python build_readme.py
        Last generated: {generated_at}
        -->

        <div align="center">

        <img src="./assets/typing.svg" alt="Typing SVG">

        <br>

        [![GitHub followers](https://img.shields.io/github/followers/{USERNAME}?style=for-the-badge&logo=github&logoColor=white&color=8B5CF6)](https://github.com/{USERNAME})
        [![GitHub stars](https://img.shields.io/github/stars/{USERNAME}?style=for-the-badge&logo=githubsponsors&logoColor=white&color=EA580C)](https://github.com/{USERNAME})
        [![Profile Views](https://komarev.com/ghpvc/?username={USERNAME}&style=for-the-badge&color=blueviolet)](https://github.com/{USERNAME})

        </div>

        ## About Me

        <table>
        <tr>
        <td width="58%" valign="top">

        I work across the abstraction stack: training AI systems, building developer tools, and exploring operating-system internals.

        **What I Do**

        - Build and train neural networks and AI-powered tools.
        - Design secure, production-grade OS kernel experiments in Rust.
        - Create intelligent systems that can run close to the hardware.

        **Current Flagship Projects**

        {projects_md}

        **Tech Interests**

        - Rust for systems, safety, shells, and kernels.
        - Python for deep learning and automation.
        - Linux, Docker, compilers, and low-level tooling.

        **Belief**

        > Nothing is True, Everything is Permitted.

        </td>
        <td width="42%" valign="top">

        <img src="https://raw.githubusercontent.com/abhisheknaiidu/abhisheknaiidu/master/code.gif" width="100%" alt="Coding">

        </td>
        </tr>
        </table>

        ## Tech Stack

        <div align="center">

        {tech_md}

        </div>

        ## GitHub Overview

        <table>
        <tr>
        <td width="58%" valign="top">

        **Metrics**

        <img src="./github-metrics.svg" alt="GitHub Metrics" width="100%">

        </td>
        <td width="42%" valign="top">

        **Stats**

        <img src="./github-stats.svg" alt="Thefool's GitHub Stats" width="100%">

        **Language Stats**

        <img src="./assets/language-stats.svg" alt="Language Stats by Commits" width="100%">

        **3D Contribution**

        <img src="./profile-3d-contrib/profile-night-rainbow.svg" alt="GitHub Profile 3D Contribution" width="100%">

        **Pinned Projects**

        {project_cards_md}

        </td>
        </tr>
        </table>
        
        ## Connect

        <div align="center">

        I'm open to discussing OS development, AI tooling, systems programming, and collaboration opportunities.

        [![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/{USERNAME})
        [![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:thefoolyuzhe@gmail.com)
        [![Blog](https://img.shields.io/badge/Blog-thefool.chat-6366F1?style=for-the-badge&logo=ghost&logoColor=white)](https://blog.thefool.chat/)

        </div>
        """
    )


def refresh_generated_assets() -> None:
    fetch_svg(
        typing_url(),
        ASSETS / "typing.svg",
        "Hi! I'm Thefool",
        "Bridging Gap: AI & Bare Metal",
        height=80,
    )

    fetch_svg(
        stats_url(),
        ROOT / "github-stats.svg",
        "GitHub Stats",
        USERNAME,
        height=195,
    )

    for project in PROJECTS:
        slug = project_slug(project)
        fetch_svg(
            pin_url(project),
            ASSETS / f"pin-{slug}.svg",
            project["title"],
            project["description"],
            height=120,
        )

    write_language_stats()


def main() -> None:
    refresh_generated_assets()
    (ROOT / "README.md").write_text(render_readme().strip() + "\n", encoding="utf-8")
    print("updated README.md")


if __name__ == "__main__":
    main()
