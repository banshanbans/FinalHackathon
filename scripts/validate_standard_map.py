#!/usr/bin/env python3
"""Validate the frozen official-map asset and its 31 interactive regions."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

from annotate_standard_map import PROVINCES, SVG_NS

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "apps" / "web" / "src" / "assets" / "maps"
EPS_PATH = MAP_DIR / "source" / "4o28b0625501ad13015501ad2bfc0045.eps"
SVG_PATH = MAP_DIR / "china-standard-map.svg"
EPS_SHA256 = "48dcb75fce083d66ee58582368218413f28bbd39c803b75fde15390b1a0badf1"
PROVINCE_GEOMETRY_SHA256 = "3f4d35ae47742f8e272ca23621c4ed79e7b188036bbf2c0cfc44e160b2fa4197"


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate() -> None:
    if digest(EPS_PATH.read_bytes()) != EPS_SHA256:
        raise ValueError("official standard-map EPS checksum changed")

    root = ET.parse(SVG_PATH).getroot()
    regions = [
        path
        for path in root.iter(f"{{{SVG_NS}}}path")
        if path.get("data-region-role") == "simulation-province"
    ]
    actual = [(path.get("data-code"), path.get("name")) for path in regions]
    if actual != list(PROVINCES):
        raise ValueError("SVG does not contain the frozen 31-province ordering")
    if len({path.get("id") for path in regions}) != 31:
        raise ValueError("SVG province path IDs must be unique")

    geometry = "\n".join(path.get("d", "") for path in regions).encode()
    if digest(geometry) != PROVINCE_GEOMETRY_SHA256:
        raise ValueError("annotated province geometry changed after EPS conversion")
    if root.get("data-map-source") != "MNR-standard-map-GS2016-1609":
        raise ValueError("SVG source marker is missing")
    print("Map validation passed: official EPS checksum and 31 SVG regions verified.")


if __name__ == "__main__":
    validate()
