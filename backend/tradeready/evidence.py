from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import EvidenceItem


DATA_PATH = Path(__file__).parent / "data" / "evidence.json"


@lru_cache(maxsize=1)
def load_evidence() -> list[EvidenceItem]:
    raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return [EvidenceItem.model_validate(item) for item in raw]


def evidence_by_id(ids: set[str] | list[str]) -> list[EvidenceItem]:
    wanted = set(ids)
    return [item for item in load_evidence() if item.id in wanted]


def find_category_classification(category: str) -> EvidenceItem | None:
    for item in load_evidence():
        if item.rule_type == "classification" and item.data.get("category") == category:
            return item
    return None


def find_rule(jurisdiction: str, rule_type: str, tag: str | None = None) -> EvidenceItem | None:
    for item in load_evidence():
        if item.jurisdiction != jurisdiction or item.rule_type != rule_type:
            continue
        if tag and tag not in item.tags:
            continue
        return item
    return None


def find_rules(jurisdiction: str, rule_type: str) -> list[EvidenceItem]:
    return [
        item
        for item in load_evidence()
        if item.jurisdiction == jurisdiction and item.rule_type == rule_type
    ]
