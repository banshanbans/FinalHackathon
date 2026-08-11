#!/usr/bin/env python3
"""Render the deterministic 31×6 enterprise profile snapshot to stdout."""

import json

from simulation.data import build_enterprise_profiles


def main() -> None:
    profiles = [
        item.model_dump(mode="json") for _, item in sorted(build_enterprise_profiles().items())
    ]
    print(json.dumps(profiles, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
