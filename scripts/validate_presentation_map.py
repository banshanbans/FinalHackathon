#!/usr/bin/env python3
"""Validate the presentation GeoJSON and SVG fallback against frozen paths."""

from __future__ import annotations

import json
import math

from build_presentation_map import (
    FALLBACK,
    SOURCE,
    TARGET,
    build_collection,
    mercator_y,
    sha256_bytes,
    svg_regions,
)


def coordinates(value):
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(item, int | float) for item in value)
    ):
        yield value
        return
    if isinstance(value, list):
        for item in value:
            yield from coordinates(item)


def validate() -> None:
    actual = json.loads(TARGET.read_text(encoding="utf-8"))
    expected = build_collection()
    if actual != expected:
        raise ValueError("presentation GeoJSON is stale or differs from the deterministic build")
    if FALLBACK.read_bytes() != SOURCE.read_bytes():
        raise ValueError("presentation SVG fallback differs from the frozen analysis map")

    simulation_source = svg_regions(SOURCE)
    context_source = svg_regions(SOURCE, "territory-context")
    source_by_code = {item.get("data-code"): item for item in simulation_source + context_source}
    features = actual.get("features", [])
    west, south, east, north = actual["bbox"]
    source_left, source_top, source_right, source_bottom = actual["metadata"]["source_bounds"]
    source_aspect = (source_right - source_left) / (source_bottom - source_top)
    render_aspect = math.radians(east - west) / (mercator_y(north) - mercator_y(south))
    if not math.isclose(source_aspect, render_aspect, rel_tol=1e-7, abs_tol=1e-7):
        raise ValueError("presentation Web Mercator bounds distort the frozen SVG aspect ratio")
    if actual["metadata"]["curve_sampling_steps"] < 24:
        raise ValueError("presentation curve sampling is too coarse for SVG outline fidelity")
    if len(features) != 34 or set(source_by_code) != {
        item["properties"]["province_code"] for item in features
    }:
        raise ValueError(
            "presentation map must cover 31 simulation provinces plus Hong Kong, Macao and Taiwan"
        )
    simulation_features = [
        item for item in features if item["properties"]["region_role"] == "simulation-province"
    ]
    context_features = [
        item for item in features if item["properties"]["region_role"] == "territory-context"
    ]
    if len(simulation_features) != 31 or len(context_features) != 3:
        raise ValueError("presentation map region role counts are invalid")
    if {item["properties"]["province_code"] for item in context_features} != {
        "71",
        "81",
        "82",
    }:
        raise ValueError("presentation map territory context code set is invalid")
    if any(
        item["properties"]["included_in_simulation"] or item["properties"]["interactive"]
        for item in context_features
    ):
        raise ValueError("territory context must not enter simulation or interaction")
    for feature in features:
        properties = feature["properties"]
        source_path = source_by_code[properties["province_code"]].get("d", "")
        if properties["source_path_sha256"] != sha256_bytes(source_path.encode("utf-8")):
            raise ValueError(f"source path hash mismatch for {properties['province_code']}")
        for polygon in feature["geometry"]["coordinates"]:
            ring = polygon[0]
            if ring[0] != ring[-1] or len(ring) < 4:
                raise ValueError(f"open or degenerate ring for {properties['province_code']}")
        for longitude, latitude in coordinates(feature["geometry"]["coordinates"]):
            if not (math.isfinite(longitude) and math.isfinite(latitude)):
                raise ValueError("presentation map contains a non-finite coordinate")
            if not (-180 <= longitude <= 180 and -85 <= latitude <= 85):
                raise ValueError("presentation map contains an invalid Web Mercator coordinate")
            if not (west <= longitude <= east and south <= latitude <= north):
                raise ValueError("presentation map coordinate exceeds its declared render bounds")
    print(
        "Presentation map validation passed: "
        "31 simulation provinces plus Hong Kong, Macao and Taiwan context, "
        f"GeoJSON {sha256_bytes(TARGET.read_bytes())}."
    )


if __name__ == "__main__":
    validate()
