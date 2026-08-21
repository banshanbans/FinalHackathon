#!/usr/bin/env python3
"""Validate the public repository surface without third-party dependencies."""

from __future__ import annotations

import re
import struct
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
FINALIST_COPY = "**抖音 AI 创变者计划 2026 北京全国总决赛作品**"
EXPECTED_SCREENSHOT_SIZE = (1600, 900)
REQUIRED_PATHS = (
    "apps/api",
    "apps/presentation",
    "apps/roadshow",
    "apps/web",
    "simulation",
    "data",
    "config",
    "docs/README.md",
    "runtime/cache/README.md",
    "NOTICE.md",
    "THIRD_PARTY_NOTICES.md",
    "SECURITY.md",
    ".github/workflows/quality.yml",
)
REQUIRED_MAKE_TARGETS = (
    "setup",
    "dev-api",
    "dev-presentation",
    "test",
    "lint",
    "validate-data",
    "build",
    "docker-build",
    "check",
)
CORE_MARKDOWN = (
    "README.md",
    "docs/README.md",
    "NOTICE.md",
    "THIRD_PARTY_NOTICES.md",
    "SECURITY.md",
)
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def relative_destination(raw: str) -> str | None:
    destination = raw.strip().split(maxsplit=1)[0].strip("<>")
    if not destination or destination.startswith("#"):
        return None
    if re.match(r"^[a-z][a-z0-9+.-]*:", destination, flags=re.IGNORECASE):
        return None
    return unquote(destination.split("#", 1)[0].split("?", 1)[0])


def image_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return struct.unpack(">II", header[16:24])
        if not header.startswith(b"\xff\xd8"):
            raise ValueError("unsupported image format")
        handle.seek(2)
        while True:
            marker_start = handle.read(1)
            if not marker_start:
                break
            if marker_start != b"\xff":
                continue
            marker = handle.read(1)
            while marker == b"\xff":
                marker = handle.read(1)
            if marker in {bytes([value]) for value in range(0xC0, 0xC4)} | {
                bytes([value]) for value in range(0xC5, 0xC8)
            } | {bytes([value]) for value in range(0xC9, 0xCC)} | {
                bytes([value]) for value in range(0xCD, 0xD0)
            }:
                length = struct.unpack(">H", handle.read(2))[0]
                payload = handle.read(length - 2)
                height, width = struct.unpack(">HH", payload[1:5])
                return width, height
            length_bytes = handle.read(2)
            if len(length_bytes) != 2:
                break
            handle.seek(struct.unpack(">H", length_bytes)[0] - 2, 1)
    raise ValueError("JPEG dimensions not found")


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [item for item in result.stdout.split("\0") if item]


def forbidden_tracked_reason(path: str) -> str | None:
    parts = Path(path).parts
    basename = parts[-1]
    if path.startswith("runtime/cache/") and path != "runtime/cache/README.md":
        return "runtime cache"
    if any(
        part in {"node_modules", "dist", "output", "outputs", ".playwright-cli"} for part in parts
    ):
        return "generated directory"
    if basename == ".env" or basename.endswith((".pem", ".key", ".crt")):
        return "sensitive file"
    if basename.endswith(".tsbuildinfo"):
        return "TypeScript build state"
    if re.search(r" 2\.[^/]+$", path):
        return "duplicate conflict copy"
    return None


def main() -> int:
    errors: list[str] = []
    readme = README.read_text(encoding="utf-8")
    lines = readme.splitlines()

    if not lines or lines[0] != "# 13110":
        errors.append("README must start with '# 13110'")
    if FINALIST_COPY not in lines[:3]:
        errors.append("finalist copy must appear within the first three README lines")
    if readme.count(FINALIST_COPY) != 1:
        errors.append("finalist copy must appear exactly once in README")
    if "全国一等奖" in readme:
        errors.append("README must not claim a national first prize")
    if "final.socialdog.cn" in readme:
        errors.append("README must not publish the production URL")

    for required in REQUIRED_PATHS:
        if not (ROOT / required).exists():
            errors.append(f"required repository path is missing: {required}")

    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in REQUIRED_MAKE_TARGETS:
        if not re.search(rf"^{re.escape(target)}(?:\s[^:]*)?:", makefile, flags=re.MULTILINE):
            errors.append(f"required Make target is missing: {target}")

    for markdown_name in CORE_MARKDOWN:
        markdown_path = ROOT / markdown_name
        if not markdown_path.exists():
            continue
        content = markdown_path.read_text(encoding="utf-8")
        for raw in MARKDOWN_LINK.findall(content):
            destination = relative_destination(raw)
            if destination is None:
                continue
            target = (markdown_path.parent / destination).resolve()
            if not target.exists():
                errors.append(f"broken relative link in {markdown_name}: {destination}")

    screenshot_paths: list[Path] = []
    for raw in MARKDOWN_IMAGE.findall(readme):
        destination = relative_destination(raw)
        if destination is not None:
            screenshot_paths.append((ROOT / destination).resolve())
    if len(screenshot_paths) != 2:
        errors.append(
            f"README must reference exactly two local screenshots, found {len(screenshot_paths)}"
        )
    for screenshot in screenshot_paths:
        if not screenshot.exists():
            continue
        try:
            actual_size = image_size(screenshot)
        except ValueError as exc:
            errors.append(f"cannot inspect screenshot {screenshot.relative_to(ROOT)}: {exc}")
            continue
        if actual_size != EXPECTED_SCREENSHOT_SIZE:
            errors.append(
                f"screenshot {screenshot.relative_to(ROOT)} is {actual_size}, "
                f"expected {EXPECTED_SCREENSHOT_SIZE}"
            )

    for tracked in tracked_files():
        if reason := forbidden_tracked_reason(tracked):
            errors.append(f"forbidden tracked {reason}: {tracked}")

    if errors:
        print("Repository checks failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Repository checks passed: brand, links, screenshots, structure, and tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
