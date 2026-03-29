#!/usr/bin/env python3
"""Discover update targets for GitHub Actions."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from lib import write_output

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class MatrixItem:
    """Single package or flake-input update target."""

    type: str
    name: str
    current_version: str

    def to_dict(self) -> dict[str, str]:
        return {
            "type": self.type,
            "name": self.name,
            "current_version": self.current_version,
        }


def discover_packages(packages_filter: list[str] | None) -> list[MatrixItem]:
    """Return the single packaged repo package if requested."""
    packages = ["bws"]
    selected = packages if packages_filter is None else packages_filter
    items: list[MatrixItem] = []

    for name in selected:
        if name != "bws":
            log.warning("Skipping unknown package %s", name)
            continue

        version = "2.0.0"
        package_file = Path("pkgs") / name / "package.nix"
        for line in package_file.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("version = "):
                version = stripped.split('"')[1]
                break

        items.append(MatrixItem(type="package", name=name, current_version=version))

    return items


def discover_flake_inputs(inputs_filter: list[str] | None) -> list[MatrixItem]:
    """Discover flake inputs from flake.lock."""
    lock = json.loads(Path("flake.lock").read_text())
    nodes: dict[str, dict[str, object]] = lock.get("nodes", {})
    names = inputs_filter or sorted(k for k in nodes if k != "root")

    items: list[MatrixItem] = []
    for name in names:
        node = nodes.get(name)
        if node is None:
            log.warning("Skipping unknown input %s", name)
            continue
        locked = node.get("locked")
        rev = (
            locked.get("rev", "unknown")[:8] if isinstance(locked, dict) else "unknown"
        )
        items.append(MatrixItem(type="flake-input", name=name, current_version=rev))

    return items


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    packages_env = os.environ.get("PACKAGES", "")
    inputs_env = os.environ.get("INPUTS", "")

    matrix_items = [
        *discover_packages(packages_env.split() or None),
        *discover_flake_inputs(inputs_env.split() or None),
    ]

    matrix = {"include": [item.to_dict() for item in matrix_items]}
    write_output("matrix", json.dumps(matrix, separators=(",", ":")))
    write_output("has-updates", str(bool(matrix_items)).lower())


if __name__ == "__main__":
    main()
