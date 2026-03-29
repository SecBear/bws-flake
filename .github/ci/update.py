#!/usr/bin/env python3
"""Perform package or flake-input updates."""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path

from lib import UpdateType, nix_eval_raw, run, write_output

log = logging.getLogger(__name__)


def git_has_changes() -> bool:
    """Check if the working tree has uncommitted changes."""
    return run(["git", "diff", "--quiet"], check=False).returncode != 0


def sync_readme_version(new_version: str) -> None:
    """Keep the README package version in sync with package.nix."""
    readme = Path("README.md")
    updated = re.sub(
        r"Current packaged version: `[^`]+`",
        f"Current packaged version: `{new_version}`",
        readme.read_text(),
    )
    readme.write_text(updated)


def update_package(name: str) -> None:
    """Update the single packaged repo package with nix-update."""
    if name != "bws":
        log.error("::error::Unknown package %s", name)
        sys.exit(1)

    log.info("Updating package %s...", name)
    run(["nix-update", "--flake", name])

    new_version = nix_eval_raw(".#bws.version") or "unknown"
    sync_readme_version(new_version)

    if not git_has_changes():
        log.info("No changes detected")
        write_output("updated", "false")
        return

    changelog = nix_eval_raw(".#bws.meta.changelog") or ""
    write_output("updated", "true")
    write_output("new_version", new_version)
    write_output("changelog", changelog)


def update_flake_input(name: str) -> None:
    """Update a single flake input."""
    run(["nix", "flake", "update", name])

    if not git_has_changes():
        log.info("No changes detected")
        write_output("updated", "false")
        return

    metadata = json.loads(
        run(["nix", "flake", "metadata", "--json", "--no-write-lock-file"], capture=True).stdout
    )
    rev = (
        metadata.get("locks", {})
        .get("nodes", {})
        .get(name, {})
        .get("locked", {})
        .get("rev", "unknown")
    )
    write_output("updated", "true")
    write_output("new_version", rev[:8])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("type", choices=[t.value for t in UpdateType])
    parser.add_argument("name")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = parse_args()

    match UpdateType(args.type):
        case UpdateType.PACKAGE:
            update_package(args.name)
        case UpdateType.FLAKE_INPUT:
            update_flake_input(args.name)


if __name__ == "__main__":
    main()
