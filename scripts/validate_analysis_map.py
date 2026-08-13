#!/usr/bin/env python3
"""Verify the M31 analysis map only selects, never alters, official province paths."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET

from build_analysis_map import SOURCE, SVG_NS, TARGET, TERRITORY_CONTEXT_PATHS, path_digest


def regions(path, role):
    return [
        item
        for item in ET.parse(path).getroot().iter(f"{{{SVG_NS}}}path")
        if item.get("data-region-role") == role
    ]


def validate() -> None:
    official = regions(SOURCE, "simulation-province")
    analysis = regions(TARGET, "simulation-province")
    if len(official) != 31 or len(analysis) != 31:
        raise ValueError("analysis map must contain exactly the frozen 31 provinces")
    expected = [(item.get("data-code"), item.get("d")) for item in official]
    actual = [(item.get("data-code"), item.get("d")) for item in analysis]
    if expected != actual:
        raise ValueError("analysis map geometry differs from the official 31-province source")
    source_root = ET.parse(SOURCE).getroot()
    official_context = [
        item
        for item in source_root.iter(f"{{{SVG_NS}}}path")
        if path_digest(item) in TERRITORY_CONTEXT_PATHS
    ]
    analysis_context = regions(TARGET, "territory-context")
    expected_context = [
        (
            TERRITORY_CONTEXT_PATHS[path_digest(item)][0],
            TERRITORY_CONTEXT_PATHS[path_digest(item)][1],
            item.get("d"),
        )
        for item in official_context
    ]
    actual_context = [
        (item.get("data-code"), item.get("name"), item.get("d")) for item in analysis_context
    ]
    if len(actual_context) != 3 or expected_context != actual_context:
        raise ValueError("analysis map must preserve Hong Kong, Macao and Taiwan context geometry")
    if any(item.get("data-in-simulation") != "false" for item in analysis_context):
        raise ValueError("territory context paths must remain outside the 31-province simulation")
    digest = hashlib.sha256("\n".join(item[1] or "" for item in actual).encode()).hexdigest()
    print(
        "Analysis map validation passed: "
        f"31 simulation provinces plus Hong Kong, Macao and Taiwan context verified ({digest})."
    )


if __name__ == "__main__":
    validate()
