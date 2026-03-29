#!/usr/bin/env python3
"""Create or update a PR for automated package or flake-input updates."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass

from lib import UpdateType, run

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class PrConfig:
    """All data needed to create or update a PR."""

    branch: str
    title: str
    body: str
    commit_message: str


def gh_get_pr_number(branch: str) -> str | None:
    """Return the PR number for an existing branch PR."""
    result = run(
        [
            "gh",
            "pr",
            "list",
            "--head",
            branch,
            "--json",
            "number",
            "--jq",
            ".[0].number // empty",
        ],
        capture=True,
    )
    return result.stdout.strip() or None


def build_config(
    *,
    update_type: UpdateType,
    name: str,
    current_version: str,
    new_version: str,
    changelog_url: str,
) -> PrConfig:
    """Build PR metadata from update parameters."""
    match update_type:
        case UpdateType.PACKAGE:
            title = f"{name}: {current_version} -> {new_version}"
            body = f"Automated update of `{name}` from `{current_version}` to `{new_version}`."
            commit_message = f"{title}\n\n{changelog_url}" if changelog_url else title
            branch = f"update/{name}"
        case UpdateType.FLAKE_INPUT:
            title = f"flake.lock: update {name}"
            body = f"Automated update of flake input `{name}` from `{current_version}` to `{new_version}`."
            commit_message = f"{title}\n\n{current_version} -> {new_version}"
            branch = f"update/{name}"

    return PrConfig(
        branch=branch,
        title=title,
        body=body,
        commit_message=commit_message,
    )


def create_or_update_pr(config: PrConfig, *, labels: str, auto_merge: bool) -> None:
    """Commit current changes, push a branch, and create or update its PR."""
    run(["git", "add", "."])
    run(["git", "checkout", "-B", config.branch])
    run(["git", "commit", "-m", config.commit_message, "--signoff"])
    run(["git", "push", "--force", "origin", config.branch])

    pr_number = gh_get_pr_number(config.branch)
    if pr_number:
        run(["gh", "pr", "edit", pr_number, "--title", config.title, "--body", config.body])
    else:
        label_args: list[str] = [
            arg
            for raw in labels.split(",")
            if (label := raw.strip())
            for arg in ("--label", label)
        ]
        run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                config.title,
                "--body",
                config.body,
                "--base",
                "main",
                "--head",
                config.branch,
                *label_args,
            ]
        )
        pr_number = gh_get_pr_number(config.branch)

    if auto_merge and pr_number:
        run(["gh", "pr", "merge", pr_number, "--auto", "--squash"], check=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("type", choices=[t.value for t in UpdateType])
    parser.add_argument("name")
    parser.add_argument("current_version")
    parser.add_argument("new_version")
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not os.environ.get("GH_TOKEN"):
        log.error("GH_TOKEN environment variable is not set")
        sys.exit(1)

    args = parse_args()
    config = build_config(
        update_type=UpdateType(args.type),
        name=args.name,
        current_version=args.current_version,
        new_version=args.new_version,
        changelog_url=os.environ.get("CHANGELOG_URL", ""),
    )
    create_or_update_pr(
        config,
        labels=os.environ.get("PR_LABELS", "dependencies,automated"),
        auto_merge=os.environ.get("AUTO_MERGE", "false") == "true",
    )


if __name__ == "__main__":
    main()
