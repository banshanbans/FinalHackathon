from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from build_presentation_map import inverse_mercator_y, mercator_y, parse_path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps/presentation/public/assets/china-standard-map.svg"
OUTPUT = ROOT / "apps/presentation/public/assets/china-south-sea-standard-overlay.svg"
DASHES_OUTPUT = ROOT / "apps/presentation/public/assets/china-south-sea-standard-dashes.svg"
DASHES_GEOJSON_OUTPUT = (
    ROOT / "apps/presentation/public/assets/china-south-sea-standard-dashes.geojson"
)
SVG_NS = "http://www.w3.org/2000/svg"
SOUTH_CHINA_SEA_VIEWBOX = "330 660 70 100"
SOUTH_CHINA_SEA_BOUNDS = (330.0, 660.0, 400.0, 760.0)
DASH_DISPLAY_BOUNDS = (106.0, 6.0, 127.5, 26.0)
PATH_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
DASH_PATH_GROUPS = (
    (20, 21, 22, 23),
    (24, 25, 26, 27),
    (28, 29, 30, 31),
    (36, 37, 38, 39),
    (40, 41, 42, 43),
    (44, 45, 46, 47),
    (48, 49, 50, 51),
    (52, 53, 54, 55),
    (102, 103, 104),
    (106, 107, 108),
    (129, 130, 131, 132),
    (133, 134, 135, 136),
)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _style_fill(style: str | None) -> str | None:
    if not style:
        return None
    for declaration in style.split(";"):
        key, separator, value = declaration.partition(":")
        if separator and key.strip() == "fill":
            return value.strip().lower()
    return None


def _collect_standard_ink(
    node: ET.Element,
    inherited_fill: str | None,
    output_group: ET.Element,
    collected_paths: list[ET.Element],
) -> int:
    fill = node.attrib.get("fill") or _style_fill(node.attrib.get("style")) or inherited_fill
    fill = fill.lower() if fill else None
    count = 0
    if (
        _local_name(node.tag) == "path"
        and fill in {"#000", "#000000", "black"}
        and _path_intersects_viewbox(node.attrib.get("d", ""))
    ):
        path = copy.deepcopy(node)
        path.attrib.pop("id", None)
        path.attrib.pop("fill", None)
        output_group.append(path)
        collected_paths.append(copy.deepcopy(path))
        return 1
    for child in node:
        count += _collect_standard_ink(child, fill, output_group, collected_paths)
    return count


def _path_intersects_viewbox(path_data: str) -> bool:
    values = [float(value) for value in PATH_NUMBER.findall(path_data)]
    if len(values) < 2:
        return False
    coordinates = list(zip(values[0::2], values[1::2], strict=True))
    min_x = min(point[0] for point in coordinates)
    max_x = max(point[0] for point in coordinates)
    min_y = min(point[1] for point in coordinates)
    max_y = max(point[1] for point in coordinates)
    west, north, east, south = SOUTH_CHINA_SEA_BOUNDS
    return max_x >= west and min_x <= east and max_y >= north and min_y <= south


def _principal_axis_segment(
    paths: list[ET.Element],
) -> tuple[tuple[float, float], tuple[float, float]]:
    points = [
        point for path in paths for ring in parse_path(path.attrib.get("d", "")) for point in ring
    ]
    if len(points) < 2:
        raise RuntimeError("dash symbol does not contain enough source points")
    center_x = sum(point[0] for point in points) / len(points)
    center_y = sum(point[1] for point in points) / len(points)
    variance_x = sum((point[0] - center_x) ** 2 for point in points)
    variance_y = sum((point[1] - center_y) ** 2 for point in points)
    covariance = sum((point[0] - center_x) * (point[1] - center_y) for point in points)
    angle = 0.5 * math.atan2(2 * covariance, variance_x - variance_y)
    axis_x = math.cos(angle)
    axis_y = math.sin(angle)
    projections = [
        (point[0] - center_x) * axis_x + (point[1] - center_y) * axis_y for point in points
    ]
    low = min(projections)
    high = max(projections)
    trim = (high - low) * 0.12
    low += trim
    high -= trim
    return (
        (center_x + axis_x * low, center_y + axis_y * low),
        (center_x + axis_x * high, center_y + axis_y * high),
    )


def _segment_bounds(
    segments: list[tuple[tuple[float, float], tuple[float, float]]],
) -> tuple[float, float, float, float]:
    points = [point for segment in segments for point in segment]
    padding = 0.45
    return (
        min(point[0] for point in points) - padding,
        min(point[1] for point in points) - padding,
        max(point[0] for point in points) + padding,
        max(point[1] for point in points) + padding,
    )


def _project_dash_point(
    point: tuple[float, float],
    source_bounds: tuple[float, float, float, float],
) -> list[float]:
    source_west, source_north, source_east, source_south = source_bounds
    display_west, display_south, display_east, display_north = DASH_DISPLAY_BOUNDS
    x_ratio = (point[0] - source_west) / (source_east - source_west)
    y_ratio = (point[1] - source_north) / (source_south - source_north)
    longitude = display_west + x_ratio * (display_east - display_west)
    north_y = mercator_y(display_north)
    south_y = mercator_y(display_south)
    latitude = inverse_mercator_y(north_y + y_ratio * (south_y - north_y))
    return [round(longitude, 7), round(latitude, 7)]


def _write_georeferenced_dashes(
    segments: list[tuple[tuple[float, float], tuple[float, float]]],
    path_groups: list[list[ET.Element]],
    source_bounds: tuple[float, float, float, float],
) -> None:
    features: list[dict[str, object]] = []
    if len(segments) != len(path_groups):
        raise RuntimeError("dash segment/source group count mismatch")
    for index, (segment, source_paths) in enumerate(zip(segments, path_groups, strict=True)):
        source_path_data = "|".join(path.attrib.get("d", "") for path in source_paths)
        features.append(
            {
                "type": "Feature",
                "id": f"south-china-sea-dash-{index + 1}",
                "properties": {
                    "source_path_indexes": list(DASH_PATH_GROUPS[index]),
                    "source_path_sha256": hashlib.sha256(
                        source_path_data.encode("utf-8")
                    ).hexdigest(),
                    "map_source": "MNR-standard-map-GS2016-1609",
                    "simulation_scope": "none",
                    "derivation": "principal-axis-of-official-dash-symbol",
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [_project_dash_point(point, source_bounds) for point in segment],
                },
            }
        )
    payload = {
        "type": "FeatureCollection",
        "name": "south-china-sea-discontinuous-line-map-layer-v1",
        "bbox": [
            DASH_DISPLAY_BOUNDS[0],
            DASH_DISPLAY_BOUNDS[1],
            DASH_DISPLAY_BOUNDS[2],
            DASH_DISPLAY_BOUNDS[3],
        ],
        "metadata": {
            "schema_version": "south-china-sea-cartography-v1",
            "map_source": "MNR-standard-map-GS2016-1609",
            "derivation": "official-dash-symbol-principal-axes-georeferenced-for-rendering",
            "source_viewbox": list(source_bounds),
            "display_bounds": list(DASH_DISPLAY_BOUNDS),
            "render_only": True,
            "distance_analysis_allowed": False,
            "simulation_scope": "none",
            "path_count": sum(len(group) for group in DASH_PATH_GROUPS),
            "segment_count": len(features),
        },
        "features": features,
    }
    DASHES_GEOJSON_OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def build() -> int:
    source_root = ET.parse(SOURCE).getroot()
    ET.register_namespace("", SVG_NS)
    output_root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": SOUTH_CHINA_SEA_VIEWBOX,
            "role": "img",
            "aria-label": "南海诸岛标准地图标注",
            "data-map-source": "MNR-standard-map-GS2016-1609",
            "data-derivation": "black-cartographic-ink-crop",
        },
    )
    ET.SubElement(output_root, f"{{{SVG_NS}}}title").text = "南海诸岛"
    output_group = ET.SubElement(
        output_root,
        f"{{{SVG_NS}}}g",
        {
            "fill": "#a9e6e5",
            "fill-rule": "evenodd",
        },
    )
    collected_paths: list[ET.Element] = []
    path_count = _collect_standard_ink(source_root, None, output_group, collected_paths)
    if path_count < 10:
        raise RuntimeError(f"unexpected standard-map ink path count: {path_count}")
    tree = ET.ElementTree(output_root)
    ET.indent(tree, space="  ")
    tree.write(OUTPUT, encoding="utf-8", xml_declaration=True)
    path_groups = [[collected_paths[index] for index in group] for group in DASH_PATH_GROUPS]
    dash_segments = [_principal_axis_segment(group) for group in path_groups]
    dash_source_bounds = _segment_bounds(dash_segments)
    source_west, source_north, source_east, source_south = dash_source_bounds
    dashes_root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": (
                f"{source_west:.4f} {source_north:.4f} "
                f"{source_east - source_west:.4f} {source_south - source_north:.4f}"
            ),
            "role": "img",
            "aria-label": "南海断续线标准地图标注",
            "data-map-source": "MNR-standard-map-GS2016-1609",
            "data-derivation": "principal-axes-from-official-discontinuous-line-symbols",
            "width": f"{source_east - source_west:.4f}",
            "height": f"{source_south - source_north:.4f}",
        },
    )
    ET.SubElement(dashes_root, f"{{{SVG_NS}}}title").text = "南海断续线"
    dashes_group = ET.SubElement(
        dashes_root,
        f"{{{SVG_NS}}}g",
        {
            "data-layer": "south-china-sea-discontinuous-line",
            "fill": "none",
            "stroke": "#bceeed",
            "stroke-linecap": "round",
            "stroke-width": ".42",
        },
    )
    for index, segment in enumerate(dash_segments):
        ET.SubElement(
            dashes_group,
            f"{{{SVG_NS}}}line",
            {
                "x1": f"{segment[0][0]:.4f}",
                "y1": f"{segment[0][1]:.4f}",
                "x2": f"{segment[1][0]:.4f}",
                "y2": f"{segment[1][1]:.4f}",
                "data-source-path-indexes": ",".join(
                    str(value) for value in DASH_PATH_GROUPS[index]
                ),
                "fill": "none",
                "stroke": "#bceeed",
                "stroke-linecap": "round",
                "stroke-width": ".42",
            },
        )
    if len(dashes_group) != len(DASH_PATH_GROUPS):
        raise RuntimeError(f"unexpected discontinuous-line path count: {len(dashes_group)}")
    dashes_tree = ET.ElementTree(dashes_root)
    ET.indent(dashes_tree, space="  ")
    dashes_tree.write(DASHES_OUTPUT, encoding="utf-8", xml_declaration=True)
    _write_georeferenced_dashes(dash_segments, path_groups, dash_source_bounds)
    return path_count


if __name__ == "__main__":
    print(f"south china sea standard overlay paths: {build()}")
