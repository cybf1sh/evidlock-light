"""SHA-256, manifesty i weryfikacja."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def sha256_file(path: str | Path, chunk_size: int = 1024 * 1024 * 4, callback=None) -> str:
    target = Path(path)
    hasher = hashlib.sha256()
    total = max(1, target.stat().st_size)
    processed = 0
    with target.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
            processed += len(chunk)
            if callback:
                callback(processed, total)
    return hasher.hexdigest().upper()


def build_manifest(root: str | Path, callback=None) -> list[dict]:
    base = Path(root).resolve()
    files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
    manifest: list[dict] = []
    total = max(1, len(files))
    for index, file_path in enumerate(files, 1):
        manifest.append(
            {
                "path": str(file_path.relative_to(base) if base.is_dir() else file_path.name),
                "size": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }
        )
        if callback:
            callback(index, total, file_path)
    return manifest


def save_manifest(root: str | Path, output: str | Path, callback=None) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {"root": str(Path(root).resolve()), "files": build_manifest(root, callback=callback)}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def verify_manifest(manifest_path: str | Path, root: str | Path | None = None) -> dict:
    manifest_file = Path(manifest_path)
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    base = Path(root or data.get("root") or ".").resolve()
    result = {"ok": True, "checked": 0, "changed": [], "missing": []}
    for item in data.get("files", []):
        target = base / item["path"]
        if not target.exists():
            result["ok"] = False
            result["missing"].append(item["path"])
            continue
        result["checked"] += 1
        if sha256_file(target) != item["sha256"]:
            result["ok"] = False
            result["changed"].append(item["path"])
    return result
