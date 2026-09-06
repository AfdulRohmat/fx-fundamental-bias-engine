"""Small deterministic helpers for immutable research run bundles."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            allow_nan=False,
            default=lambda item: item.isoformat()
            if isinstance(item, (date, datetime))
            else str(item),
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, values: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(value, sort_keys=True, allow_nan=False)
        for value in values
    ]
    path.write_text(
        "" if not lines else "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_manifest(directory: Path, *, phase: str) -> dict[str, Any]:
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files.append(
                {
                    "path": path.relative_to(directory).as_posix(),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_path(path),
                }
            )
    result = {"phase": phase, "files": files, "file_count": len(files)}
    write_json(directory / "manifest.json", result)
    return result
