from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import re
import sys
import textwrap
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).parent.resolve()
ASSETS = ROOT / "assets"
PINNED_PROJECTS_CACHE = ASSETS / "pinned-projects.json"

USERNAME = "YUZHEthefool"
STATS_BASE_URL = (
    "https://github-readme-stats-o6e3b1z1k-thefoolyuzhe-5613s-projects.vercel.app"
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
README_OFFLINE = os.environ.get("README_OFFLINE") == "1"
THEME = "tokyonight"
OVERVIEW_CARD_WIDTH = 500
PINNED_PROJECT_LIMIT = 6
PINNED_PROJECTS_TARGET_HEIGHT = 816
REPOSITORY_CARD_MIN_HEIGHT = 132
REPOSITORY_CARD_MAX_HEIGHT = 204
FOCUS_PROJECT_LIMIT = 4
STATS_CACHE_SECONDS = 21600
LANGUAGE_WINDOW_DAYS = 365

FALLBACK_PROJECTS = [
    {
        "owner": "farion1231",
        "repo": "cc-switch",
        "title": "CC Switch",
        "description": "Maintainer of the cross-platform AI coding assistant manager; working on pricing sync and Grok Build support.",
    },
    {
        "owner": "apache",
        "repo": "arrow-rs",
        "title": "arrow-rs",
        "description": "Official Rust implementation of Apache Arrow.",
    },
    {
        "owner": "rust-lang",
        "repo": "rust",
        "title": "rust",
        "description": "Empowering everyone to build reliable and efficient software.",
    },
    {
        "owner": "rust-lang",
        "repo": "rust-analyzer",
        "title": "rust-analyzer",
        "description": "A Rust compiler front-end for IDEs.",
    },
    {
        "owner": "Zero-kernel",
        "repo": "Nilix",
        "title": "Nilix",
        "description": "A monolithic kernel in pure Rust, inspired by the Linux kernel.",
    },
    {
        "owner": "Xero-Team",
        "repo": "zpdf",
        "title": "zpdf",
        "description": "A PDF parsing library written in pure Rust.",
    },
]

PROJECT_OVERRIDES = {
    "farion1231/cc-switch": {
        "title": "CC Switch",
        "description": "Maintainer of the cross-platform AI coding assistant manager; working on pricing sync and Grok Build support.",
    },
}

PROJECTS = [project.copy() for project in FALLBACK_PROJECTS]

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
SVG_ERROR_MARKERS = (
    "Something went wrong! file an issue at https://tiny.one/readme-stats",
    "Cannot read properties of undefined",
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
            "card_width": str(OVERVIEW_CARD_WIDTH),
            "cache_seconds": str(STATS_CACHE_SECONDS),
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


def project_slug(project: dict[str, str]) -> str:
    raw = f'{project["owner"]}-{project["repo"]}'.lower()
    return re.sub(r"[^a-z0-9]+", "-", raw).strip("-")


def repository_card_height() -> int:
    project_count = max(1, len(PROJECTS))
    calculated = round(PINNED_PROJECTS_TARGET_HEIGHT / project_count)
    return max(
        REPOSITORY_CARD_MIN_HEIGHT,
        min(REPOSITORY_CARD_MAX_HEIGHT, calculated),
    )


def wrap_project_description(description: str) -> list[str]:
    has_wide_characters = any(
        unicodedata.east_asian_width(character) in {"W", "F"}
        for character in description
    )
    return textwrap.wrap(
        description,
        width=34 if has_wide_characters else 66,
        max_lines=2,
        placeholder="...",
    ) or [""]


def focus_description(description: str) -> str:
    has_wide_characters = any(
        unicodedata.east_asian_width(character) in {"W", "F"}
        for character in description
    )
    limit = 30 if has_wide_characters else 54
    return description if len(description) <= limit else description[: limit - 3] + "..."


def sync_project_pin_assets() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    expected = {
        ASSETS / f"pin-{project_slug(project)}.svg": project
        for project in PROJECTS
    }

    for target in ASSETS.glob("pin-*.svg"):
        if target not in expected:
            target.unlink()
            print(f"removed stale {target.relative_to(ROOT)}")


def sanitize_svg(data: str) -> str:
    data = data.strip().lstrip("\ufeff")
    return BARE_AMPERSAND.sub("&amp;", data)


def is_valid_svg(data: str) -> bool:
    if not data:
        return False
    if any(marker.lower() in data.lower() for marker in SVG_ERROR_MARKERS):
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
    width = OVERVIEW_CARD_WIDTH
    compact = height <= 130
    title_y = 34 if compact else 54
    subtitle_y = 58 if compact else 92
    footer_y = height - 12 if compact else height - 34
    subtitle_size = 13 if compact else 16
    line_height = 16 if compact else 20
    subtitle_lines = textwrap.wrap(
        subtitle,
        width=64 if compact else 52,
        max_lines=2,
        placeholder="...",
    ) or [""]
    subtitle_spans = "\n".join(
        f'<tspan x="28" dy="{0 if index == 0 else line_height}">'
        f"{html.escape(line, quote=True)}</tspan>"
        for index, line in enumerate(subtitle_lines)
    )
    return textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{safe_title}">
          <rect width="{width}" height="{height}" rx="12" fill="#1a1b27"/>
          <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="11" fill="none" stroke="#2f334d"/>
          <text x="28" y="{title_y}" fill="#70a5fd" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="24" font-weight="700">{safe_title}</text>
          <text x="28" y="{subtitle_y}" fill="#c3d3ff" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="{subtitle_size}">{subtitle_spans}</text>
          <text x="28" y="{footer_y}" fill="#7982a9" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12">Generated fallback - waiting for stats API</text>
        </svg>
        """
    ).strip()


def github_rest_request(path: str) -> dict[str, object]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "YUZHEthefool-readme-builder/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("GitHub REST response is not an object")
    return payload


def fetch_repository(project: dict[str, str]) -> dict[str, object]:
    owner = quote(project["owner"])
    repo = quote(project["repo"])
    return github_rest_request(f"/repos/{owner}/{repo}")


def compact_count(value: object) -> str:
    try:
        count = int(value or 0)
    except (TypeError, ValueError):
        count = 0
    for threshold, suffix in ((1_000_000, "m"), (1_000, "k")):
        if count >= threshold:
            result = f"{count / threshold:.1f}".rstrip("0").rstrip(".")
            return f"{result}{suffix}"
    return str(count)


def repository_card_svg(
    project: dict[str, str], repository: dict[str, object] | None
) -> str:
    width = OVERVIEW_CARD_WIDTH
    height = repository_card_height()
    title = html.escape(project["title"], quote=True)
    full_name = html.escape(
        str(repository.get("full_name"))
        if repository and repository.get("full_name")
        else f'{project["owner"]}/{project["repo"]}',
        quote=True,
    )
    description_lines = wrap_project_description(project["description"])
    description_spans = "\n".join(
        f'<tspan x="24" dy="{0 if index == 0 else 17}">'
        f"{html.escape(line, quote=True)}</tspan>"
        for index, line in enumerate(description_lines)
    )

    language_value = repository.get("language") if repository else None
    language = str(language_value) if language_value else "Repository"
    language_color = LANGUAGE_FALLBACK_COLORS.get(
        normalize_language(language),
        LANGUAGE_FALLBACK_COLORS["Other"],
    )
    stars = compact_count(repository.get("stargazers_count")) if repository else "-"
    forks = compact_count(repository.get("forks_count")) if repository else "-"
    updated_value = repository.get("pushed_at") if repository else None
    updated = str(updated_value)[:10] if updated_value else "unavailable"
    default_branch_value = repository.get("default_branch") if repository else None
    default_branch = str(default_branch_value) if default_branch_value else "-"
    license_data = repository.get("license") if repository else None
    license_value = license_data.get("spdx_id") if isinstance(license_data, dict) else None
    license_name = str(license_value) if license_value and license_value != "NOASSERTION" else "-"

    if height >= REPOSITORY_CARD_MAX_HEIGHT:
        content = f"""
          <text x="24" y="34" fill="#70a5fd" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="18" font-weight="700">{title}</text>
          <text x="24" y="55" fill="#7982a9" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">{full_name}</text>
          <text x="24" y="84" fill="#c3d3ff" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12.5">{description_spans}</text>
          <line x1="24" y1="126" x2="476" y2="126" stroke="#2f334d"/>
          <circle cx="28" cy="149" r="5" fill="{language_color}"/>
          <text x="40" y="153" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">{html.escape(language, quote=True)}</text>
          <text x="165" y="153" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">License {html.escape(license_name, quote=True)}</text>
          <text x="280" y="153" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Stars {stars}</text>
          <text x="380" y="153" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Forks {forks}</text>
          <text x="24" y="181" fill="#7982a9" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="10.5">Branch {html.escape(default_branch, quote=True)}</text>
          <text x="476" y="181" text-anchor="end" fill="#7982a9" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="10.5">Updated {updated}</text>
        """
    else:
        metadata_y = height - 13
        content = f"""
          <text x="24" y="30" fill="#70a5fd" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="18" font-weight="700">{title}</text>
          <text x="24" y="48" fill="#7982a9" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">{full_name}</text>
          <text x="24" y="72" fill="#c3d3ff" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12.5">{description_spans}</text>
          <circle cx="28" cy="{metadata_y - 4}" r="5" fill="{language_color}"/>
          <text x="40" y="{metadata_y}" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">{html.escape(language, quote=True)}</text>
          <text x="178" y="{metadata_y}" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Stars {stars}</text>
          <text x="258" y="{metadata_y}" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">Forks {forks}</text>
          <text x="350" y="{metadata_y}" fill="#7982a9" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="10.5">Updated {updated}</text>
        """

    return textwrap.dedent(
        f"""\
        <svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="xMinYMin meet" role="img" aria-label="{title} repository card">
          <!-- generated-by: build_readme.py repository_card_svg v3 -->
          <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="7" fill="#1a1b27" stroke="#2f334d"/>
        {content}
        </svg>
        """
    ).strip()


def write_project_pin_cards() -> None:
    for project in PROJECTS:
        target = ASSETS / f"pin-{project_slug(project)}.svg"
        repository = None
        if not README_OFFLINE:
            try:
                repository = fetch_repository(project)
            except Exception as exc:  # noqa: BLE001 - preserve the last usable card
                print(
                    f"could not refresh {project['owner']}/{project['repo']}: {exc}",
                    file=sys.stderr,
                )

        existing = read_existing_svg(target)
        if repository is None and existing is not None:
            print(f"kept {target.relative_to(ROOT)}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            repository_card_svg(project, repository) + "\n",
            encoding="utf-8",
        )
        print(f"updated {target.relative_to(ROOT)}")


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


def normalize_project(value: object) -> dict[str, str] | None:
    if not isinstance(value, dict):
        return None
    owner = value.get("owner")
    repo = value.get("repo")
    title = value.get("title")
    description = value.get("description")
    if not all(isinstance(item, str) and item.strip() for item in (owner, repo, title)):
        return None
    return {
        "owner": owner.strip(),
        "repo": repo.strip(),
        "title": title.strip(),
        "description": description.strip()
        if isinstance(description, str) and description.strip()
        else f"{title.strip()} repository.",
    }


def fetch_pinned_projects() -> list[dict[str, str]]:
    query = """
    query($login: String!, $count: Int!) {
      user(login: $login) {
        pinnedItems(first: $count, types: REPOSITORY) {
          nodes {
            ... on Repository {
              name
              description
              owner {
                login
              }
            }
          }
        }
      }
    }
    """
    data = graphql_request(
        query,
        {"login": USERNAME, "count": PINNED_PROJECT_LIMIT},
    )
    user = data.get("user")
    if not isinstance(user, dict):
        raise RuntimeError(f"GitHub user {USERNAME} was not found")
    pinned_items = user.get("pinnedItems")
    nodes = pinned_items.get("nodes") if isinstance(pinned_items, dict) else None
    if not isinstance(nodes, list):
        raise RuntimeError("GitHub pinnedItems response is missing nodes")

    projects = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        owner_data = node.get("owner")
        owner = owner_data.get("login") if isinstance(owner_data, dict) else None
        repo = node.get("name")
        if not isinstance(owner, str) or not isinstance(repo, str):
            continue
        key = f"{owner}/{repo}".lower()
        override = PROJECT_OVERRIDES.get(key, {})
        project = normalize_project(
            {
                "owner": owner,
                "repo": repo,
                "title": override.get("title") or repo,
                "description": override.get("description")
                or node.get("description")
                or f"{repo} repository.",
            }
        )
        if project:
            projects.append(project)

    if not projects:
        raise RuntimeError("GitHub profile has no pinned repositories")
    return projects


def read_pinned_projects_cache() -> list[dict[str, str]]:
    if not PINNED_PROJECTS_CACHE.exists():
        return []
    try:
        payload = json.loads(PINNED_PROJECTS_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [project for item in payload if (project := normalize_project(item))]


def write_pinned_projects_cache(projects: list[dict[str, str]]) -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    PINNED_PROJECTS_CACHE.write_text(
        json.dumps(projects, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"updated {PINNED_PROJECTS_CACHE.relative_to(ROOT)}")


def load_projects() -> None:
    global PROJECTS

    if not README_OFFLINE:
        try:
            PROJECTS = fetch_pinned_projects()
            write_pinned_projects_cache(PROJECTS)
            print(f"loaded {len(PROJECTS)} pinned repositories from GitHub")
            return
        except Exception as exc:  # noqa: BLE001 - cached projects keep README stable
            print(f"could not load GitHub pinned repositories: {exc}", file=sys.stderr)

    cached = read_pinned_projects_cache()
    if cached:
        PROJECTS = cached
        print(f"loaded {len(PROJECTS)} pinned repositories from cache")
        return

    PROJECTS = [project.copy() for project in FALLBACK_PROJECTS]
    print(f"using {len(PROJECTS)} fallback pinned repositories")


def normalize_language(language: str) -> str:
    if language in {"C", "C++"}:
        return "C/C++"
    return language


def make_repository_alias(index: int) -> str:
    return f"repo{index}"


def fetch_language_stats() -> dict[str, object]:
    since = (
        dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=LANGUAGE_WINDOW_DAYS)
    ).isoformat(timespec="seconds")
    query_parts = [
        "query($since: GitTimestamp!) {",
    ]
    for index, project in enumerate(PROJECTS):
        alias = make_repository_alias(index)
        query_parts.append(
            f"""
            {alias}: repository(owner: "{project['owner']}", name: "{project['repo']}") {{
              defaultBranchRef {{
                target {{
                  ... on Commit {{
                    history(since: $since) {{
                      totalCount
                    }}
                  }}
                }}
              }}
              languages(first: 10, orderBy: {{field: SIZE, direction: DESC}}) {{
                totalSize
                edges {{
                  size
                  node {{
                    name
                    color
                  }}
                }}
              }}
            }}
            """
        )
    query_parts.append("}")
    query = "\n".join(query_parts)

    repos = 0
    total_commits = 0
    language_commits: dict[str, float] = {}
    language_colors: dict[str, str] = {}

    data = graphql_request(query, {"since": since})
    for index, project in enumerate(PROJECTS):
        repo = data.get(make_repository_alias(index))
        if not repo:
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
        "scope": "flagship repositories",
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
    scope = str(stats.get("scope") or "repositories")
    dominant = languages[0] if languages else {
        "name": "No data",
        "commits": 0,
        "color": LANGUAGE_FALLBACK_COLORS["Other"],
    }
    dominant_pct = (dominant["commits"] / total_commits * 100) if total_commits else 0

    width = OVERVIEW_CARD_WIDTH
    height = 420
    chart_cx = 118
    chart_cy = 180
    outer_radius = 76
    inner_radius = 50
    row_x = 232
    row_y = 112
    row_gap = 34
    commit_x = 355
    bar_x = 368
    bar_width = 62
    percent_x = 472

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="Language Stats by Commits">',
        "<!-- generated-by: build_readme.py language_stats_svg v2 -->",
        "<defs>",
        '<filter id="shadow" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity="0.35"/></filter>',
        '<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#0f1722"/><stop offset="1" stop-color="#05090f"/></linearGradient>',
        "</defs>",
        '<rect x="1" y="1" width="498" height="418" rx="14" fill="url(#panel)" stroke="#202b38"/>',
        '<text x="24" y="38" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="23" font-weight="700">Language Stats</text>',
        '<text x="205" y="38" fill="#58a6ff" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="16" font-weight="700">(by Commits)</text>',
        '<rect x="356" y="18" width="120" height="28" rx="14" fill="#132235"/>',
        '<text x="373" y="37" fill="#58a6ff" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12" font-weight="700">GraphQL API</text>',
        f'<text x="24" y="66" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12">Based on {total_commits:,} commits across {repos} {html.escape(scope)} - Last 12 months</text>',
        '<rect x="24" y="84" width="452" height="230" rx="12" fill="#071018" stroke="#1b2733"/>',
        '<rect x="24" y="330" width="452" height="58" rx="12" fill="#071018" stroke="#1b2733"/>',
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
            f'<text x="{chart_cx}" y="{chart_cy - 4}" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="15" font-weight="700">{html.escape(str(dominant["name"]))}</text>',
            f'<text x="{chart_cx}" y="{chart_cy + 28}" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="25" font-weight="800">{dominant_pct:.1f}%</text>',
        ]
    )

    for index, item in enumerate(languages):
        y = row_y + index * row_gap
        commits = int(item["commits"])
        pct = commits / total_commits * 100 if total_commits else 0
        bar_fill = min(bar_width, max(1.5, bar_width * pct / 100))
        name = html.escape(str(item["name"]))
        color = item["color"]
        parts.extend(
            [
                f'<circle cx="{row_x}" cy="{y}" r="6" fill="{color}"/>',
                f'<text x="{row_x + 14}" y="{y + 5}" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12.5" font-weight="700">{name}</text>',
                f'<text x="{commit_x}" y="{y + 5}" text-anchor="end" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11">{commits:,}</text>',
                f'<rect x="{bar_x}" y="{y - 5}" width="{bar_width}" height="9" rx="4.5" fill="#202933"/>',
                f'<rect x="{bar_x}" y="{y - 5}" width="{bar_fill:.2f}" height="9" rx="4.5" fill="{color}"/>',
                f'<text x="{percent_x}" y="{y + 5}" text-anchor="end" fill="{color}" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11.5" font-weight="700">{pct:.1f}%</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="62" y="359" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="17" font-weight="800">{total_commits:,}</text>',
            '<text x="62" y="376" text-anchor="middle" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="10.5">Commits</text>',
            f'<text x="184" y="359" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="17" font-weight="800">{repos}</text>',
            '<text x="184" y="376" text-anchor="middle" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="10.5">Repositories</text>',
            f'<text x="306" y="359" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="17" font-weight="800">{days}</text>',
            '<text x="306" y="376" text-anchor="middle" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="10.5">Days</text>',
            f'<text x="426" y="359" text-anchor="middle" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12.5" font-weight="700">{updated}</text>',
            '<text x="426" y="376" text-anchor="middle" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="10.5">Updated</text>',
            '<text x="24" y="406" fill="#8f9bad" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="10.5">Data source: GitHub GraphQL API - flagship commit history weighted by repo languages</text>',
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
        existing = read_existing_svg(target)
        fallback = (
            existing
            if existing and "generated-by: build_readme.py language_stats_svg v2" in existing
            else language_stats_svg(
            {
                "languages": [
                    {"name": "Rust", "commits": 75, "color": LANGUAGE_FALLBACK_COLORS["Rust"]},
                    {"name": "Python", "commits": 12, "color": LANGUAGE_FALLBACK_COLORS["Python"]},
                    {"name": "Go", "commits": 8, "color": LANGUAGE_FALLBACK_COLORS["Go"]},
                    {"name": "TypeScript", "commits": 3, "color": LANGUAGE_FALLBACK_COLORS["TypeScript"]},
                    {"name": "Other", "commits": 2, "color": LANGUAGE_FALLBACK_COLORS["Other"]},
                ],
                "total_commits": 100,
                "repositories": len(PROJECTS),
                "days": LANGUAGE_WINDOW_DAYS,
                "updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"),
                "scope": "flagship repositories",
            }
        )
        )
        target.write_text(fallback + "\n", encoding="utf-8")
        print(f"using fallback for {target.relative_to(ROOT)}: {exc}", file=sys.stderr)


def focus_card_svg() -> str:
    row_colors = ["#f7812b", "#58a6ff", "#8b6fe8", "#73c255"]
    rows = [
        (
            html.escape(project["title"], quote=True),
            html.escape(focus_description(project["description"]), quote=True),
            row_colors[index],
        )
        for index, project in enumerate(PROJECTS[:FOCUS_PROJECT_LIMIT])
    ]
    tags = [
        ("AI Systems", "#58a6ff"),
        ("Bare Metal", "#f7812b"),
        ("Rust", "#73c255"),
        ("Tooling", "#8b6fe8"),
    ]

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="500" height="310" viewBox="0 0 500 310" role="img" aria-label="Current Focus">',
        "<!-- generated-by: build_readme.py focus_card_svg v1 -->",
        "<defs>",
        '<linearGradient id="focusPanel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101923"/><stop offset="1" stop-color="#060a10"/></linearGradient>',
        '<filter id="focusShadow" x="-10%" y="-10%" width="120%" height="120%"><feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#000" flood-opacity="0.32"/></filter>',
        "</defs>",
        '<rect x="1" y="1" width="498" height="308" rx="14" fill="url(#focusPanel)" stroke="#202b38"/>',
        '<text x="24" y="38" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="23" font-weight="800">Current Focus</text>',
        '<text x="24" y="64" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="12">Building practical systems where AI meets low-level software.</text>',
    ]

    y = 92
    for title, subtitle, color in rows:
        parts.extend(
            [
                f'<rect x="24" y="{y - 18}" width="452" height="42" rx="10" fill="#071018" stroke="#1b2733" filter="url(#focusShadow)"/>',
                f'<circle cx="44" cy="{y + 3}" r="6" fill="{color}"/>',
                f'<text x="62" y="{y}" fill="#f4f7fb" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="14" font-weight="800">{title}</text>',
                f'<text x="62" y="{y + 17}" fill="#aab4c3" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11.5">{subtitle}</text>',
            ]
        )
        y += 47

    tag_x = 24
    for label, color in tags:
        width = 72 + max(0, len(label) - 6) * 4
        parts.extend(
            [
                f'<rect x="{tag_x}" y="272" width="{width}" height="24" rx="12" fill="#101b29" stroke="{color}" stroke-opacity="0.55"/>',
                f'<text x="{tag_x + width / 2:.1f}" y="288" text-anchor="middle" fill="{color}" font-family="Segoe UI, Ubuntu, Arial, sans-serif" font-size="11" font-weight="700">{label}</text>',
            ]
        )
        tag_x += width + 10

    parts.append("</svg>")
    return "\n".join(parts)


def write_focus_card() -> None:
    target = ASSETS / "focus-card.svg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(focus_card_svg() + "\n", encoding="utf-8")
    print(f"updated {target.relative_to(ROOT)}")


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
          <img src="./assets/pin-{slug}.svg" alt="{alt}" width="{OVERVIEW_CARD_WIDTH}">
        </a>
        """
    ).strip()


def project_cards() -> str:
    return "\n\n".join(project_card(project) for project in PROJECTS)


def project_list() -> str:
    items = []
    for project in PROJECTS:
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

        <br>

        <img src="./assets/focus-card.svg" width="100%" alt="Current Focus">

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

        <img src="./github-stats.svg" alt="Thefool's GitHub Stats" width="{OVERVIEW_CARD_WIDTH}">

        **Language Stats**

        <img src="./assets/language-stats.svg" alt="Language Stats by Commits" width="{OVERVIEW_CARD_WIDTH}">

        **3D Contribution**

        <img src="./profile-3d-contrib/profile-night-rainbow.svg" alt="GitHub Profile 3D Contribution" width="{OVERVIEW_CARD_WIDTH}">

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
    write_focus_card()
    sync_project_pin_assets()
    write_project_pin_cards()

    if README_OFFLINE:
        print("skipping remote asset refresh because README_OFFLINE=1")
        return

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

    write_language_stats()


def main() -> None:
    load_projects()
    refresh_generated_assets()
    (ROOT / "README.md").write_text(render_readme().strip() + "\n", encoding="utf-8")
    print("updated README.md")


if __name__ == "__main__":
    main()
