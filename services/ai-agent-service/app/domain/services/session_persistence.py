"""Shared session persistence helpers.

persist_session() — fire-and-forget DB write (swallows all exceptions).
load_session()    — memory-first, DB fallback, re-hydrates _sessions_v2.
"""

import structlog

from app.db.engine import AsyncSessionLocal
from app.domain.repositories.agent_session_repository import AgentSessionRepository

logger = structlog.get_logger()


async def persist_session(session_id: str, session: dict) -> None:
    """Write session to PostgreSQL. Never raises — DB failure must not break chat."""
    try:
        async with AsyncSessionLocal() as db:
            repo = AgentSessionRepository(db)
            existing = await repo.get(session_id)
            if existing is None:
                await repo.create(session_id, session)
            else:
                await repo.update(session_id, session)
        logger.debug("db.session_persisted", session_id=session_id)
    except Exception as e:
        logger.warning("db.persist_failed", session_id=session_id, error=str(e))


async def load_session(session_id: str) -> dict | None:
    """Load session: check in-memory first, then fall back to DB.

    If loaded from DB, re-hydrates _sessions_v2 so subsequent requests are fast.
    Returns None if not found anywhere.
    """
    # Late imports to avoid circular dependency with route modules
    from app.api.v1.routes import chat_v2 as _chat_v2_module
    from app.api.v1.routes.chat import _sessions as _sessions_v1

    # 1. Check in-memory (fast path)
    session = _sessions_v1.get(session_id) or _chat_v2_module._sessions_v2.get(session_id)
    if session is not None:
        return session

    # 2. Fall back to DB
    try:
        async with AsyncSessionLocal() as db:
            repo = AgentSessionRepository(db)
            row = await repo.get(session_id)

        if row is None:
            return None

        # 3. Reconstruct session dict from DB row
        session = dict(row.state_snapshot or {})
        session["messages"] = AgentSessionRepository.deserialize_messages(row.messages or [])

        # 4. Re-hydrate in-memory cache for future requests
        _chat_v2_module._sessions_v2[session_id] = session
        logger.info("db.session_restored", session_id=session_id)
        return session

    except Exception as e:
        logger.warning("db.load_failed", session_id=session_id, error=str(e))
        return None
