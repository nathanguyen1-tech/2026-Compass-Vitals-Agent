"""Intake Tracker — Tracks clinical intake progress and completeness.

Manages phase progression, OLDCARTS field coverage, section completeness,
and supports pre-existing patient history data.
"""

from __future__ import annotations

import math
import re
from copy import deepcopy


# Valid intake phases in order
PHASES = [
    "greeting",
    "cc",
    "red_flag_screening",
    "hpi",
    "ros",
    "pmh",
    "medications",
    "allergies",
    "social_family",
    "summary",
    "complete",
]

# OLDCARTS fields
OLDCARTS_FIELDS = [
    "onset", "location", "duration", "character",
    "aggravating", "alleviating", "timing", "severity",
]

# Minimum OLDCARTS fields required for SOAP generation
MIN_OLDCARTS_FIELDS = 6

# Minimum ROS systems required
MIN_ROS_SYSTEMS = 2

# Sections that count toward completeness
REQUIRED_SECTIONS = [
    "cc", "hpi", "ros", "pmh", "medications", "allergies", "red_flag_screening",
]

# Marker regex: [INTAKE:field=value]
INTAKE_MARKER_PATTERN = re.compile(r"\[INTAKE:(\w+)=([^\]]+)\]")


class IntakeTracker:
    """Tracks completeness of clinical intake sections.

    Supports:
    - Phase tracking through clinical flow
    - OLDCARTS field coverage
    - Pre-existing patient history (marks sections complete on init)
    - Serialization to/from dict for session storage
    - Progress indicators for the patient
    """

    def __init__(
        self,
        data: dict | None = None,
        existing_history: dict | None = None,
    ):
        """Initialize tracker.

        Args:
            data: Serialized tracker state (from session). If provided, restores state.
            existing_history: Pre-existing patient data (PMH, meds, allergies, etc.)
                Keys can include: "pmh", "medications", "allergies", "social_family"
                If provided, marks those sections as pre-filled.
        """
        if data:
            self._load(data)
        else:
            self._init_fresh(existing_history)

    def _init_fresh(self, existing_history: dict | None = None) -> None:
        """Initialize a fresh tracker."""
        self.phase = "greeting"
        self.complaint_category: str | None = None
        self.message_count = 0

        # Chief complaint
        self.cc: str | None = None

        # HPI / OLDCARTS
        self.hpi: dict[str, str | None] = {f: None for f in OLDCARTS_FIELDS}
        self.hpi_additional: dict[str, str] = {}
        self.relevant_oldcarts: list[str] = list(OLDCARTS_FIELDS)

        # Red flag screening
        self.red_flags_checked: list[str] = []
        self.red_flags_found: list[str] = []
        self.red_flag_screening_done = False

        # Review of Systems
        self.ros_systems: dict[str, str] = {}  # system -> finding

        # PMH, Meds, Allergies, Social/Family
        self.pmh: str | None = None
        self.pmh_complete = False
        self.medications: str | None = None
        self.medications_complete = False
        self.allergies: str | None = None
        self.allergies_complete = False
        self.social_family: str | None = None
        self.social_family_complete = False

        # Pre-filled flags
        self.pmh_prefilled = False
        self.medications_prefilled = False
        self.allergies_prefilled = False
        self.social_family_prefilled = False

        # Summary
        self.summary_confirmed = False

        # LLM-detected emergency (Tier 3)
        self.emergency_detected_reason: str | None = None

        # Suspected emergency — 2-question confirmation flow
        # When set: {"reason": "...", "confirmation_questions_asked": 0, "source": "llm"}
        self.suspected_emergency: dict | None = None

        # Apply pre-existing history
        if existing_history:
            self._apply_existing_history(existing_history)

    def _apply_existing_history(self, history: dict) -> None:
        """Mark sections as complete if pre-existing data is available."""
        if history.get("pmh"):
            self.pmh = history["pmh"] if isinstance(history["pmh"], str) else str(history["pmh"])
            self.pmh_complete = True
            self.pmh_prefilled = True

        if history.get("medications"):
            self.medications = (
                history["medications"]
                if isinstance(history["medications"], str)
                else str(history["medications"])
            )
            self.medications_complete = True
            self.medications_prefilled = True

        if history.get("allergies"):
            self.allergies = (
                history["allergies"]
                if isinstance(history["allergies"], str)
                else str(history["allergies"])
            )
            self.allergies_complete = True
            self.allergies_prefilled = True

        if history.get("social_family") or history.get("social_history"):
            val = history.get("social_family") or history.get("social_history")
            self.social_family = val if isinstance(val, str) else str(val)
            self.social_family_complete = True
            self.social_family_prefilled = True

    def _load(self, data: dict) -> None:
        """Restore tracker state from a serialized dict."""
        self.phase = data.get("phase", "greeting")
        self.complaint_category = data.get("complaint_category")
        self.message_count = data.get("message_count", 0)

        self.cc = data.get("cc")

        self.hpi = {f: data.get("hpi", {}).get(f) for f in OLDCARTS_FIELDS}
        self.hpi_additional = data.get("hpi_additional", {})
        self.relevant_oldcarts = data.get("relevant_oldcarts", list(OLDCARTS_FIELDS))

        self.red_flags_checked = data.get("red_flags_checked", [])
        self.red_flags_found = data.get("red_flags_found", [])
        self.red_flag_screening_done = data.get("red_flag_screening_done", False)

        self.ros_systems = data.get("ros_systems", {})

        self.pmh = data.get("pmh")
        self.pmh_complete = data.get("pmh_complete", False)
        self.medications = data.get("medications")
        self.medications_complete = data.get("medications_complete", False)
        self.allergies = data.get("allergies")
        self.allergies_complete = data.get("allergies_complete", False)
        self.social_family = data.get("social_family")
        self.social_family_complete = data.get("social_family_complete", False)

        self.pmh_prefilled = data.get("pmh_prefilled", False)
        self.medications_prefilled = data.get("medications_prefilled", False)
        self.allergies_prefilled = data.get("allergies_prefilled", False)
        self.social_family_prefilled = data.get("social_family_prefilled", False)

        self.summary_confirmed = data.get("summary_confirmed", False)

        self.emergency_detected_reason = data.get("emergency_detected_reason")

        self.suspected_emergency = data.get("suspected_emergency")

    def to_dict(self) -> dict:
        """Serialize tracker state for session storage."""
        return {
            "phase": self.phase,
            "complaint_category": self.complaint_category,
            "message_count": self.message_count,
            "cc": self.cc,
            "hpi": dict(self.hpi),
            "hpi_additional": dict(self.hpi_additional),
            "relevant_oldcarts": list(self.relevant_oldcarts),
            "red_flags_checked": list(self.red_flags_checked),
            "red_flags_found": list(self.red_flags_found),
            "red_flag_screening_done": self.red_flag_screening_done,
            "ros_systems": dict(self.ros_systems),
            "pmh": self.pmh,
            "pmh_complete": self.pmh_complete,
            "medications": self.medications,
            "medications_complete": self.medications_complete,
            "allergies": self.allergies,
            "allergies_complete": self.allergies_complete,
            "social_family": self.social_family,
            "social_family_complete": self.social_family_complete,
            "pmh_prefilled": self.pmh_prefilled,
            "medications_prefilled": self.medications_prefilled,
            "allergies_prefilled": self.allergies_prefilled,
            "social_family_prefilled": self.social_family_prefilled,
            "summary_confirmed": self.summary_confirmed,
            "emergency_detected_reason": self.emergency_detected_reason,
            "suspected_emergency": self.suspected_emergency,
        }

    # === Field Updates ===

    def update_field(self, field: str, value: str) -> None:
        """Update a tracked field from an [INTAKE:field=value] marker.

        Handles routing to the correct internal field based on field name.
        """
        # Phase markers
        if field == "phase":
            if value in PHASES:
                self.phase = value
            return

        # Chief complaint
        if field == "cc":
            self.cc = value
            return

        # OLDCARTS fields
        if field in OLDCARTS_FIELDS:
            self.hpi[field] = value
            return

        # HPI additional (complaint-specific)
        if field.startswith("hpi_"):
            self.hpi_additional[field] = value
            return

        # Red flag check
        if field == "red_flag_check":
            parts = value.split(":")
            flag_id = parts[0]
            result = parts[1] if len(parts) > 1 else "checked"
            if flag_id not in self.red_flags_checked:
                self.red_flags_checked.append(flag_id)
            if result == "positive" and flag_id not in self.red_flags_found:
                self.red_flags_found.append(flag_id)
            return

        if field == "red_flag_screening_done":
            self.red_flag_screening_done = True
            return

        # ROS
        if field.startswith("ros_"):
            system = field[4:]  # e.g., "ros_constitutional" -> "constitutional"
            self.ros_systems[system] = value
            return

        # PMH
        if field == "pmh":
            self.pmh = value
            self.pmh_complete = True
            return

        # Medications
        if field == "medications":
            self.medications = value
            self.medications_complete = True
            return

        # Allergies
        if field == "allergies":
            self.allergies = value
            self.allergies_complete = True
            return

        # Social/Family
        if field in ("social_family", "social_history", "family_history"):
            self.social_family = value
            self.social_family_complete = True
            return

        # Summary confirmation
        if field == "summary_confirmed":
            self.summary_confirmed = True
            return

        # LLM-detected emergency (Tier 3) — backward compatible
        if field == "emergency_detected":
            self.emergency_detected_reason = value
            return

        # Emergency confirmation flow — 2-question protocol
        if field == "emergency_suspected":
            self.suspected_emergency = {
                "reason": value,
                "confirmation_questions_asked": 0,
                "source": "llm",
            }
            return

        if field == "emergency_confirmed":
            self.emergency_detected_reason = value
            return

        if field == "emergency_cleared":
            self.suspected_emergency = None
            return

    # === Complaint-Aware OLDCARTS ===

    def set_relevant_oldcarts(self, fields: list[str]) -> None:
        """Set which OLDCARTS fields are relevant for the current complaint.

        Only fields that are valid OLDCARTS names are kept.
        Falls back to all 8 if the resulting list is empty.
        """
        valid = [f for f in fields if f in OLDCARTS_FIELDS]
        self.relevant_oldcarts = valid if valid else list(OLDCARTS_FIELDS)

    def get_min_oldcarts_required(self) -> int:
        """Minimum OLDCARTS fields needed, scaled to relevant fields.

        Uses 75% of relevant fields with a floor of 3.
        """
        return max(3, math.ceil(len(self.relevant_oldcarts) * 0.75))

    # === Completeness Checks ===

    def get_hpi_coverage(self) -> tuple[int, int]:
        """Return (filled_fields, total_relevant_fields) for OLDCARTS."""
        filled = sum(1 for f in self.relevant_oldcarts if self.hpi.get(f) is not None)
        return filled, len(self.relevant_oldcarts)

    def get_missing_hpi_fields(self) -> list[str]:
        """Return list of relevant OLDCARTS fields not yet collected."""
        return [f for f in self.relevant_oldcarts if self.hpi.get(f) is None]

    def get_completed_sections(self) -> list[str]:
        """Return list of sections that are complete."""
        completed = []
        if self.cc:
            completed.append("cc")

        filled, total = self.get_hpi_coverage()
        if filled >= self.get_min_oldcarts_required():
            completed.append("hpi")

        if len(self.ros_systems) >= MIN_ROS_SYSTEMS:
            completed.append("ros")

        if self.pmh_complete:
            completed.append("pmh")

        if self.medications_complete:
            completed.append("medications")

        if self.allergies_complete:
            completed.append("allergies")

        if self.red_flag_screening_done or len(self.red_flags_checked) > 0:
            completed.append("red_flag_screening")

        if self.social_family_complete:
            completed.append("social_family")

        return completed

    def get_missing_sections(self) -> list[str]:
        """Return list of required sections still incomplete."""
        completed = set(self.get_completed_sections())
        return [s for s in REQUIRED_SECTIONS if s not in completed]

    def get_completeness_score(self) -> float:
        """Return 0.0-1.0 score of how complete the intake is.

        Weights:
        - CC: 10%
        - Red flag screening: 10%
        - HPI: 30% (proportional to OLDCARTS coverage)
        - ROS: 15%
        - PMH: 10%
        - Medications: 10%
        - Allergies: 10%
        - Social/Family: 5%
        """
        score = 0.0

        # CC (10%)
        if self.cc:
            score += 0.10

        # Red flag screening (10%)
        if self.red_flag_screening_done or len(self.red_flags_checked) > 0:
            score += 0.10

        # HPI (30%)
        filled, total = self.get_hpi_coverage()
        if total > 0:
            score += 0.30 * (filled / total)

        # ROS (15%)
        ros_count = len(self.ros_systems)
        if ros_count >= MIN_ROS_SYSTEMS:
            score += 0.15
        elif ros_count > 0:
            score += 0.15 * (ros_count / MIN_ROS_SYSTEMS)

        # PMH (10%)
        if self.pmh_complete:
            score += 0.10

        # Medications (10%)
        if self.medications_complete:
            score += 0.10

        # Allergies (10%)
        if self.allergies_complete:
            score += 0.10

        # Social/Family (5%)
        if self.social_family_complete:
            score += 0.05

        return round(score, 2)

    def is_minimum_complete(self) -> bool:
        """Check if minimum data for SOAP generation is met.

        Requires: CC, 6/8 OLDCARTS, 2+ ROS systems, PMH, meds, allergies, red flags screened.
        """
        missing = self.get_missing_sections()
        return len(missing) == 0

    # === Progress ===

    def get_progress_description(self, language: str = "vi") -> str:
        """Return a human-readable progress indicator."""
        score = self.get_completeness_score()

        if language == "vi":
            if score < 0.25:
                return "Chung ta moi bat dau."
            elif score < 0.50:
                return "Chung ta da di duoc khoang mot phan tu."
            elif score < 0.75:
                return "Chung ta da di duoc khoang nua chang duong."
            elif score < 0.90:
                return "Chung ta sap hoan thanh."
            else:
                return "Chung ta gan xong roi."
        else:
            if score < 0.25:
                return "We're just getting started."
            elif score < 0.50:
                return "We're about a quarter of the way through."
            elif score < 0.75:
                return "We're about halfway through."
            elif score < 0.90:
                return "We're almost done."
            else:
                return "We're nearly finished."

    def suggest_next_phase(self) -> str:
        """Based on current completeness, suggest what phase should come next."""
        if not self.cc:
            return "cc"

        if not self.red_flag_screening_done and len(self.red_flags_checked) == 0:
            return "red_flag_screening"

        filled, _ = self.get_hpi_coverage()
        if filled < self.get_min_oldcarts_required():
            return "hpi"

        if len(self.ros_systems) < MIN_ROS_SYSTEMS:
            return "ros"

        if not self.pmh_complete:
            return "pmh"

        if not self.medications_complete:
            return "medications"

        if not self.allergies_complete:
            return "allergies"

        if not self.social_family_complete:
            return "social_family"

        if not self.summary_confirmed:
            return "summary"

        return "complete"

    def get_prefilled_sections(self) -> list[str]:
        """Return list of sections that were pre-filled from patient history."""
        prefilled = []
        if self.pmh_prefilled:
            prefilled.append("pmh")
        if self.medications_prefilled:
            prefilled.append("medications")
        if self.allergies_prefilled:
            prefilled.append("allergies")
        if self.social_family_prefilled:
            prefilled.append("social_family")
        return prefilled

    # === Intake Data Export ===

    def to_intake_data(self) -> dict:
        """Export tracker data as intake_data dict for downstream agents.

        Compatible with the format expected by screening_agent._build_intake_summary().
        """
        data: dict = {}

        if self.cc:
            data["chief_complaint"] = self.cc

        if self.complaint_category:
            data["complaint_category"] = self.complaint_category

        # OLDCARTS
        for field, value in self.hpi.items():
            if value is not None:
                data[field] = value

        # Additional HPI
        for field, value in self.hpi_additional.items():
            data[field] = value

        # ROS
        if self.ros_systems:
            data["ros"] = dict(self.ros_systems)

        # PMH
        if self.pmh:
            data["pmh"] = self.pmh

        # Medications
        if self.medications:
            data["medications"] = self.medications

        # Allergies
        if self.allergies:
            data["allergies"] = self.allergies

        # Social/Family
        if self.social_family:
            data["social_family"] = self.social_family

        # Red flags
        if self.red_flags_found:
            data["red_flags_found"] = list(self.red_flags_found)

        return data


# === Marker Parsing ===


def parse_intake_markers(text: str) -> tuple[str, dict[str, str]]:
    """Parse [INTAKE:field=value] markers from LLM response text.

    Returns:
        (clean_text, extracted_fields) — text with markers removed,
        and dict of field->value pairs extracted.
    """
    extracted: dict[str, str] = {}

    for match in INTAKE_MARKER_PATTERN.finditer(text):
        field = match.group(1)
        value = match.group(2).strip()
        extracted[field] = value

    # Remove all markers from text
    clean_text = INTAKE_MARKER_PATTERN.sub("", text).strip()
    # Clean up any double spaces or leading/trailing whitespace from removal
    clean_text = re.sub(r"  +", " ", clean_text)
    clean_text = re.sub(r"\n\n\n+", "\n\n", clean_text)

    return clean_text, extracted
