from __future__ import annotations

import asyncio
import os
import uuid
from collections import defaultdict

from openai import AsyncOpenAI

from app.memory import RulesMemory
from app.models import BatchDecision, EmailItem, Rule


class InboxAgent:
    def __init__(self, memory: RulesMemory) -> None:
        self.memory = memory
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    async def group_emails(self, emails: list[EmailItem]) -> dict[str, list[EmailItem]]:
        grouped: dict[str, list[EmailItem]] = defaultdict(list)
        for e in emails:
            grouped[f"domain:{e.sender_domain}"].append(e)
        return grouped

    async def decide_batch(self, key: str, emails: list[EmailItem]) -> BatchDecision:
        for r in self.memory.rules:
            if r.scope == "domain" and key == f"domain:{r.pattern}":
                return BatchDecision(key, [e.id for e in emails], [e.subject for e in emails], r.action, r.confidence, "Matched memorized rule")

        prompt = {
            "group": key,
            "count": len(emails),
            "sample_subjects": [e.subject for e in emails[:10]],
            "known_rules": [rule.__dict__ for rule in self.memory.rules],
            "task": "Choose one action: archive/trash/keep/ask, and confidence 0-1 with short reason",
        }
        result = await self.client.responses.create(
            model="gpt-4o-mini",
            input=[{"role": "user", "content": str(prompt)}],
            temperature=0,
        )
        text = result.output_text.lower()
        action = "ask"
        for candidate in ["archive", "trash", "keep", "ask"]:
            if candidate in text:
                action = candidate
                break
        confidence = 0.55 if action == "ask" else 0.75
        return BatchDecision(key, [e.id for e in emails], [e.subject for e in emails], action, confidence, text[:180])

    def learn_from_user(self, group_key: str, action: str, rationale: str = "User provided guidance") -> Rule:
        _, pattern = group_key.split(":", 1)
        rule = Rule(
            rule_id=str(uuid.uuid4()),
            scope="domain",
            pattern=pattern,
            action=action,
            confidence=0.98,
            rationale=rationale,
        )
        self.memory.add_rule(rule)
        return rule

    async def process(self, emails: list[EmailItem]) -> list[BatchDecision]:
        grouped = await self.group_emails(emails)
        tasks = [self.decide_batch(key, group) for key, group in grouped.items()]
        return await asyncio.gather(*tasks)
