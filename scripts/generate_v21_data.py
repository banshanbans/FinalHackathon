#!/usr/bin/env python3
import json

from simulation.data import DATA_DIR, build_province_personas, build_province_profiles


def _write_snapshot(name: str, values: list[dict[str, object]]) -> None:
    path = DATA_DIR / name
    path.write_text(
        json.dumps(values, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    profiles = build_province_profiles()
    personas = build_province_personas(profiles)
    _write_snapshot(
        "province_profiles_v3.json",
        [item.model_dump(mode="json") for _, item in sorted(profiles.items())],
    )
    _write_snapshot(
        "province_personas_v1.json",
        [item.model_dump(mode="json") for _, item in sorted(personas.items())],
    )
    print("Generated 31 V3 province profiles and 31 deterministic personas.")


if __name__ == "__main__":
    main()
