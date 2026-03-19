"""Differential Tracker — Running clinical differential for V3 intake agent.

Tracks hypotheses and determines the highest-yield next question
based on what would most change the differential.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


AnswerQuality = Literal["sufficient", "partial", "vague", "skipped", "declined", "redirected"]


@dataclass
class Hypothesis:
    """A single differential diagnosis hypothesis."""
    name: str
    name_vi: str
    probability: float          # 0.0 – 1.0
    missing_keys: list[str]     # fields that would clarify this dx
    red_flag: bool = False      # True if this dx is life-threatening


@dataclass
class FieldStatus:
    """Tracks answer quality and retry count for a single clinical field."""
    quality: AnswerQuality = "skipped"
    skip_count: int = 0
    value: str | None = None


class DifferentialTracker:
    """Maintains a live clinical differential and field status across turns.

    Core V3 innovation: questions are chosen based on diagnostic yield
    (which field would most change the differential), not fixed OLDCARTS order.
    """

    def __init__(self, data: dict | None = None):
        if data:
            self._load(data)
        else:
            self._init_fresh()

    def _init_fresh(self) -> None:
        self.hypotheses: list[Hypothesis] = []
        self.field_statuses: dict[str, FieldStatus] = {}
        self.next_target: str | None = None
        self.emergency_score: int = 0
        self.emergency_reasoning: str = ""
        self.skip_counts: dict[str, int] = {}
        self.turn_count: int = 0
        self.complaint_category: str | None = None

    def _load(self, data: dict) -> None:
        self.hypotheses = [
            Hypothesis(**h) for h in data.get("hypotheses", [])
        ]
        self.field_statuses = {
            k: FieldStatus(**v)
            for k, v in data.get("field_statuses", {}).items()
        }
        self.next_target = data.get("next_target")
        self.emergency_score = data.get("emergency_score", 0)
        self.emergency_reasoning = data.get("emergency_reasoning", "")
        self.skip_counts = data.get("skip_counts", {})
        self.turn_count = data.get("turn_count", 0)
        self.complaint_category = data.get("complaint_category")

    def to_dict(self) -> dict:
        return {
            "hypotheses": [
                {
                    "name": h.name,
                    "name_vi": h.name_vi,
                    "probability": h.probability,
                    "missing_keys": h.missing_keys,
                    "red_flag": h.red_flag,
                }
                for h in self.hypotheses
            ],
            "field_statuses": {
                k: {
                    "quality": v.quality,
                    "skip_count": v.skip_count,
                    "value": v.value,
                }
                for k, v in self.field_statuses.items()
            },
            "next_target": self.next_target,
            "emergency_score": self.emergency_score,
            "emergency_reasoning": self.emergency_reasoning,
            "skip_counts": self.skip_counts,
            "turn_count": self.turn_count,
            "complaint_category": self.complaint_category,
        }

    def update_from_reasoner(self, reasoner_output: dict) -> None:
        """Merge structured JSON from Clinical Reasoner into tracker state."""
        self.turn_count += 1

        # Update hypotheses
        raw_hypotheses = reasoner_output.get("running_differential", [])
        self.hypotheses = [
            Hypothesis(
                name=h.get("dx", h.get("name", "Unknown")),
                name_vi=h.get("dx_vi", h.get("name_vi", "")),
                probability=h.get("probability", 0.0),
                missing_keys=h.get("missing_keys", []),
                red_flag=h.get("red_flag", False),
            )
            for h in raw_hypotheses
        ]

        # Update field statuses from answer_quality
        for field, quality in reasoner_output.get("answer_quality", {}).items():
            if field not in self.field_statuses:
                self.field_statuses[field] = FieldStatus()
            status = self.field_statuses[field]
            status.quality = quality
            if quality in ("skipped", "redirected"):
                status.skip_count += 1
            elif quality == "sufficient":
                status.skip_count = 0  # reset on success

        # Update known facts
        for field, value in reasoner_output.get("known_facts", {}).items():
            if value and field not in self.field_statuses:
                self.field_statuses[field] = FieldStatus()
            if value and field in self.field_statuses:
                self.field_statuses[field].value = value
                if self.field_statuses[field].quality == "skipped":
                    self.field_statuses[field].quality = "sufficient"

        # Emergency
        self.emergency_score = reasoner_output.get("emergency_score", self.emergency_score)
        self.emergency_reasoning = reasoner_output.get("emergency_reasoning", "")

        # Next target
        self.next_target = reasoner_output.get("next_question_target")

        # Complaint category
        cat = reasoner_output.get("complaint_category")
        if cat:
            self.complaint_category = cat

    def get_skip_count(self, field: str) -> int:
        """How many times has patient skipped/redirected this field."""
        return self.field_statuses.get(field, FieldStatus()).skip_count

    def is_field_sufficient(self, field: str) -> bool:
        status = self.field_statuses.get(field)
        return status is not None and status.quality == "sufficient"

    def get_unanswered_required_fields(self, required: list[str]) -> list[str]:
        """Return required fields that are not yet 'sufficient'."""
        return [
            f for f in required
            if not self.is_field_sufficient(f)
            and self.field_statuses.get(f, FieldStatus()).quality != "declined"
        ]

    def has_emergency(self) -> bool:
        return self.emergency_score >= 7

    def summary_for_reasoner(self) -> str:
        """Compact clinical state summary to inject into Reasoner prompt."""
        lines = [f"Turn: {self.turn_count}"]
        if self.complaint_category:
            lines.append(f"Complaint category: {self.complaint_category}")

        if self.hypotheses:
            lines.append("Running differential:")
            for h in sorted(self.hypotheses, key=lambda x: -x.probability):
                prob_pct = int(h.probability * 100)
                flag = " ⚠️RED FLAG" if h.red_flag else ""
                lines.append(f"  - {h.name} ({prob_pct}%){flag} | missing: {h.missing_keys}")

        if self.field_statuses:
            lines.append("Field status:")
            for field, status in self.field_statuses.items():
                skip_note = f" [skipped x{status.skip_count}]" if status.skip_count > 0 else ""
                val_note = f": {status.value}" if status.value else ""
                lines.append(f"  - {field} [{status.quality}]{val_note}{skip_note}")

        if self.next_target:
            lines.append(f"Last decided next target: {self.next_target}")

        return "\n".join(lines)
