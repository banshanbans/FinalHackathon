#!/usr/bin/env python3
"""Derive the uncluttered M31 analysis map without changing official geometry."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

from annotate_standard_map import SVG_NS

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "apps" / "web" / "src" / "assets" / "maps"
SOURCE = MAP_DIR / "china-standard-map.svg"
TARGET = MAP_DIR / "china-analysis-map.svg"

# Frozen paths inside the same Ministry of Natural Resources standard map.
# Hong Kong and Taiwan use their official area outlines. At 1:48,000,000 the
# source represents Macao with a scale marker, which is preserved as-is.
TERRITORY_CONTEXT_PATHS: dict[str, tuple[str, str, str]] = {
    "818ef1662cf600181d83785547075f7ce79e30e0b9ff9d40d7b7a85cfa0534c7": (
        "81",
        "香港",
        "official-outline",
    ),
    "dc921ec509c87b8862110d4e1b2f19dcd88b28b67ef8be2efec3ca32466422f5": (
        "71",
        "台湾",
        "official-outline",
    ),
    "f8f72e25d7212035d95f1a85ff6dc61e96393a8575b70a10620ff22de53d73e8": (
        "82",
        "澳门",
        "official-scale-marker",
    ),
}


def path_digest(path: ET.Element) -> str:
    return hashlib.sha256(path.get("d", "").encode()).hexdigest()


def build() -> None:
    source_root = ET.parse(SOURCE).getroot()
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": source_root.get("viewBox", ""),
            "version": "1.1",
            "data-map-source": "MNR-standard-map-GS2016-1609-derived-analysis",
            "data-derived-from": "china-standard-map.svg",
        },
    )
    root.append(
        ET.Comment(
            "Derived only by selecting frozen official 31-province paths plus "
            "Hong Kong, Macao and Taiwan context paths; no geometry is redrawn."
        )
    )
    for path in source_root.iter(f"{{{SVG_NS}}}path"):
        if path.get("data-region-role") == "simulation-province":
            attributes = {
                "id": path.get("id", ""),
                "name": path.get("name", ""),
                "data-code": path.get("data-code", ""),
                "data-region-role": "simulation-province",
                "data-in-simulation": "true",
                "d": path.get("d", ""),
            }
        else:
            context = TERRITORY_CONTEXT_PATHS.get(path_digest(path))
            if context is None:
                continue
            code, name, representation = context
            attributes = {
                "id": f"territory-{code}",
                "name": name,
                "data-code": code,
                "data-region-role": "territory-context",
                "data-in-simulation": "false",
                "data-representation": representation,
                "d": path.get("d", ""),
            }
        root.append(ET.Element(f"{{{SVG_NS}}}path", attributes))
    ET.register_namespace("", SVG_NS)
    ET.ElementTree(root).write(TARGET, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    build()
