"""CareFlowState — Shared state cho toàn bộ care flow.

Đây là data contract duy nhất giữa tất cả agents.
Mọi agent đọc từ state và ghi kết quả vào state.
"""

from typing import Literal, Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class CareFlowState(TypedDict):
    """Shared state cho toàn bộ care flow. Tất cả agents đọc/ghi vào đây."""

    # === Patient Context ===
    patient_id: str
    case_id: str
    organization_id: str

    # === Conversation ===
    messages: Annotated[list[BaseMessage], add_messages]

    # === Intake Data (Intake Agent ghi) ===
    intake_data: dict | None
    intake_complete: bool

    # === Screening Results (Screening Agent ghi) ===
    screening_result: dict | None
    severity: Literal["emergency", "urgent", "routine"] | None
    differential_diagnoses: list[dict]
    is_emergency: bool

    # === Order Recommendations (Proposer Agent ghi) ===
    order_recommendations: list[dict]
    drug_interactions: list[dict]
    allergy_alerts: list[dict]

    # === Critic Validation (Critic Agent ghi) ===
    critic_validation: dict | None
    critic_approved: bool
    critic_issues: list[dict]

    # === Confidence Scoring ===
    confidence_score: float | None
    confidence_breakdown: dict | None

    # === Flow Control ===
    current_station: int
    flow_type: Literal["emergency", "prescription", "lab", "monitoring"] | None
    needs_human_review: bool
    human_review_reason: str | None

    # === NLP Context ===
    detected_language: str
    cultural_expressions: list[dict]

    # === Metadata ===
    created_at: str
    updated_at: str
    correlation_id: str
