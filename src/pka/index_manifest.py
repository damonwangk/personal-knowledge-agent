from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST_VERSION = 2


@dataclass(frozen=True)
class SourceRecord:
    source_key: str
    source_hash: str
    chunk_ids: list[str]


class IndexManifest:
    def __init__(self, index_dir: Path) -> None:
        self.path = index_dir / "manifest.json"
        self.data = self._load()

    def unchanged(self, source_key: str, source_hash: str) -> bool:
        if self.data.get("version") != MANIFEST_VERSION:
            return False
        source = self.data.get("sources", {}).get(source_key)
        return bool(source and source.get("hash") == source_hash)

    def old_chunk_ids(self, source_key: str) -> list[str]:
        source = self.data.get("sources", {}).get(source_key, {})
        return list(source.get("chunk_ids", []))

    def update_source(self, record: SourceRecord) -> None:
        self.data.setdefault("sources", {})[record.source_key] = {
            "hash": record.source_hash,
            "chunk_ids": record.chunk_ids,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

    def save(self) -> None:
        self.data["version"] = MANIFEST_VERSION
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": MANIFEST_VERSION, "sources": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))
