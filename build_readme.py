from __future__ import annotations

import datetime as dt
import html
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
THEME = "tokyonight"

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

        # Hi, I'm Thefool

        **Bridging AI systems and bare metal.**

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


def main() -> None:
    refresh_generated_assets()
    (ROOT / "README.md").write_text(render_readme().strip() + "\n", encoding="utf-8")
    print("updated README.md")


if __name__ == "__main__":
    main()
