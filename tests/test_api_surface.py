from __future__ import annotations

import re
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "api-surface.md"
ROW = re.compile(
    r"^\|\s*`(?P<method>\w+)`\s*\|.*\|\s*(?P<verb>GET|POST)\s*\|"
    r"\s*(?P<rw>[RW])\s*\|\s*(?P<group>[\w /-]+?)\s*\|$"
)


def parse_rows() -> list[dict[str, str]]:
    return [
        match.groupdict() for line in DOC.read_text().splitlines() if (match := ROW.match(line))
    ]


def test_every_method_name_is_unique() -> None:
    methods = [row["method"] for row in parse_rows()]
    duplicates = {method for method in methods if methods.count(method) > 1}
    assert not duplicates, f"duplicated rows: {sorted(duplicates)}"


def test_count_matches_declared_total() -> None:
    text = DOC.read_text()
    declared_match = re.search(r"<!-- method-count: (\d+) -->", text)
    assert declared_match is not None
    assert len(parse_rows()) == int(declared_match.group(1)) == 62


def test_supported_count_excludes_only_obsolete_methods() -> None:
    text = DOC.read_text()
    supported_match = re.search(r"<!-- supported-count: (\d+) -->", text)
    assert supported_match is not None
    assert int(supported_match.group(1)) == 59
    assert text.count("Excluded: Microsoft marks this method `Obsolete`") == 3


def test_known_anchor_methods_are_present() -> None:
    methods = {row["method"] for row in parse_rows()}
    assert {"GetUserSites", "AddSite", "SubmitUrlBatch", "GetUrlSubmissionQuota"} <= methods


def test_fetchurl_is_classified_as_a_post_write() -> None:
    rows = {row["method"]: row for row in parse_rows()}
    assert rows["FetchUrl"]["verb"] == "POST"
    assert rows["FetchUrl"]["rw"] == "W"
