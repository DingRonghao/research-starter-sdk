"""Metadata-only before/after audit for the local iCloud Drive tree."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def snapshot(root: Path) -> dict[str, Any]:
    root = root.resolve(strict=True)
    entries: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as children:
                for child in children:
                    path = Path(child.path)
                    relative = path.relative_to(root).as_posix()
                    try:
                        stat = child.stat(follow_symlinks=False)
                        is_dir = child.is_dir(follow_symlinks=False)
                        entries[relative] = {
                            "type": "directory" if is_dir else "file",
                            "size": None if is_dir else stat.st_size,
                            "mtime_ns": stat.st_mtime_ns,
                            "attributes": getattr(stat, "st_file_attributes", None),
                        }
                        if is_dir:
                            pending.append(path)
                    except OSError as exc:
                        errors.append({"path": relative, "error": f"{type(exc).__name__}: {exc}"})
        except OSError as exc:
            errors.append(
                {"path": directory.relative_to(root).as_posix(), "error": f"{type(exc).__name__}: {exc}"}
            )
    return {
        "root": str(root),
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "entries": dict(sorted(entries.items())),
        "errors": errors,
    }


def compare(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    old = before["entries"]
    new = after["entries"]
    return {
        "root": after["root"],
        "before_created_at": before["created_at"],
        "after_created_at": after["created_at"],
        "added": {key: new[key] for key in sorted(new.keys() - old.keys())},
        "removed": {key: old[key] for key in sorted(old.keys() - new.keys())},
        "changed": {
            key: {"before": old[key], "after": new[key]}
            for key in sorted(old.keys() & new.keys())
            if old[key] != new[key]
        },
        "before_errors": before.get("errors", []),
        "after_errors": after.get("errors", []),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--before", type=Path)
    args = parser.parse_args()
    current = snapshot(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.before:
        prior = json.loads(args.before.read_text(encoding="utf-8"))
        payload = compare(prior, current)
    else:
        payload = current
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "output": str(args.output.resolve()),
        "entries": len(current["entries"]),
        "errors": len(current["errors"]),
    }
    if args.before:
        summary.update({name: len(payload[name]) for name in ("added", "removed", "changed")})
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
