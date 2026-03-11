"""Unit tests for LLMLogStore — in-memory ring buffer for LLM call logs."""

import uuid

import pytest

from app.domain.services.llm_log_store import LLMLogEntry, LLMLogStore


def _make_entry(
    *,
    model: str = "gpt-4",
    agent_type: str = "intake",
    status: str = "success",
    total_tokens: int = 100,
    latency_ms: float = 500.0,
    case_id: str = "case-1",
    session_id: str = "sess-1",
) -> LLMLogEntry:
    return LLMLogEntry(
        id=str(uuid.uuid4()),
        timestamp="2026-03-11T10:00:00Z",
        model=model,
        agent_type=agent_type,
        case_id=case_id,
        session_id=session_id,
        prompt_tokens=60,
        completion_tokens=40,
        total_tokens=total_tokens,
        latency_ms=latency_ms,
        status=status,
        error_message="" if status == "success" else "LLM call failed",
        request_messages=[{"role": "user", "content": "test"}],
        response_content="test response",
        finish_reason="stop",
        temperature=0.3,
        max_tokens=4096,
    )


class TestEmptyStore:
    def test_query_returns_empty(self):
        store = LLMLogStore()
        entries, total = store.query()
        assert entries == []
        assert total == 0

    def test_get_by_id_returns_none(self):
        store = LLMLogStore()
        assert store.get_by_id("nonexistent") is None

    def test_stats_returns_zeros(self):
        store = LLMLogStore()
        stats = store.get_stats()
        assert stats["total_requests"] == 0
        assert stats["total_tokens"] == 0
        assert stats["avg_latency_ms"] == 0.0
        assert stats["error_rate"] == 0.0

    def test_distinct_models_empty(self):
        store = LLMLogStore()
        assert store.get_distinct_models() == []

    def test_distinct_agent_types_empty(self):
        store = LLMLogStore()
        assert store.get_distinct_agent_types() == []


class TestAddAndQuery:
    def test_add_single_entry(self):
        store = LLMLogStore()
        entry = _make_entry()
        store.add(entry)
        results, total = store.query()
        assert total == 1
        assert results[0].id == entry.id

    def test_get_by_id_found(self):
        store = LLMLogStore()
        entry = _make_entry()
        store.add(entry)
        found = store.get_by_id(entry.id)
        assert found is not None
        assert found.model == "gpt-4"

    def test_newest_first_ordering(self):
        store = LLMLogStore()
        e1 = _make_entry(case_id="first")
        e2 = _make_entry(case_id="second")
        e3 = _make_entry(case_id="third")
        store.add(e1)
        store.add(e2)
        store.add(e3)
        results, _ = store.query()
        assert results[0].case_id == "third"
        assert results[2].case_id == "first"


class TestFiltering:
    def test_filter_by_model(self):
        store = LLMLogStore()
        store.add(_make_entry(model="gpt-4"))
        store.add(_make_entry(model="gpt-4o-mini"))
        store.add(_make_entry(model="gpt-4"))
        results, total = store.query(model="gpt-4o-mini")
        assert total == 1
        assert results[0].model == "gpt-4o-mini"

    def test_filter_by_agent_type(self):
        store = LLMLogStore()
        store.add(_make_entry(agent_type="intake"))
        store.add(_make_entry(agent_type="screening"))
        store.add(_make_entry(agent_type="intake"))
        results, total = store.query(agent_type="screening")
        assert total == 1

    def test_filter_by_status(self):
        store = LLMLogStore()
        store.add(_make_entry(status="success"))
        store.add(_make_entry(status="error"))
        store.add(_make_entry(status="success"))
        results, total = store.query(status="error")
        assert total == 1
        assert results[0].status == "error"

    def test_filter_combined(self):
        store = LLMLogStore()
        store.add(_make_entry(model="gpt-4", agent_type="intake"))
        store.add(_make_entry(model="gpt-4o-mini", agent_type="intake"))
        store.add(_make_entry(model="gpt-4", agent_type="screening"))
        results, total = store.query(model="gpt-4", agent_type="intake")
        assert total == 1

    def test_filter_by_case_id(self):
        store = LLMLogStore()
        store.add(_make_entry(case_id="abc"))
        store.add(_make_entry(case_id="def"))
        results, total = store.query(case_id="abc")
        assert total == 1


class TestPagination:
    def test_limit(self):
        store = LLMLogStore()
        for _ in range(10):
            store.add(_make_entry())
        results, total = store.query(limit=3)
        assert len(results) == 3
        assert total == 10

    def test_offset(self):
        store = LLMLogStore()
        for i in range(5):
            store.add(_make_entry(case_id=f"case-{i}"))
        results, total = store.query(limit=2, offset=2)
        assert len(results) == 2
        assert total == 5


class TestRingBufferEviction:
    def test_evicts_oldest_when_full(self):
        store = LLMLogStore(max_entries=3)
        e1 = _make_entry(case_id="oldest")
        e2 = _make_entry(case_id="middle")
        e3 = _make_entry(case_id="newest")
        store.add(e1)
        store.add(e2)
        store.add(e3)

        # Add one more — should evict e1
        e4 = _make_entry(case_id="extra")
        store.add(e4)

        _, total = store.query()
        assert total == 3
        assert store.get_by_id(e1.id) is None  # evicted
        assert store.get_by_id(e2.id) is not None
        assert store.get_by_id(e4.id) is not None


class TestStats:
    def test_stats_with_entries(self):
        store = LLMLogStore()
        store.add(_make_entry(total_tokens=100, latency_ms=200.0, status="success"))
        store.add(_make_entry(total_tokens=300, latency_ms=800.0, status="success"))
        store.add(_make_entry(total_tokens=200, latency_ms=500.0, status="error"))

        stats = store.get_stats()
        assert stats["total_requests"] == 3
        assert stats["total_tokens"] == 600
        assert stats["avg_latency_ms"] == 500.0
        assert stats["error_count"] == 1
        assert stats["error_rate"] == pytest.approx(33.3, abs=0.1)

    def test_stats_by_model(self):
        store = LLMLogStore()
        store.add(_make_entry(model="gpt-4", total_tokens=100))
        store.add(_make_entry(model="gpt-4o-mini", total_tokens=50))
        store.add(_make_entry(model="gpt-4", total_tokens=200))

        stats = store.get_stats()
        assert stats["by_model"]["gpt-4"]["count"] == 2
        assert stats["by_model"]["gpt-4"]["tokens"] == 300
        assert stats["by_model"]["gpt-4o-mini"]["count"] == 1

    def test_stats_by_agent_type(self):
        store = LLMLogStore()
        store.add(_make_entry(agent_type="intake", latency_ms=100.0))
        store.add(_make_entry(agent_type="intake", latency_ms=300.0))
        store.add(_make_entry(agent_type="screening", latency_ms=500.0))

        stats = store.get_stats()
        assert stats["by_agent_type"]["intake"]["count"] == 2
        assert stats["by_agent_type"]["intake"]["avg_latency_ms"] == 200.0
        assert stats["by_agent_type"]["screening"]["count"] == 1


class TestDistinct:
    def test_distinct_models(self):
        store = LLMLogStore()
        store.add(_make_entry(model="gpt-4"))
        store.add(_make_entry(model="gpt-4o-mini"))
        store.add(_make_entry(model="gpt-4"))
        models = store.get_distinct_models()
        assert set(models) == {"gpt-4", "gpt-4o-mini"}

    def test_distinct_agent_types(self):
        store = LLMLogStore()
        store.add(_make_entry(agent_type="intake"))
        store.add(_make_entry(agent_type="screening"))
        types = store.get_distinct_agent_types()
        assert set(types) == {"intake", "screening"}
