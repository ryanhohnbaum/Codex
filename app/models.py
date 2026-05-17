from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ActionType = Literal["archive", "trash", "keep", "ask"]


@dataclass
class EmailItem:
    id: str
    thread_id: str
    subject: str
    sender: str
    sender_domain: str
    snippet: str
    internal_date: datetime


@dataclass
class Rule:
    rule_id: str
    scope: Literal["domain", "sender", "keyword", "thread", "category"]
    pattern: str
    action: ActionType
    confidence: float = 0.9
    rationale: str = ""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class BatchDecision:
    group_key: str
    email_ids: list[str]
    subjects: list[str]
    action: ActionType
    confidence: float
    reason: str
