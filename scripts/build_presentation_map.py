#!/usr/bin/env python3
"""Build a WebGL render projection from the frozen China analysis SVG paths.

The GeoJSON is a presentation-only coordinate projection. It preserves the
31-province simulation boundary while also displaying Hong Kong, Macao and
Taiwan as non-computational territory context. It samples the frozen cubic
Bezier paths without making geographic or distance claims.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "apps" / "web" / "src" / "assets" / "maps" / "china-analysis-map.svg"
OUTPUT_DIR = ROOT / "apps" / "presentation" / "public" / "assets"
TARGET = OUTPUT_DIR / "china-presentation-map.geojson"
FALLBACK = OUTPUT_DIR / "china-analysis-map.svg"
SVG_NS = "http://www.w3.org/2000/svg"
SOURCE_GEOMETRY_HASH = "2f6aea81b85e929df44aa83beb6c4dcf3fe8f14b8274506e62c6b836ac1c97d6"
TOKEN_RE = re.compile(r"[MLCZ]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
CURVE_STEPS = 24


@dataclass(frozen=True)
class RenderBounds:
    west: float
    east: float
    south: float = 18.0
    north: float = 54.0


def render_bounds_for(
    source_bounds: tuple[float, float, float, float],
) -> RenderBounds:
    """Choose Web Mercator bounds that preserve the SVG path aspect exactly."""
    left, top, right, bottom = source_bounds
    source_aspect = (right - left) / (bottom - top)
    mercator_height = mercator_y(54.0) - mercator_y(18.0)
    longitude_span = math.degrees(source_aspect * mercator_height)
    center_longitude = 105.0
    return RenderBounds(
        west=round(center_longitude - longitude_span / 2, 7),
        east=round(center_longitude + longitude_span / 2, 7),
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def svg_regions(path: Path, role: str = "simulation-province") -> list[ET.Element]:
    return [
        item
        for item in ET.parse(path).getroot().iter(f"{{{SVG_NS}}}path")
        if item.get("data-region-role") == role
    ]


def parse_path(
    path_data: str, *, curve_steps: int = CURVE_STEPS
) -> list[list[tuple[float, float]]]:
    tokens = TOKEN_RE.findall(path_data)
    index = 0
    cursor = (0.0, 0.0)
    current: list[tuple[float, float]] = []
    rings: list[list[tuple[float, float]]] = []

    def number() -> float:
        nonlocal index
        value = float(tokens[index])
        index += 1
        return value

    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "M":
            if current:
                rings.append(current)
            cursor = (number(), number())
            current = [cursor]
        elif command == "L":
            cursor = (number(), number())
            current.append(cursor)
        elif command == "C":
            control_1 = (number(), number())
            control_2 = (number(), number())
            end = (number(), number())
            start = cursor
            for step in range(1, curve_steps + 1):
                t = step / curve_steps
                inverse = 1 - t
                current.append(
                    (
                        inverse**3 * start[0]
                        + 3 * inverse**2 * t * control_1[0]
                        + 3 * inverse * t**2 * control_2[0]
                        + t**3 * end[0],
                        inverse**3 * start[1]
                        + 3 * inverse**2 * t * control_1[1]
                        + 3 * inverse * t**2 * control_2[1]
                        + t**3 * end[1],
                    )
                )
            cursor = end
        elif command == "Z":
            if current and current[-1] != current[0]:
                current.append(current[0])
            if current:
                rings.append(current)
                current = []
        else:
            raise ValueError(f"unsupported SVG path command: {command}")
    if current:
        if current[-1] != current[0]:
            current.append(current[0])
        rings.append(current)
    if not rings:
        raise ValueError("province path did not produce any closed rings")
    return rings


def path_bounds(regions: list[ET.Element]) -> tuple[float, float, float, float]:
    points = [
        point
        for region in regions
        for ring in parse_path(region.get("d", ""), curve_steps=CURVE_STEPS)
        for point in ring
    ]
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def mercator_y(latitude: float) -> float:
    radians = math.radians(latitude)
    return math.log(math.tan(math.pi / 4 + radians / 2))


def inverse_mercator_y(value: float) -> float:
    return math.degrees(2 * math.atan(math.exp(value)) - math.pi / 2)


def project_point(
    point: tuple[float, float],
    *,
    source_bounds: tuple[float, float, float, float],
    render_bounds: RenderBounds,
) -> list[float]:
    left, top, right, bottom = source_bounds
    x_ratio = (point[0] - left) / (right - left)
    y_ratio = (point[1] - top) / (bottom - top)
    longitude = render_bounds.west + x_ratio * (render_bounds.east - render_bounds.west)
    north_y = mercator_y(render_bounds.north)
    south_y = mercator_y(render_bounds.south)
    latitude = inverse_mercator_y(north_y + y_ratio * (south_y - north_y))
    return [round(longitude, 7), round(latitude, 7)]


def build_collection() -> dict[str, object]:
    simulation_regions = svg_regions(SOURCE)
    context_regions = svg_regions(SOURCE, "territory-context")
    if len(simulation_regions) != 31:
        raise ValueError(f"expected 31 frozen province paths, received {len(simulation_regions)}")
    if len(context_regions) != 3:
        raise ValueError(
            f"expected Hong Kong, Macao and Taiwan context paths, received {len(context_regions)}"
        )
    regions = simulation_regions + context_regions
    codes = [item.get("data-code", "") for item in regions]
    if len(codes) != len(set(codes)):
        raise ValueError("frozen province paths contain duplicate codes")

    source_bounds = path_bounds(regions)
    render_bounds = render_bounds_for(source_bounds)
    features: list[dict[str, object]] = []
    for region in regions:
        path_data = region.get("d", "")
        role = region.get("data-region-role", "")
        projected_rings = [
            [
                project_point(
                    point,
                    source_bounds=source_bounds,
                    render_bounds=render_bounds,
                )
                for point in ring
            ]
            for ring in parse_path(path_data)
        ]
        features.append(
            {
                "type": "Feature",
                "id": region.get("data-code"),
                "properties": {
                    "province_code": region.get("data-code"),
                    "name": region.get("name"),
                    "region_role": role,
                    "included_in_simulation": role == "simulation-province",
                    "interactive": role == "simulation-province",
                    "representation": region.get("data-representation", "official-outline"),
                    "source_path_sha256": sha256_bytes(path_data.encode("utf-8")),
                    "source_subpath_count": len(projected_rings),
                    "render_vertex_count": sum(len(ring) for ring in projected_rings),
                },
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [[ring] for ring in projected_rings],
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "name": "policyscope-presentation-map-v2",
        "bbox": [
            render_bounds.west,
            render_bounds.south,
            render_bounds.east,
            render_bounds.north,
        ],
        "metadata": {
            "schema_version": "presentation-map-v2",
            "source": "china-analysis-map.svg",
            "source_standard_map": "GS(2016)1609",
            "source_svg_sha256": sha256_bytes(SOURCE.read_bytes()),
            "source_geometry_sha256": sha256_bytes(
                "\n".join(item.get("d", "") for item in regions).encode()
            ),
            "simulation_geometry_sha256": SOURCE_GEOMETRY_HASH,
            "projection": "svg-to-web-mercator-render-v3-complete-map",
            "render_only": True,
            "distance_analysis_allowed": False,
            "curve_sampling_steps": CURVE_STEPS,
            "source_aspect_ratio": round(
                (source_bounds[2] - source_bounds[0]) / (source_bounds[3] - source_bounds[1]),
                10,
            ),
            "source_bounds": list(source_bounds),
            "simulation_region_count": len(simulation_regions),
            "territory_context_count": len(context_regions),
            "territory_context_codes": ["71", "81", "82"],
            "disclaimer": "Presentation-only render projection; not geographic survey data.",
        },
        "features": features,
    }


def build() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    collection = build_collection()
    TARGET.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    shutil.copyfile(SOURCE, FALLBACK)
    print(
        "Presentation map built: "
        "31 simulation provinces plus 3 territory context regions, "
        f"{sha256_bytes(TARGET.read_bytes())}."
    )


if __name__ == "__main__":
    build()
