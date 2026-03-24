"""Auto Test Store — lưu kết quả test vào PostgreSQL."""

from __future__ import annotations

import structlog
from sqlalchemy import delete, desc, select

from app.db.engine import AsyncSessionLocal
from app.domain.models.auto_test_run import AutoTestRun as AutoTestRunModel

logger = structlog.get_logger()


async def save_run(
    test_run_id: str,
    total_cases: int,
    summary: dict,
    results: list[dict],
    name: str = "",
) -> None:
    """Lưu hoặc cập nhật test run vào DB."""
    async with AsyncSessionLocal() as db:
        # Upsert: xóa cũ nếu có, tạo mới
        existing = await db.execute(
            select(AutoTestRunModel).where(AutoTestRunModel.test_run_id == test_run_id)
        )
        row = existing.scalar_one_or_none()
        if row:
            row.total_cases = total_cases
            row.summary = summary
            row.results = results
            row.name = name
        else:
            row = AutoTestRunModel(
                test_run_id=test_run_id,
                name=name,
                total_cases=total_cases,
                summary=summary,
                results=results,
            )
            db.add(row)
        await db.commit()
    logger.info("auto_test.saved", run_id=test_run_id, name=name, cases=total_cases)


async def list_runs() -> list[dict]:
    """Danh sách test runs (không kèm results chi tiết)."""
    async with AsyncSessionLocal() as db:
        stmt = select(AutoTestRunModel).order_by(desc(AutoTestRunModel.created_at)).limit(100)
        result = await db.execute(stmt)
        rows = result.scalars().all()
    return [
        {
            "test_run_id": r.test_run_id,
            "name": r.name or "",
            "timestamp": r.created_at.isoformat() if r.created_at else "",
            "total_cases": r.total_cases,
            "summary": r.summary or {},
            "case_count": len(r.results) if r.results else 0,
        }
        for r in rows
    ]


async def get_run(run_id: str) -> dict | None:
    """Chi tiết 1 test run (kèm results + conversation)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(AutoTestRunModel).where(AutoTestRunModel.test_run_id == run_id)
        )
        row = result.scalar_one_or_none()
    if not row:
        return None
    return {
        "test_run_id": row.test_run_id,
        "name": row.name or "",
        "timestamp": row.created_at.isoformat() if row.created_at else "",
        "total_cases": row.total_cases,
        "summary": row.summary or {},
        "results": row.results or [],
    }


async def delete_run(run_id: str) -> bool:
    """Xóa 1 test run."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            delete(AutoTestRunModel).where(AutoTestRunModel.test_run_id == run_id)
        )
        await db.commit()
    return result.rowcount > 0
