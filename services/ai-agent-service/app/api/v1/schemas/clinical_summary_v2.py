"""Clinical Summary v2 schemas — LLM-generated clinical narrative sections."""

from pydantic import BaseModel


class ClinicalNarrativeSection(BaseModel):
    """A bilingual clinical narrative section (English + Vietnamese)."""

    content: str
    content_vi: str = ""


class ClinicalSummaryV2Response(BaseModel):
    """LLM-generated Clinical Summary with HPI, CC, ROS narratives.

    Unlike ClinicalSummaryResponse (v1, pure Python extraction),
    this uses GPT-4 to synthesize clinical data into detailed narratives.
    """

    case_id: str
    session_id: str
    generated_at: str

    # Three main clinical narrative sections
    hpi: ClinicalNarrativeSection
    chief_complaint: ClinicalNarrativeSection
    ros: ClinicalNarrativeSection

    # Metadata
    severity: str = ""
    primary_diagnosis: str = ""
    is_emergency: bool = False
    needs_human_review: bool = False
    human_review_reason: str | None = None
    red_flags: list[str] = []
    data_quality_notes: list[str] = []
    detected_language: str = "vi"
