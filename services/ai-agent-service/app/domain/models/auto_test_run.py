"""Auto Test Run — lưu kết quả mỗi lần chạy auto test."""

from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.models.base import Base, TimestampMixin, generate_ulid


class AutoTestRun(Base, TimestampMixin):
    __tablename__ = "auto_test_runs"

    id: Mapped[str] = mapped_column(String(26), primary_key=True, default=generate_ulid)
    test_run_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[list] = mapped_column(JSON, default=list)  # list of case results with conversation
