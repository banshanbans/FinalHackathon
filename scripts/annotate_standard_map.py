#!/usr/bin/env python3
"""Annotate the official EPS-derived SVG with stable province region names.

The source EPS is the 1:48,000,000 China map downloaded from the Ministry of
Natural Resources standard-map service.  pstoedit preserves the Illustrator
stacking order: path 0 is the ocean/background, path 1 is the national fill,
and paths 2..32 are the 31 mainland provincial fills. This script makes that
ordering explicit and reproducible for ECharts' SVG map parser.
"""

from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
PROVINCES: tuple[tuple[str, str], ...] = (
    ("15", "内蒙古"),
    ("23", "黑龙江"),
    ("22", "吉林"),
    ("21", "辽宁"),
    ("32", "江苏"),
    ("33", "浙江"),
    ("13", "河北"),
    ("37", "山东"),
    ("34", "安徽"),
    ("36", "江西"),
    ("35", "福建"),
    ("44", "广东"),
    ("14", "山西"),
    ("41", "河南"),
    ("42", "湖北"),
    ("43", "湖南"),
    ("45", "广西"),
    ("52", "贵州"),
    ("50", "重庆"),
    ("61", "陕西"),
    ("64", "宁夏"),
    ("51", "四川"),
    ("53", "云南"),
    ("63", "青海"),
    ("11", "北京"),
    ("12", "天津"),
    ("62", "甘肃"),
    ("65", "新疆"),
    ("54", "西藏"),
    ("31", "上海"),
    ("46", "海南"),
)

PROVINCE_PATH_START = 2
REGION_METADATA_ATTRIBUTES = ("id", "name", "data-code", "data-region-role")


def annotate(source: Path, destination: Path) -> None:
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    tree = ET.parse(source)
    root = tree.getroot()
    # ECharts' SVG parser does not always propagate inherited fill rules from
    # Illustrator groups.  Materialize them on paths so the large white frame
    # remains an even-odd ring instead of covering the provincial fills.
    for group in root.iter(f"{{{SVG_NS}}}g"):
        fill_rule = group.get("fill-rule")
        if fill_rule:
            for descendant in group.iter(f"{{{SVG_NS}}}path"):
                descendant.set("fill-rule", fill_rule)
    # The EPS contains a white even-odd page/frame mask. ECharts currently
    # flattens that compound path as an opaque rectangle and hides every
    # unselected province. Remove only that non-geographic mask; the map frame,
    # national boundary and all province boundary paths remain unchanged.
    frame_mask_start = "M 0 478.859"
    for parent in root.iter():
        for child in list(parent):
            if child.tag != f"{{{SVG_NS}}}path":
                continue
            normalized = " ".join(child.get("d", "").split())
            if normalized.startswith(frame_mask_start) and "M 32.2773 515.09" in normalized:
                parent.remove(child)
    paths = list(root.iter(f"{{{SVG_NS}}}path"))
    required_path_count = PROVINCE_PATH_START + len(PROVINCES)
    if len(paths) < required_path_count:
        raise ValueError(f"expected at least {required_path_count} paths, found {len(paths)}")

    # Clear prior generated metadata so the annotation step is idempotent and
    # an old offset cannot leave a second interactive region behind.
    for path in paths:
        for attribute in REGION_METADATA_ATTRIBUTES:
            path.attrib.pop(attribute, None)

    # Path zero is the sea/background and path one is the full national fill.
    # Paths 2..32 are the provincial fills in the source Illustrator order.
    province_paths = paths[PROVINCE_PATH_START:required_path_count]
    for path, (code, name) in zip(province_paths, PROVINCES, strict=True):
        path.set("id", f"province-{code}")
        path.set("name", name)
        path.set("data-code", code)
        path.set("data-region-role", "simulation-province")

    root.set("data-map-source", "MNR-standard-map-GS2016-1609")
    root.set("data-simulation-scope", "mainland-31")
    tree.write(destination, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    annotate(args.source, args.destination)


if __name__ == "__main__":
    main()
