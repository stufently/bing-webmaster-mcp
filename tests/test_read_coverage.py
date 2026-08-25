from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "api-surface.md"
ROW = re.compile(r"^\|\s*`(?P<method>\w+)`\s*\|.*\|\s*(?P<rw>[RW])\s*\|")
MODULES = (
    "sites",
    "traffic",
    "crawl",
    "submission",
    "sitemaps",
    "blocking",
    "params",
    "geo",
    "links",
    "keywords",
)
EXCLUDED = {"GetDeepLinkAlgoUrls", "GetDeepLink"}


def test_every_supported_read_appears_in_exactly_one_domain_module() -> None:
    sources = {
        name: (ROOT / "bing_webmaster_mcp" / "ops" / f"{name}.py").read_text() for name in MODULES
    }
    missing: list[str] = []
    duplicated: list[str] = []
    for line in DOC.read_text().splitlines():
        match = ROW.match(line)
        if match is None or match["rw"] != "R" or match["method"] in EXCLUDED:
            continue
        count = sum(f'"{match["method"]}"' in source for source in sources.values())
        if count == 0:
            missing.append(match["method"])
        elif count > 1:
            duplicated.append(match["method"])
    assert not missing
    assert not duplicated
