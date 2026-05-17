from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.models import Rule


class RulesMemory:
    def __init__(self, path: str = "rules_memory.json") -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = {"rules": [], "history": []}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    @property
    def rules(self) -> list[Rule]:
        return [Rule(**r) for r in self._data.get("rules", [])]

    def add_rule(self, rule: Rule) -> None:
        self._data.setdefault("rules", []).append(rule.__dict__)
        self.save()

    def add_history(self, event: dict[str, Any]) -> None:
        self._data.setdefault("history", []).append(event)
        self.save()

    def has_rules(self) -> bool:
        return len(self._data.get("rules", [])) > 0
