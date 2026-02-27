---
title: 'AI Agent System Blueprint - Compass Vitals'
project: '2026-Compass_Vitals_Agent'
created: '2026-02-26'
status: 'ready-for-implementation'
language: 'Vietnamese'
version: '1.0'
references:
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/research/technical-ai-agent-frameworks-medical-healthcare-research-2026-02-24.md'
  - 'docs/service-3-access-to-care-247-high-level-flow.md'
---

# AI Agent System Blueprint — Compass Vitals

> Tài liệu blueprint chi tiết A-to-Z cho toàn bộ hệ thống AI Agent. Đây là nguồn tham khảo duy nhất để BMAD Dev agent xây dựng `ai-agent-service` — bao gồm setup, kiến trúc, từng agent, từng workflow, NLP, security, testing, và deployment.

---

## Mục lục

1. [Tổng quan hệ thống Agent](#1-tổng-quan-hệ-thống-agent)
2. [Kiến trúc & Thiết kế](#2-kiến-trúc--thiết-kế)
3. [Setup & Cấu hình ban đầu](#3-setup--cấu-hình-ban-đầu)
4. [LLM Gateway](#4-llm-gateway)
5. [PHI De-identification Pipeline](#5-phi-de-identification-pipeline)
6. [Chi tiết từng Agent](#6-chi-tiết-từng-agent)
7. [LangGraph Workflow Graphs](#7-langgraph-workflow-graphs)
8. [Vietnamese NLP Pipeline](#8-vietnamese-nlp-pipeline)
9. [Confidence Scoring System](#9-confidence-scoring-system)
10. [Kafka Event Integration](#10-kafka-event-integration)
11. [Database Schema](#11-database-schema)
12. [API Endpoints](#12-api-endpoints)
13. [Security & PHI Protection](#13-security--phi-protection)
14. [Error Handling & Resilience](#14-error-handling--resilience)
15. [Testing Strategy](#15-testing-strategy)
16. [Thứ tự triển khai](#16-thứ-tự-triển-khai)

---

## 1. Tổng quan hệ thống Agent

### 1.1 Mục đích

AI Agent System là trái tim của nền tảng Compass Vitals — xử lý **80% công việc lâm sàng** tự động, từ thu thập triệu chứng đến đề xuất phác đồ điều trị. Hệ thống kết hợp 5 AI agent chuyên biệt hoạt động theo mô hình Supervisor Pattern, phục vụ 4 luồng chăm sóc (Care Flow) cho bệnh nhân Vietnamese-American.

### 1.2 Vai trò trong nền tảng

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPASS VITALS PLATFORM                       │
│                                                                  │
│  ┌──────────┐    ┌──────────────────┐    ┌──────────────────┐   │
│  │ Patient   │───▶│  AI Agent System  │───▶│  VN MD Dashboard │   │
│  │ Portal    │    │  (80% tự động)   │    │  (Review/Draft)  │   │
│  │ (Chat)    │◀───│                  │    └────────┬─────────┘   │
│  └──────────┘    │  ┌────────────┐  │             │              │
│                  │  │ Supervisor │  │             ▼              │
│                  │  │ ┌────────┐ │  │    ┌──────────────────┐   │
│                  │  │ │Intake  │ │  │    │  US MD Dashboard  │   │
│                  │  │ │Screen  │ │  │    │  (Approve/Sign)   │   │
│                  │  │ │Propose │ │  │    └──────────────────┘   │
│                  │  │ │Critic  │ │  │                            │
│                  │  │ └────────┘ │  │                            │
│                  │  └────────────┘  │                            │
│                  └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Mô hình Triple Safety Net

Mọi quyết định lâm sàng đều trải qua 3 lớp kiểm tra:

| Lớp | Actor | Vai trò | Thời gian |
|-----|-------|---------|-----------|
| **Lớp 1** | AI Critic Agent | Validation tự động, phát hiện hallucination, kiểm tra drug interaction | <30 giây |
| **Lớp 2** | VN MD (Bác sĩ Việt) | Review lâm sàng, tạo Draft Orders, cầu nối văn hóa | ~10 phút |
| **Lớp 3** | US MD (Bác sĩ Mỹ) | Phê duyệt cuối cùng, ký đơn thuốc, chịu trách nhiệm pháp lý | ~5 phút |

### 1.4 Năm Agent chuyên biệt

| Agent | Vai trò | Thay thế | FR tương ứng |
|-------|---------|----------|--------------|
| **Supervisor** | Điều phối workflow, route case | Quản lý phòng khám | — |
| **Intake** | Thu thập triệu chứng qua chat | Y tá triage (RN) | FR9 |
| **Screening** | Đánh giá lâm sàng, phân loại severity | Bác sĩ đánh giá sơ bộ | FR10, FR14 |
| **Proposer** | Đề xuất phác đồ điều trị | Bác sĩ kê đơn | FR11, FR12, FR13 |
| **Critic** | Kiểm tra adversarial, safety net | Dược sĩ + Peer review | FR15, FR16 |

### 1.5 Bốn Care Flow

| Flow | Tên | Số trạm | SLA | Đặc điểm |
|------|-----|---------|-----|-----------|
| **A** | Emergency | 6 | <15 phút | KHÔNG cần MD approval, tối ưu tốc độ |
| **B** | Prescription | 9 | Premium <1h, Plus <2h, Connect <4h | **MVP Priority**, 3-Stage Order Lifecycle |
| **C** | Lab/Imaging | 9 | 1-7 ngày | Tương tự Flow B, output là lab orders |
| **D** | Monitoring | 14 | 24-72h | 3 entry points, AI check-in định kỳ |

### 1.6 Chỉ số mục tiêu

| Chỉ số | Mục tiêu | Ghi chú |
|--------|----------|---------|
| AI Response Time | <2 giây | Mỗi turn trong conversation |
| Medical Accuracy | >90% | So với quyết định của board-certified MD |
| Hallucination Rate | <2% | Caught bởi Critic Agent + MD review |
| Drug Interaction Detection | 100% | Zero tolerance — safety-critical |
| Allergy Screening | 100% | Zero tolerance — safety-critical |
| Emergency Detection | 100% | Không được bỏ sót trường hợp khẩn cấp |
| Vietnamese NLP Accuracy | >90% | Nhận diện biểu đạt văn hóa |
| LLM Cost Per Interaction | <$5 | Hybrid LLM strategy |
| Concurrent Sessions | 500+ | Horizontal autoscaling |

---

## 2. Kiến trúc & Thiết kế

### 2.1 Supervisor Pattern

Hệ thống sử dụng **Supervisor Pattern** của LangGraph 1.0 GA — một coordinator trung tâm (Supervisor Agent) điều phối các agent chuyên biệt:

```
                    ┌─────────────────┐
                    │   SUPERVISOR     │
                    │   (Coordinator)  │
                    └───────┬─────────┘
                            │ Điều phối
               ┌────────────┼────────────┐
               ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  INTAKE   │ │SCREENING │ │ PROPOSER │
        │  Agent    │ │  Agent   │ │  Agent   │
        └──────────┘ └──────────┘ └────┬─────┘
                                       │
                                       ▼
                                 ┌──────────┐
                                 │  CRITIC   │
                                 │  Agent    │
                                 └──────────┘
```

**Đặc điểm:**
- Supervisor KHÔNG gọi trực tiếp agent → thay vào đó, điều khiển luồng qua **conditional edges** trong LangGraph StateGraph
- Tất cả agents đọc/ghi vào **cùng một shared state** (`CareFlowState`)
- Supervisor quyết định agent tiếp theo dựa trên trạng thái hiện tại của state

### 2.2 LangGraph StateGraph

Mỗi care flow được implement dưới dạng một `StateGraph`:

```python
from langgraph.graph import StateGraph, END

# Ví dụ Prescription Flow
graph = StateGraph(CareFlowState)

# Thêm nodes (mỗi node = một function xử lý)
graph.add_node("intake", intake_node)
graph.add_node("screening", screening_node)
graph.add_node("proposal", proposal_node)
graph.add_node("critic_review", critic_node)
graph.add_node("priority_route", priority_node)

# Thêm edges (luồng chuyển tiếp)
graph.add_edge("intake", "screening")
graph.add_edge("screening", "proposal")
graph.add_edge("proposal", "critic_review")

# Conditional edge (routing logic)
graph.add_conditional_edges(
    "critic_review",
    route_after_critic,  # Function quyết định đi đâu tiếp
    {
        "approved": "priority_route",
        "rejected": "proposal",  # Quay lại Proposer nếu bị reject
    }
)
```

### 2.3 Shared State Schema

**File:** `services/ai-agent-service/app/agents/state.py`

Đây là **data contract duy nhất** giữa tất cả agents. Mọi agent đọc từ state và ghi kết quả vào state:

```python
from typing import TypedDict, Literal, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class CareFlowState(TypedDict):
    """Shared state cho toàn bộ care flow. Tất cả agents đọc/ghi vào đây."""

    # === Patient Context ===
    patient_id: str                    # UUID bệnh nhân
    case_id: str                       # UUID case hiện tại
    organization_id: str               # UUID tổ chức (multi-tenancy)

    # === Conversation ===
    messages: Annotated[list[BaseMessage], add_messages]  # Chat history (append-only)

    # === Intake Data (Intake Agent ghi) ===
    intake_data: dict | None           # Structured intake: symptoms, duration, severity, history
    intake_complete: bool              # Intake Agent đã thu thập đủ thông tin chưa

    # === Screening Results (Screening Agent ghi) ===
    screening_result: dict | None      # Clinical assessment
    severity: Literal["emergency", "urgent", "routine"] | None
    differential_diagnoses: list[dict] # Danh sách chẩn đoán phân biệt
    is_emergency: bool                 # Flag khẩn cấp

    # === Order Recommendations (Proposer Agent ghi) ===
    order_recommendations: list[dict]  # Danh sách đề xuất (thuốc/lab/monitoring)
    drug_interactions: list[dict]      # Kết quả kiểm tra tương tác thuốc
    allergy_alerts: list[dict]         # Cảnh báo dị ứng

    # === Critic Validation (Critic Agent ghi) ===
    critic_validation: dict | None     # Kết quả validation
    critic_approved: bool              # Critic đã approve chưa
    critic_issues: list[dict]          # Danh sách vấn đề phát hiện

    # === Confidence Scoring ===
    confidence_score: float | None     # Điểm tin cậy tổng thể (0-100)
    confidence_breakdown: dict | None  # Chi tiết từng factor

    # === Flow Control ===
    current_station: int               # Trạm hiện tại (1-14)
    flow_type: Literal["emergency", "prescription", "lab", "monitoring"] | None
    needs_human_review: bool           # Cần MD review không
    human_review_reason: str | None    # Lý do cần review

    # === NLP Context ===
    detected_language: str             # "vi", "en", hoặc "mixed"
    cultural_expressions: list[dict]   # Biểu đạt văn hóa phát hiện được

    # === Metadata ===
    created_at: str                    # ISO 8601
    updated_at: str                    # ISO 8601
    correlation_id: str                # UUID cho distributed tracing
```

### 2.4 Agent Communication

Agents **KHÔNG** giao tiếp trực tiếp với nhau. Luồng giao tiếp:

1. Supervisor khởi tạo `CareFlowState`
2. LangGraph graph engine gọi từng node (agent) theo thứ tự
3. Mỗi agent đọc state → xử lý → ghi kết quả vào state
4. Conditional edges kiểm tra state để quyết định node tiếp theo

### 2.5 Human-in-the-Loop

LangGraph hỗ trợ **interrupt points** — nơi workflow tạm dừng chờ con người:

```python
from langgraph.checkpoint.postgres import PostgresSaver

# Tạo checkpointer để lưu state khi interrupt
checkpointer = PostgresSaver(connection_string=DATABASE_URL)

# Compile graph với interrupt points
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["vn_md_review", "us_md_review"]  # Dừng trước node này
)
```

Khi graph dừng tại interrupt point:
1. State được lưu vào PostgreSQL (qua checkpointer)
2. Kafka event được publish (thông báo MD có case cần review)
3. MD review trên dashboard → gọi API resume workflow
4. Graph tiếp tục từ interrupt point với state đã cập nhật

### 2.6 Event-Driven Integration

`ai-agent-service` giao tiếp với các service khác qua Kafka:

```
ai-agent-service ──publish──▶ care.case.created ──▶ clinical-workflow-service
ai-agent-service ──publish──▶ order.recommendation.generated ──▶ clinical-workflow-service
ai-agent-service ──publish──▶ care.case.escalated ──▶ notification-service
ai-agent-service ◀──consume── care.case.created (trigger from other services)
```

---

## 3. Setup & Cấu hình ban đầu

### 3.1 Cấu trúc thư mục đầy đủ

```
services/ai-agent-service/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app, lifespan, middleware, routers
│   ├── config.py                        # Pydantic BaseSettings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── routes/
│   │       │   ├── __init__.py
│   │       │   ├── chat.py              # POST /api/v1/chat, WebSocket /api/v1/chat/ws
│   │       │   └── screening.py         # POST /api/v1/screening/start, GET status/results
│   │       └── schemas/
│   │           ├── __init__.py
│   │           ├── chat.py              # ChatRequest, ChatResponse
│   │           └── screening.py         # ScreeningStartRequest, ScreeningStatusResponse
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dependencies.py              # FastAPI DI (get_db, get_kafka, get_llm_gateway)
│   │   ├── security.py                  # JWT validation, RBAC checks
│   │   └── exceptions.py               # Custom exception hierarchy
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── agent_session.py         # SQLAlchemy: agent_sessions table
│   │   │   ├── screening_result.py      # SQLAlchemy: screening_results table
│   │   │   ├── phi_mapping.py           # SQLAlchemy: phi_mappings table
│   │   │   └── cultural_expression.py   # SQLAlchemy: cultural_expressions table
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── session_repository.py
│   │   │   ├── screening_repository.py
│   │   │   └── phi_mapping_repository.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── llm_gateway.py           # LLM integration layer (GPT-4 + Claude)
│   │       ├── phi_deidentifier.py      # PHI de-identification pipeline
│   │       └── confidence_scorer.py     # Confidence scoring algorithm
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── state.py                     # CareFlowState TypedDict (CRITICAL)
│   │   ├── supervisor.py                # Supervisor Agent
│   │   ├── intake_agent.py              # Intake Agent
│   │   ├── screening_agent.py           # Screening Agent
│   │   ├── proposer_agent.py            # Proposer Agent
│   │   ├── critic_agent.py              # Critic Agent
│   │   ├── tools/                       # Agent tools (functions)
│   │   │   ├── __init__.py
│   │   │   ├── patient_lookup.py        # Tra cứu hồ sơ bệnh nhân
│   │   │   ├── drug_interaction.py      # Kiểm tra tương tác thuốc
│   │   │   ├── allergy_checker.py       # Kiểm tra dị ứng
│   │   │   ├── emergency_detector.py    # Phát hiện khẩn cấp
│   │   │   └── fhir_formatter.py        # Format output theo FHIR
│   │   ├── prompts/                     # System prompts cho từng agent
│   │   │   ├── __init__.py
│   │   │   ├── intake_prompt.py
│   │   │   ├── screening_prompt.py
│   │   │   ├── proposer_prompt.py
│   │   │   └── critic_prompt.py
│   │   └── graphs/                      # LangGraph StateGraph definitions
│   │       ├── __init__.py
│   │       ├── prescription_flow.py     # Flow B: 9 stations (MVP)
│   │       ├── emergency_flow.py        # Flow A: 6 stations
│   │       ├── lab_flow.py              # Flow C: 9 stations
│   │       └── monitoring_flow.py       # Flow D: 14 stations
│   │
│   ├── nlp/                             # Vietnamese NLP pipeline
│   │   ├── __init__.py
│   │   ├── cultural_mapper.py           # Ánh xạ biểu đạt văn hóa VN
│   │   ├── code_switcher.py             # Xử lý code-switching VN↔EN
│   │   └── medical_terminology.py       # Thuật ngữ y khoa tiếng Việt
│   │
│   ├── events/                          # Kafka integration
│   │   ├── __init__.py
│   │   ├── producers.py                 # Kafka event producers
│   │   ├── consumers.py                 # Kafka event consumers
│   │   └── schemas.py                   # Event payload schemas
│   │
│   └── middleware/
│       ├── __init__.py
│       ├── audit.py                     # PHI access audit logging
│       └── phi_filter.py               # PHI de-identification middleware
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Shared fixtures (testcontainers, mocks)
│   ├── unit/
│   │   ├── test_intake_agent.py
│   │   ├── test_screening_agent.py
│   │   ├── test_proposer_agent.py
│   │   ├── test_critic_agent.py
│   │   ├── test_llm_gateway.py
│   │   ├── test_phi_deidentifier.py
│   │   ├── test_confidence_scorer.py
│   │   ├── test_cultural_mapper.py
│   │   └── test_code_switcher.py
│   └── integration/
│       ├── test_prescription_flow.py
│       ├── test_emergency_flow.py
│       ├── test_kafka_events.py
│       └── test_database.py
│
├── alembic/                             # Database migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│
├── Dockerfile
├── pyproject.toml
└── README.md
```

### 3.2 Dependencies (`pyproject.toml`)

```toml
[project]
name = "ai-agent-service"
version = "0.1.0"
requires-python = ">=3.13"

dependencies = [
    # Web Framework
    "fastapi[standard]>=0.133.0",
    "uvicorn[standard]>=0.34.0",

    # AI / LLM
    "langgraph>=1.0.0",
    "langchain-core>=0.3.0",
    "langchain-openai>=0.3.0",
    "langchain-anthropic>=0.3.0",
    "openai>=1.60.0",
    "anthropic>=0.40.0",

    # Database
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",

    # Cache
    "redis>=5.2.0",

    # Kafka
    "confluent-kafka>=2.6.0",

    # FHIR
    "fhir.resources>=7.1.0",

    # Security
    "cryptography>=44.0.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",

    # Validation
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",

    # Observability
    "opentelemetry-api>=1.29.0",
    "opentelemetry-sdk>=1.29.0",
    "opentelemetry-instrumentation-fastapi>=0.50b0",
    "structlog>=24.4.0",

    # Utilities
    "httpx>=0.28.0",
    "tenacity>=9.0.0",       # Retry library
    "circuitbreaker>=2.0.0", # Circuit breaker
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "testcontainers[postgres,kafka,redis]>=4.0.0",
    "httpx>=0.28.0",         # TestClient
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]
```

### 3.3 Environment Variables

```bash
# === LLM API Keys ===
OPENAI_API_KEY=sk-...                    # GPT-4 primary
ANTHROPIC_API_KEY=sk-ant-...             # Claude backup

# === Database ===
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/ai_agent_db

# === Redis ===
REDIS_URL=redis://localhost:6379/0

# === Kafka ===
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_SECURITY_PROTOCOL=SASL_SSL          # Production: SASL_SSL
KAFKA_SASL_MECHANISM=PLAIN

# === AWS Cognito ===
COGNITO_USER_POOL_ID=us-east-1_xxxxx
COGNITO_APP_CLIENT_ID=xxxxx
COGNITO_REGION=us-east-1
COGNITO_JWKS_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxx/.well-known/jwks.json

# === Service Config ===
SERVICE_NAME=ai-agent-service
SERVICE_PORT=8001
LOG_LEVEL=INFO
ENVIRONMENT=development                   # development | staging | production

# === LLM Config ===
PRIMARY_LLM_MODEL=gpt-4
BACKUP_LLM_MODEL=claude-sonnet-4-5-20250929
SCREENING_LLM_MODEL=gpt-4o-mini           # Cost optimization
LLM_MAX_RETRIES=3
LLM_RETRY_BACKOFF_SECONDS=2
LLM_CIRCUIT_BREAKER_THRESHOLD=5
LLM_CIRCUIT_BREAKER_TIMEOUT=60

# === PHI Config ===
PHI_ENCRYPTION_KEY=...                     # AES-256 key
PHI_MAPPING_TTL_HOURS=24                   # Mapping expiry

# === Feature Flags ===
ENABLE_VOICE_CHAT=false                    # Phase 2
ENABLE_MONITORING_FLOW=true
```

### 3.4 Config Class (`config.py`)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Service
    service_name: str = "ai-agent-service"
    service_port: int = 8001
    environment: str = "development"
    log_level: str = "INFO"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"

    # LLM
    openai_api_key: str
    anthropic_api_key: str
    primary_llm_model: str = "gpt-4"
    backup_llm_model: str = "claude-sonnet-4-5-20250929"
    screening_llm_model: str = "gpt-4o-mini"
    llm_max_retries: int = 3
    llm_retry_backoff_seconds: int = 2
    llm_circuit_breaker_threshold: int = 5
    llm_circuit_breaker_timeout: int = 60

    # Cognito
    cognito_user_pool_id: str
    cognito_app_client_id: str
    cognito_region: str = "us-east-1"

    # PHI
    phi_encryption_key: str
    phi_mapping_ttl_hours: int = 24

settings = Settings()
```

### 3.5 FastAPI App (`main.py`)

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.v1.routes import chat, screening
from app.middleware.audit import AuditMiddleware
from app.middleware.phi_filter import PHIFilterMiddleware
from app.events.consumers import start_kafka_consumers, stop_kafka_consumers
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB pool, Redis, Kafka consumers. Shutdown: cleanup."""
    # Startup
    await init_database()
    await init_redis()
    await start_kafka_consumers()
    yield
    # Shutdown
    await stop_kafka_consumers()
    await close_redis()
    await close_database()

app = FastAPI(
    title="AI Agent Service",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware (thứ tự quan trọng: outer → inner)
app.add_middleware(AuditMiddleware)       # Log mọi PHI access
app.add_middleware(PHIFilterMiddleware)   # Verify PHI de-identification

# Routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(screening.router, prefix="/api/v1", tags=["screening"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.service_name}
```

### 3.6 Docker Setup

**Dockerfile:**
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY app/ app/
COPY alembic/ alembic/
COPY alembic.ini .

# Run with uvicorn
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**docker-compose.yml (local dev):**
```yaml
services:
  ai-agent-service:
    build: ./services/ai-agent-service
    ports:
      - "8001:8001"
    env_file:
      - ./services/ai-agent-service/.env
    depends_on:
      - postgres
      - redis
      - kafka

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ai_agent_db
      POSTGRES_USER: compass
      POSTGRES_PASSWORD: compass_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  kafka:
    image: confluentinc/cp-kafka:7.7.1
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  zookeeper:
    image: confluentinc/cp-zookeeper:7.7.1
    ports:
      - "2181:2181"
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

volumes:
  postgres_data:
```

---

## 4. LLM Gateway

### 4.1 Tổng quan

**File:** `services/ai-agent-service/app/domain/services/llm_gateway.py`

LLM Gateway là **cổng duy nhất** để gọi external LLM APIs. Mọi agent BẮT BUỘC phải đi qua gateway — không được gọi OpenAI/Anthropic trực tiếp.

```
Agent ──▶ LLM Gateway ──▶ PHI Verification Gate ──▶ Provider Selection ──▶ Retry/Fallback ──▶ LLM API
                                    │                        │
                                    ▼                        ▼
                              BLOCK nếu               GPT-4 (primary)
                              chưa de-identify        Claude (backup)
```

### 4.2 Interface Design

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class LLMResponse(BaseModel):
    content: str
    model: str
    usage: dict  # {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
    finish_reason: str

class LLMProvider(ABC):
    """Abstract interface cho mọi LLM provider."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Generate text completion."""

    @abstractmethod
    async def generate_structured(
        self,
        messages: list[dict],
        response_format: type[BaseModel],
        temperature: float = 0.1,
    ) -> BaseModel:
        """Generate structured output (JSON matching Pydantic model)."""


class OpenAIProvider(LLMProvider):
    """GPT-4 implementation."""
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, messages, temperature=0.3, max_tokens=4096):
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=self.model,
            usage=response.usage.model_dump(),
            finish_reason=response.choices[0].finish_reason,
        )

    async def generate_structured(self, messages, response_format, temperature=0.1):
        response = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=response_format,
            temperature=temperature,
        )
        return response.choices[0].message.parsed


class AnthropicProvider(LLMProvider):
    """Claude implementation."""
    # Tương tự OpenAIProvider nhưng dùng Anthropic SDK
```

### 4.3 LLM Gateway Class

```python
from tenacity import retry, stop_after_attempt, wait_exponential
from circuitbreaker import circuit

class LLMGateway:
    """Cổng duy nhất để gọi LLM. Bao gồm PHI verification, retry, fallback, circuit breaker."""

    def __init__(self, settings: Settings, phi_deidentifier: PHIDeidentifier):
        self.primary = OpenAIProvider(settings.openai_api_key, settings.primary_llm_model)
        self.backup = AnthropicProvider(settings.anthropic_api_key, settings.backup_llm_model)
        self.screening = OpenAIProvider(settings.openai_api_key, settings.screening_llm_model)
        self.phi_deidentifier = phi_deidentifier

    async def generate(
        self,
        messages: list[dict],
        agent_type: str,      # "intake", "screening", "proposer", "critic"
        case_id: str,
        **kwargs,
    ) -> LLMResponse:
        """Generate với PHI verification + retry + fallback."""

        # BƯỚC 1: PHI Verification Gate
        self._verify_no_phi(messages, case_id)

        # BƯỚC 2: Chọn provider dựa trên agent type
        provider = self._select_provider(agent_type)

        # BƯỚC 3: Gọi LLM với retry + fallback
        try:
            response = await self._call_with_retry(provider, messages, **kwargs)
        except LLMError:
            # Fallback sang backup provider
            response = await self._call_with_retry(self.backup, messages, **kwargs)

        # BƯỚC 4: Log usage (cost tracking)
        await self._log_usage(response, agent_type, case_id)

        return response

    def _verify_no_phi(self, messages: list[dict], case_id: str):
        """BLOCK nếu phát hiện PHI trong messages."""
        for msg in messages:
            if self.phi_deidentifier.contains_phi(msg["content"]):
                raise PHIAccessError(
                    f"PHI detected in LLM request for case {case_id}. "
                    "Messages must be de-identified before calling LLM."
                )

    def _select_provider(self, agent_type: str) -> LLMProvider:
        """Hybrid LLM strategy: agent khác nhau dùng model khác nhau."""
        if agent_type == "intake":
            return self.screening  # GPT-4o-mini (cost optimization — intake chỉ thu thập data)
        elif agent_type == "screening":
            return self.primary    # GPT-4 (cần accuracy cao cho clinical assessment)
        elif agent_type == "proposer":
            return self.primary    # GPT-4 (treatment recommendations cần accuracy cao nhất)
        elif agent_type == "critic":
            return self.primary    # GPT-4 (validation cần accuracy)
        return self.primary

    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=8))
    async def _call_with_retry(self, provider: LLMProvider, messages, **kwargs):
        """Gọi LLM với circuit breaker + retry."""
        return await provider.generate(messages, **kwargs)

    async def _log_usage(self, response: LLMResponse, agent_type: str, case_id: str):
        """Log token usage cho cost tracking."""
        # Log vào structured logger
        logger.info(
            "llm_usage",
            model=response.model,
            agent_type=agent_type,
            case_id=case_id,
            prompt_tokens=response.usage["prompt_tokens"],
            completion_tokens=response.usage["completion_tokens"],
        )
```

### 4.4 Hybrid LLM Strategy (Cost Optimization)

| Agent | Model | Lý do | Chi phí ước tính |
|-------|-------|-------|-------------------|
| Intake | GPT-4o-mini | Chỉ thu thập data, không cần clinical reasoning | ~$0.15/1M tokens |
| Screening | GPT-4 | Clinical assessment cần accuracy cao (93.1% MedQA) | ~$30/1M tokens |
| Proposer | GPT-4 | Treatment recommendations — safety-critical | ~$30/1M tokens |
| Critic | GPT-4 | Validation cần reasoning mạnh | ~$30/1M tokens |
| Complex cases | Claude Sonnet | Context window 200K tokens cho patient history dài | ~$15/1M tokens |

**Ước tính chi phí per patient interaction:** ~$2-4 (vs $15+ nếu dùng GPT-4 cho tất cả)

### 4.5 Prompt Management

Mỗi agent có system prompt riêng, được quản lý trong `agents/prompts/`:

```python
# agents/prompts/intake_prompt.py

INTAKE_SYSTEM_PROMPT = """You are a Medical Intake Specialist AI for Compass Vitals telemedicine platform.

ROLE: Gather patient symptoms through conversational interview.
LANGUAGE: Respond in the patient's language (Vietnamese or English). Support code-switching.
CULTURAL AWARENESS: Recognize Vietnamese cultural health expressions (see cultural_expressions in state).

INTERVIEW PROTOCOL:
1. Greet patient warmly in their language
2. Ask about chief complaint (main symptom)
3. Follow OLDCARTS framework:
   - Onset: Khi nào bắt đầu?
   - Location: Ở vị trí nào?
   - Duration: Kéo dài bao lâu?
   - Character: Mô tả cảm giác?
   - Aggravating/Alleviating: Điều gì làm tăng/giảm?
   - Radiation: Có lan ra nơi khác không?
   - Timing: Thường xuyên hay từng đợt?
   - Severity: Mức độ 1-10?
4. Ask about current medications and allergies
5. Ask about relevant medical history

OUTPUT: Set intake_complete=true when sufficient data collected.
NEVER: Generate diagnoses. NEVER: Recommend treatment. You ONLY gather information.
SAFETY: If patient describes emergency symptoms, set is_emergency=true IMMEDIATELY.
"""
```

---

## 5. PHI De-identification Pipeline

### 5.1 Tổng quan

**File:** `services/ai-agent-service/app/domain/services/phi_deidentifier.py`

PHI (Protected Health Information) de-identification là **BẮT BUỘC** trước mọi LLM call. Đây là yêu cầu HIPAA — PHI không bao giờ được gửi tới external LLM APIs.

### 5.2 18 HIPAA Safe Harbor Identifiers

Danh sách 18 loại PHI cần remove theo HIPAA Safe Harbor method:

| # | PHI Type | Ví dụ | Regex Pattern |
|---|----------|-------|---------------|
| 1 | Tên (Names) | Nguyễn Văn A | Vietnamese + English name patterns |
| 2 | Địa chỉ (Address) | 123 Main St, Houston TX | Street/city/state/zip patterns |
| 3 | Ngày (Dates) | 05/10/1968, March 15 | Date patterns (MM/DD/YYYY, etc.) |
| 4 | Số điện thoại | (713) 555-1234 | US phone patterns |
| 5 | Fax | (713) 555-1235 | US fax patterns |
| 6 | Email | patient@email.com | Email regex |
| 7 | SSN | 123-45-6789 | SSN pattern |
| 8 | MRN (Medical Record Number) | MRN-001234 | Custom MRN pattern |
| 9 | Health plan beneficiary # | HPN-12345 | Insurance ID patterns |
| 10 | Account numbers | ACC-98765 | Account patterns |
| 11 | Certificate/license # | TX-MD-12345 | License patterns |
| 12 | Vehicle identifiers | — | Vehicle plate patterns |
| 13 | Device identifiers | — | Serial number patterns |
| 14 | Web URLs | http://patient-site.com | URL regex |
| 15 | IP addresses | 192.168.1.100 | IPv4/IPv6 patterns |
| 16 | Biometric identifiers | — | N/A (không trong text) |
| 17 | Full-face photos | — | N/A (không trong text) |
| 18 | Unique identifying codes | UUID, custom IDs | Various ID patterns |

### 5.3 De-identification Algorithm

```python
import re
import uuid
from cryptography.fernet import Fernet

class PHIDeidentifier:
    """De-identify PHI trước khi gửi LLM. Re-identify sau khi nhận response."""

    PHI_PATTERNS = {
        "name": r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b",  # Simplified — production cần comprehensive
        "vietnamese_name": r"\b(Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô|Dương|Lý)\s\w+(\s\w+)?\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "phone": r"\b(\+1\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "date_of_birth": r"\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/\d{4}\b",
        "address": r"\b\d+\s[A-Z][a-z]+\s(St|Ave|Blvd|Rd|Dr|Ln|Ct|Way)\b",
        "zip_code": r"\b\d{5}(-\d{4})?\b",
        "mrn": r"\b(MRN|mrn)[- ]?\d{4,}\b",
        "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }

    def __init__(self, encryption_key: str, mapping_repository):
        self.fernet = Fernet(encryption_key.encode())
        self.mapping_repo = mapping_repository

    async def deidentify(self, text: str, case_id: str) -> tuple[str, dict]:
        """
        De-identify text. Trả về (de-identified_text, mapping).
        mapping được lưu encrypted trong DB để re-identify sau.
        """
        mapping = {}
        result = text

        for phi_type, pattern in self.PHI_PATTERNS.items():
            for match in re.finditer(pattern, result):
                original = match.group()
                if original not in mapping:
                    pseudonym = f"[REF-{uuid.uuid4().hex[:8]}]"
                    mapping[original] = {
                        "pseudonym": pseudonym,
                        "phi_type": phi_type,
                    }
                result = result.replace(original, mapping[original]["pseudonym"])

        # Lưu mapping encrypted vào DB
        if mapping:
            await self.mapping_repo.save_mapping(
                case_id=case_id,
                mapping=self._encrypt_mapping(mapping),
            )

        return result, mapping

    async def reidentify(self, text: str, case_id: str) -> str:
        """Re-identify text (chỉ cho internal use — MD dashboard display)."""
        encrypted_mapping = await self.mapping_repo.get_mapping(case_id)
        if not encrypted_mapping:
            return text

        mapping = self._decrypt_mapping(encrypted_mapping)
        result = text
        for original, info in mapping.items():
            result = result.replace(info["pseudonym"], original)
        return result

    def contains_phi(self, text: str) -> bool:
        """Kiểm tra text có chứa PHI không (dùng trong PHI Verification Gate)."""
        for phi_type, pattern in self.PHI_PATTERNS.items():
            if re.search(pattern, text):
                return True
        return False

    def _encrypt_mapping(self, mapping: dict) -> bytes:
        return self.fernet.encrypt(json.dumps(mapping).encode())

    def _decrypt_mapping(self, encrypted: bytes) -> dict:
        return json.loads(self.fernet.decrypt(encrypted).decode())
```

### 5.4 PHI Filter Middleware

**File:** `services/ai-agent-service/app/middleware/phi_filter.py`

Middleware này intercept mọi outgoing HTTP call tới LLM APIs:

```python
class PHIFilterMiddleware:
    """Verify rằng không có PHI trong outgoing LLM requests."""

    async def __call__(self, request, call_next):
        # Mọi request đi qua LLM Gateway đã verify PHI
        # Middleware này là lớp bảo vệ thứ hai
        response = await call_next(request)
        return response
```

### 5.5 Audit Logging

Mọi lần truy cập PHI đều được log:

```python
# Mỗi khi de-identify hoặc re-identify:
await audit_logger.log({
    "event_type": "phi.deidentified",  # hoặc "phi.reidentified"
    "case_id": case_id,
    "actor_id": current_user.id,
    "actor_role": current_user.role,
    "phi_types_found": ["name", "dob", "phone"],  # Loại PHI phát hiện
    "timestamp": datetime.utcnow().isoformat(),
    "correlation_id": correlation_id,
})
```

---

## 6. Chi tiết từng Agent

### 6.1 Supervisor Agent

**File:** `services/ai-agent-service/app/agents/supervisor.py`

**Mục đích:** Orchestrator trung tâm — nhận patient complaint ban đầu, xác định flow type, khởi tạo và điều phối workflow.

**Input:**
- Patient initial complaint (text message)
- Patient profile (từ patient-service API)

**Output:**
- `flow_type`: "emergency" | "prescription" | "lab" | "monitoring"
- `CareFlowState` đã khởi tạo

**Logic:**

```python
async def supervisor_node(state: CareFlowState) -> CareFlowState:
    """
    Supervisor xác định flow type dựa trên screening results.
    Chạy sau Screening Agent.
    """
    if state["is_emergency"]:
        return {**state, "flow_type": "emergency"}

    severity = state["severity"]
    screening = state["screening_result"]

    # Dựa vào screening result để xác định flow type
    if screening.get("needs_prescription"):
        flow_type = "prescription"
    elif screening.get("needs_lab"):
        flow_type = "lab"
    elif screening.get("needs_monitoring"):
        flow_type = "monitoring"
    else:
        flow_type = "prescription"  # Default

    return {**state, "flow_type": flow_type}
```

**Routing Logic (conditional edges):**

```python
def route_by_flow_type(state: CareFlowState) -> str:
    """Conditional edge: route tới đúng care flow graph."""
    flow_type = state["flow_type"]
    if flow_type == "emergency":
        return "emergency_flow"
    elif flow_type == "prescription":
        return "prescription_flow"
    elif flow_type == "lab":
        return "lab_flow"
    elif flow_type == "monitoring":
        return "monitoring_flow"
    return "prescription_flow"
```

### 6.2 Intake Agent

**File:** `services/ai-agent-service/app/agents/intake_agent.py`

**Mục đích:** Thu thập triệu chứng qua conversational interview. Thay thế vai trò Y tá triage.

**FR tương ứng:** FR9 (Symptom Intake with Contextual Follow-up)

**Input:**
- `messages`: Chat history với bệnh nhân
- Patient profile (medications, allergies, medical history)

**Output (ghi vào state):**
- `intake_data`: Structured data theo OLDCARTS framework
- `intake_complete`: true khi đã thu thập đủ
- `cultural_expressions`: Biểu đạt văn hóa phát hiện được
- `detected_language`: "vi" | "en" | "mixed"
- `is_emergency`: true nếu phát hiện triệu chứng khẩn cấp

**Structured Intake Data Format:**

```python
{
    "chief_complaint": "Đau bụng bên phải dưới",
    "onset": "2 ngày trước",
    "location": "bụng phải dưới",
    "duration": "liên tục, 2 ngày",
    "character": "đau nhói, tăng khi di chuyển",
    "aggravating_factors": ["di chuyển", "ho"],
    "alleviating_factors": ["nằm yên"],
    "radiation": "không",
    "timing": "liên tục",
    "severity": 7,  # /10
    "associated_symptoms": ["sốt nhẹ 37.8°C", "chán ăn", "buồn nôn"],
    "current_medications": ["Metformin 500mg 2x/ngày"],
    "allergies": ["Penicillin (phát ban)"],
    "medical_history": ["Tiểu đường type 2", "Cao huyết áp"],
    "social_history": {
        "smoking": "không",
        "alcohol": "thỉnh thoảng",
    },
}
```

**NLP Integration Flow:**

```
Patient message (Vietnamese/mixed)
        │
        ▼
┌──────────────────┐
│  Code Switcher    │ → Detect language, normalize
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ Cultural Mapper   │ → "bị nóng trong" → inflammation symptoms
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ Medical Terms     │ → Vietnamese medical terms → English
└───────┬──────────┘
        │
        ▼
  Normalized text → LLM Gateway → Intake Agent LLM call
```

**Tools available cho Intake Agent:**

| Tool | Mô tả | Khi nào gọi |
|------|--------|-------------|
| `patient_profile_lookup` | Tra cứu thông tin bệnh nhân từ patient-service | Đầu conversation |
| `medical_history_fetch` | Lấy lịch sử khám bệnh | Khi cần context y khoa |
| `allergy_list_fetch` | Lấy danh sách dị ứng | Luôn luôn (safety-critical) |
| `emergency_detector` | Kiểm tra triệu chứng khẩn cấp | Mỗi message từ patient |

### 6.3 Screening Agent

**File:** `services/ai-agent-service/app/agents/screening_agent.py`

**Mục đích:** Đánh giá lâm sàng dựa trên intake data, phân loại severity, tạo differential diagnosis.

**FR tương ứng:** FR10 (Clinical Screening), FR14 (Emergency Detection)

**Input:**
- `intake_data`: Structured data từ Intake Agent
- Patient profile (medications, allergies, history)

**Output (ghi vào state):**
- `screening_result`: Clinical assessment chi tiết
- `severity`: "emergency" | "urgent" | "routine"
- `differential_diagnoses`: Danh sách chẩn đoán phân biệt
- `is_emergency`: true nếu xác nhận khẩn cấp
- `confidence_score`: Điểm tin cậy (gọi confidence_scorer)

**Screening Result Format:**

```python
{
    "clinical_assessment": "Bệnh nhân 55 tuổi, nam, đau bụng phải dưới 2 ngày, sốt nhẹ, chán ăn. Nghi ngờ viêm ruột thừa cấp.",
    "severity": "urgent",
    "recommended_flow": "prescription",  # hoặc "lab", "monitoring"
    "needs_prescription": True,
    "needs_lab": True,     # CBC, CRP
    "needs_monitoring": False,
    "emergency_indicators": [],  # Rỗng nếu không khẩn cấp
    "risk_factors": ["Tiểu đường type 2 — tăng nguy cơ nhiễm trùng"],
}
```

**Differential Diagnosis Format:**

```python
[
    {
        "diagnosis": "Acute Appendicitis",
        "icd10": "K35.80",
        "probability": 0.75,
        "supporting_evidence": ["RLQ pain", "fever", "anorexia", "rebound tenderness"],
        "against_evidence": [],
    },
    {
        "diagnosis": "Mesenteric Lymphadenitis",
        "icd10": "I88.0",
        "probability": 0.15,
        "supporting_evidence": ["RLQ pain", "fever"],
        "against_evidence": ["age >50", "no recent URI"],
    },
]
```

**Emergency Detection Keywords:**

```python
EMERGENCY_KEYWORDS_VI = [
    "đau ngực", "khó thở", "không thở được", "tê nửa người",
    "mất ý thức", "bất tỉnh", "chảy máu nhiều", "co giật",
    "đau ngực trái", "đau lan ra cánh tay", "đột ngột yếu nửa người",
    "méo miệng", "nói ngọng đột ngột", "mất thị lực đột ngột",
]

EMERGENCY_KEYWORDS_EN = [
    "chest pain", "difficulty breathing", "can't breathe", "numbness",
    "unconscious", "severe bleeding", "seizure", "stroke signs",
    "sudden weakness", "facial drooping", "slurred speech",
]
```

### 6.4 Proposer Agent

**File:** `services/ai-agent-service/app/agents/proposer_agent.py`

**Mục đích:** Tạo Order Recommendations chi tiết (thuốc, lab, monitoring protocol). Thay thế vai trò bác sĩ kê đơn ban đầu.

**FR tương ứng:** FR11 (Treatment Plan), FR12 (Drug Interaction), FR13 (Allergy Screening)

**Input:**
- `screening_result`: Clinical assessment từ Screening Agent
- `differential_diagnoses`: Danh sách chẩn đoán phân biệt
- Patient profile (medications, allergies, weight, age, renal/hepatic function)

**Output (ghi vào state):**
- `order_recommendations`: Danh sách đề xuất chi tiết
- `drug_interactions`: Kết quả kiểm tra tương tác thuốc
- `allergy_alerts`: Cảnh báo dị ứng

**Order Recommendation Format (Medication):**

```python
{
    "type": "medication",
    "drug_name": "Amoxicillin/Clavulanate",
    "brand_name": "Augmentin",
    "dosage": "875mg/125mg",
    "frequency": "2 lần/ngày",
    "duration": "7 ngày",
    "route": "oral",
    "quantity": 14,
    "refills": 0,
    "rationale": "First-line antibiotic cho suspected UTI ở bệnh nhân nữ. Phổ rộng cover E.coli và common uropathogens.",
    "contraindication_check": "PASSED",
    "allergy_check": "PASSED — Patient allergic to Penicillin nhưng đã confirm: reaction là mild rash (not anaphylaxis), Amoxicillin/Clavulanate acceptable với monitoring.",
    "drug_interaction_check": "PASSED — No significant interactions with Metformin.",
    "fhir_medication_request": { /* FHIR MedicationRequest resource */ },
}
```

**Order Recommendation Format (Lab):**

```python
{
    "type": "lab",
    "test_name": "Complete Blood Count (CBC) with Differential",
    "cpt_code": "85025",
    "urgency": "routine",
    "rationale": "Đánh giá WBC count để confirm infection. Elevated WBC support diagnosis of appendicitis.",
    "specimen_type": "blood",
    "fasting_required": False,
    "fhir_diagnostic_report": { /* FHIR DiagnosticReport resource */ },
}
```

**Quy trình xử lý:**

```
Screening Result
      │
      ▼
┌──────────────────┐
│ 1. Drug Database  │ → Tra cứu thuốc phù hợp (First Databank/Micromedex)
│    Lookup         │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ 2. Drug Interaction│ → Kiểm tra tương tác với current medications
│    Check (100%)   │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ 3. Allergy Screen │ → Kiểm tra dị ứng với patient allergies (100%)
│    (100%)         │
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ 4. Dosage Valid.  │ → Weight-based, renal/hepatic adjustments
└───────┬──────────┘
        │
        ▼
┌──────────────────┐
│ 5. Generate Order │ → Tạo Order Recommendation + FHIR resource
│    Recommendation │
└──────────────────┘
```

**Tools available cho Proposer Agent:**

| Tool | Mô tả | Bắt buộc |
|------|--------|----------|
| `drug_database_lookup` | Tra cứu database thuốc (First Databank) | Có |
| `drug_interaction_checker` | Kiểm tra tương tác thuốc | **BẮT BUỘC** (100%) |
| `allergy_checker` | Kiểm tra dị ứng | **BẮT BUỘC** (100%) |
| `clinical_guidelines_lookup` | Tra cứu hướng dẫn lâm sàng (IDSA, AHA, etc.) | Có |
| `fhir_formatter` | Format output theo FHIR R4 | Có |
| `dosage_calculator` | Tính liều dựa trên cân nặng, thận, gan | Có |

### 6.5 Critic Agent

**File:** `services/ai-agent-service/app/agents/critic_agent.py`

**Mục đích:** Adversarial validation — cố tình tìm lỗi trong recommendations của Proposer. Safety net lớp 1.

**FR tương ứng:** FR15 (Clinical Reasoning & Confidence), FR16 (AI Critic Validation)

**Input:**
- `order_recommendations`: Đề xuất từ Proposer Agent
- `screening_result`: Screening data để cross-reference
- `differential_diagnoses`: Chẩn đoán phân biệt
- Patient profile

**Output (ghi vào state):**
- `critic_validation`: Kết quả review
- `critic_approved`: true/false
- `critic_issues`: Danh sách vấn đề phát hiện

**Validation Checks:**

| Check | Mô tả | Severity |
|-------|--------|----------|
| Drug Interaction (lại) | Double-check tương tác thuốc | **CRITICAL** — block nếu phát hiện |
| Dosage Range | Liều nằm trong khoảng an toàn | **CRITICAL** |
| Contraindication | Chống chỉ định với bệnh nền | **CRITICAL** |
| Guideline Adherence | Tuân thủ hướng dẫn lâm sàng | HIGH |
| Diagnosis-Treatment Match | Thuốc phù hợp với chẩn đoán | HIGH |
| Hallucination Check | Cross-reference thuốc có tồn tại thật | HIGH |
| Completeness | Đủ thông tin (liều, frequency, duration) | MEDIUM |

**Critic Validation Format:**

```python
{
    "overall_decision": "APPROVED",  # APPROVED | REJECTED | NEEDS_REVISION
    "confidence_score": 92.5,
    "issues_found": [],
    "checks_performed": [
        {"check": "drug_interaction", "result": "PASSED", "details": "No interactions found"},
        {"check": "dosage_range", "result": "PASSED", "details": "875mg within therapeutic range"},
        {"check": "contraindication", "result": "PASSED", "details": "No contraindications"},
        {"check": "guideline_adherence", "result": "PASSED", "details": "IDSA guidelines compliant"},
        {"check": "hallucination", "result": "PASSED", "details": "Drug exists in FDA database"},
    ],
    "reasoning": "All safety checks passed. Recommendations align with clinical guidelines for suspected UTI. Drug selection appropriate, dosage correct, no interactions with patient's current Metformin.",
}
```

**Khi Critic REJECT:**

```python
{
    "overall_decision": "REJECTED",
    "issues_found": [
        {
            "severity": "CRITICAL",
            "check": "drug_interaction",
            "description": "Severe interaction between Warfarin (patient current med) and recommended Amoxicillin/Clavulanate — increases INR, bleeding risk",
            "recommendation": "Use alternative antibiotic: Nitrofurantoin (no warfarin interaction)",
        }
    ],
}
```

Khi rejected, graph quay lại Proposer Agent với `critic_issues` trong state → Proposer tạo recommendations mới dựa trên feedback.

---

## 7. LangGraph Workflow Graphs

### 7.1 Prescription Flow (MVP Priority)

**File:** `services/ai-agent-service/app/agents/graphs/prescription_flow.py`

**9 trạm — 3-Stage Order Lifecycle:**

```
┌────────┐    ┌────────────┐    ┌──────────┐    ┌──────────────┐
│ Intake  │───▶│ Screening   │───▶│ Proposal  │───▶│ Critic Review │
│ (T1)    │    │ (T2)        │    │ (T3)      │    │ (T4)         │
└────────┘    └────────────┘    └──────────┘    └──────┬───────┘
                                                       │
                                          ┌────────────┤
                                          │ APPROVED    │ REJECTED
                                          ▼             ▼
                                   ┌────────────┐  Quay lại T3
                                   │ Priority    │
                                   │ Route (T5)  │
                                   └──────┬─────┘
                                          │
                                          ▼
                                   ┌────────────┐   ◀── HUMAN INTERRUPT
                                   │ VN MD       │       (Tạo Draft Orders)
                                   │ Review (T6) │
                                   └──────┬─────┘
                                          │
                                          ▼
                                   ┌────────────┐
                                   │ Draft Order │
                                   │ Mgr (T7)   │
                                   └──────┬─────┘
                                          │
                                          ▼
                                   ┌────────────┐   ◀── HUMAN INTERRUPT
                                   │ US MD       │       (Approve/Reject)
                                   │ Review (T8) │
                                   └──────┬─────┘
                                          │
                                          ▼
                                   ┌────────────┐
                                   │ Convert to  │
                                   │ Actual (T9) │
                                   └──────┬─────┘
                                          │
                                          ▼
                                        END
```

**Implementation:**

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

def build_prescription_flow(checkpointer) -> StateGraph:
    graph = StateGraph(CareFlowState)

    # Nodes
    graph.add_node("intake", intake_node)
    graph.add_node("screening", screening_node)
    graph.add_node("proposal", proposal_node)
    graph.add_node("critic_review", critic_node)
    graph.add_node("priority_route", priority_route_node)
    graph.add_node("vn_md_review", vn_md_review_node)
    graph.add_node("draft_order_manager", draft_order_manager_node)
    graph.add_node("us_md_review", us_md_review_node)
    graph.add_node("convert_to_actual", convert_to_actual_node)

    # Edges
    graph.set_entry_point("intake")

    # Intake → Screening (luôn)
    graph.add_edge("intake", "screening")

    # Screening → check emergency
    graph.add_conditional_edges(
        "screening",
        lambda state: "emergency" if state["is_emergency"] else "proposal",
        {
            "emergency": END,      # Emergency → chuyển sang Emergency Flow
            "proposal": "proposal",
        }
    )

    # Proposal → Critic Review
    graph.add_edge("proposal", "critic_review")

    # Critic → APPROVED hoặc REJECTED (quay lại Proposal)
    graph.add_conditional_edges(
        "critic_review",
        lambda state: "approved" if state["critic_approved"] else "rejected",
        {
            "approved": "priority_route",
            "rejected": "proposal",  # Proposer nhận critic_issues và sửa
        }
    )

    # Priority → VN MD Review (HUMAN INTERRUPT)
    graph.add_edge("priority_route", "vn_md_review")

    # VN MD → Draft Order Manager
    graph.add_edge("vn_md_review", "draft_order_manager")

    # Draft Order Manager → US MD Review (HUMAN INTERRUPT)
    graph.add_edge("draft_order_manager", "us_md_review")

    # US MD → Convert hoặc Reject
    graph.add_conditional_edges(
        "us_md_review",
        lambda state: "approved" if state.get("usmd_approved") else "rejected",
        {
            "approved": "convert_to_actual",
            "rejected": END,
        }
    )

    # Convert → END
    graph.add_edge("convert_to_actual", END)

    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["vn_md_review", "us_md_review"],  # HUMAN INTERRUPT POINTS
    )
```

### 7.2 Emergency Flow

**File:** `services/ai-agent-service/app/agents/graphs/emergency_flow.py`

**6 trạm — <15 phút — KHÔNG cần MD approval:**

```
Intake → Screening → Emergency Detect → Proposal → Priority → ER Protocol → END
```

**Đặc điểm:**
- Không có human interrupt points
- Publish `care.case.escalated` event ngay lập tức
- ER Protocol node: hiển thị cảnh báo khẩn cấp + gọi 911 instructions + ER gần nhất
- Tất cả xử lý tự động, tối ưu tốc độ

### 7.3 Lab/Imaging Flow

**File:** `services/ai-agent-service/app/agents/graphs/lab_flow.py`

**9 trạm — Tương tự Prescription Flow nhưng:**
- Proposer Agent tạo lab order recommendations thay vì medication
- Output format: test types, panels, CPT codes, specimen type
- Convert to Actual: tạo lab order PDF + LabCorp/Quest integration
- Completion có thể chuyển sang Monitoring Flow nếu cần follow-up

### 7.4 Monitoring Flow

**File:** `services/ai-agent-service/app/agents/graphs/monitoring_flow.py`

**14 trạm — 3 entry points:**

```python
def build_monitoring_flow(checkpointer, entry_point: str):
    """
    entry_point:
    - "full": Từ T6, chạy đầy đủ 14 trạm
    - "post_prescription": Từ Luồng B completion, bắt đầu T9
    - "post_lab": Từ Luồng C completion, bắt đầu T9
    """
    graph = StateGraph(CareFlowState)

    if entry_point == "full":
        # Thêm T1-T8 (giống Prescription Flow)
        graph.add_node("intake", intake_node)
        # ... T2-T8
        graph.set_entry_point("intake")
    else:
        # Bắt đầu từ T9
        graph.set_entry_point("monitor_order")

    # T9-T14 (chung cho mọi entry point)
    graph.add_node("monitor_order", monitor_order_node)
    graph.add_node("setup_protocol", setup_protocol_node)
    graph.add_node("checkin_1", checkin_node)       # AI chatbot check-in tại 24h
    graph.add_node("checkin_2", checkin_node)       # 48h
    graph.add_node("checkin_3", checkin_node)       # 72h (nếu protocol yêu cầu)
    graph.add_node("final_review", final_review_node)  # HUMAN: MD review cuối
    graph.add_node("completion", completion_node)

    # Protocol setup xác định số check-in
    graph.add_edge("monitor_order", "setup_protocol")
    graph.add_edge("setup_protocol", "checkin_1")

    # Sau mỗi check-in: stable → next check-in, deterioration → escalate
    graph.add_conditional_edges(
        "checkin_1",
        route_after_checkin,
        {
            "stable": "checkin_2",
            "deterioration": "escalate",    # Quay lại care flow
            "complete": "final_review",     # Protocol chỉ cần 1 check-in
        }
    )
    # Tương tự cho checkin_2, checkin_3

    graph.add_edge("final_review", "completion")
    graph.add_edge("completion", END)
```

**Monitoring Protocol Types:**

| Protocol | Interval | Số check-in | Use case |
|----------|----------|-------------|----------|
| 24h High-risk | Mỗi 24 giờ | 3 lần | Triệu chứng mơ hồ, risk cao |
| 48h Standard | Mỗi 48 giờ | 2 lần | Post-medication monitoring |
| 72h Low-risk | Mỗi 72 giờ | 1 lần | Routine follow-up |

---

## 8. Vietnamese NLP Pipeline

### 8.1 Cultural Mapper

**File:** `services/ai-agent-service/app/nlp/cultural_mapper.py`

**Mục đích:** Ánh xạ biểu đạt văn hóa Việt Nam → thuật ngữ y khoa Western (FR97)

**Database Format (PostgreSQL JSONB):**

```python
CULTURAL_EXPRESSIONS = [
    {
        "expression": "bị nóng trong",
        "variants": ["nóng trong người", "nóng trong", "bị nóng"],
        "medical_meaning": "Internal inflammation/infection symptoms — elevated body temperature, systemic inflammatory response",
        "medical_terms": ["inflammation", "fever", "infection"],
        "context_clues": ["sốt", "mệt", "đau"],
        "confidence": 0.90,
        "region": "all",  # Northern + Southern
    },
    {
        "expression": "gió độc",
        "variants": ["bị gió", "trúng gió", "cảm gió"],
        "medical_meaning": "Fever with chills, body aches, upper respiratory symptoms — often viral illness",
        "medical_terms": ["fever", "chills", "myalgia", "URI"],
        "context_clues": ["ớn lạnh", "đau nhức", "sổ mũi"],
        "confidence": 0.85,
        "region": "all",
    },
    {
        "expression": "bị lạnh",
        "variants": ["bị lạnh vào người", "cảm lạnh"],
        "medical_meaning": "Common cold symptoms, hypothermia, or fever onset with chills",
        "medical_terms": ["common cold", "hypothermia", "chills"],
        "context_clues": ["ho", "sổ mũi", "đau họng"],
        "confidence": 0.80,
        "region": "all",
    },
    {
        "expression": "bốc hỏa",
        "variants": ["bốc hỏa", "lên cơn nóng"],
        "medical_meaning": "Hot flashes — vasomotor symptoms, often menopausal",
        "medical_terms": ["hot flashes", "vasomotor symptoms", "menopause"],
        "context_clues": ["tuổi", "mãn kinh", "đổ mồ hôi"],
        "confidence": 0.85,
        "region": "all",
    },
    {
        "expression": "yếu thận",
        "variants": ["thận yếu", "thận hư"],
        "medical_meaning": "Kidney weakness in traditional Vietnamese medicine — can indicate fatigue, sexual dysfunction, lower back pain, frequent urination",
        "medical_terms": ["fatigue", "lower back pain", "frequent urination", "erectile dysfunction"],
        "context_clues": ["mệt", "đau lưng", "tiểu nhiều"],
        "confidence": 0.75,
        "region": "all",
    },
    {
        "expression": "máu nóng",
        "variants": ["nóng máu", "máu nóng trong người"],
        "medical_meaning": "Blood heat — skin conditions, acne, rashes, irritability",
        "medical_terms": ["dermatitis", "acne", "urticaria", "irritability"],
        "context_clues": ["mẩn ngứa", "nổi mụn", "da đỏ"],
        "confidence": 0.80,
        "region": "all",
    },
    # ... 50+ expressions nữa
]
```

**Lookup Algorithm:**

```python
class CulturalMapper:
    def __init__(self, expression_repository):
        self.repo = expression_repository

    async def map_expressions(self, text: str) -> list[dict]:
        """Phát hiện và ánh xạ biểu đạt văn hóa trong text."""
        found = []

        # 1. Exact match (nhanh nhất)
        expressions = await self.repo.get_all_expressions()
        for expr in expressions:
            for variant in [expr["expression"]] + expr["variants"]:
                if variant.lower() in text.lower():
                    found.append({
                        "original": variant,
                        "medical_meaning": expr["medical_meaning"],
                        "medical_terms": expr["medical_terms"],
                        "confidence": expr["confidence"],
                    })

        # 2. Fuzzy match (cho typos, biến thể)
        if not found:
            found = await self._fuzzy_match(text, expressions)

        # 3. LLM-assisted interpretation (last resort — tốn token)
        if not found and self._likely_cultural_expression(text):
            found = await self._llm_interpret(text)

        return found
```

### 8.2 Code Switcher

**File:** `services/ai-agent-service/app/nlp/code_switcher.py`

**Mục đích:** Xử lý code-switching Vietnamese ↔ English mid-conversation (FR98)

**Ví dụ input:** "Con bị fever 3 ngày rồi, đau họng nuốt very difficult"

**Algorithm:**

```python
class CodeSwitcher:
    def detect_language(self, text: str) -> str:
        """Phát hiện ngôn ngữ: 'vi', 'en', hoặc 'mixed'."""
        vi_chars = set("àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđ")
        has_vi = any(c in vi_chars for c in text.lower())
        has_en = bool(re.search(r'\b[a-zA-Z]{3,}\b', text))

        if has_vi and has_en:
            return "mixed"
        elif has_vi:
            return "vi"
        return "en"

    def normalize(self, text: str) -> str:
        """Normalize mixed text để LLM hiểu tốt hơn."""
        language = self.detect_language(text)
        if language == "mixed":
            # Giữ nguyên — LLM (GPT-4) xử lý code-switching tốt
            # Chỉ thêm context hint cho LLM
            return f"[CODE-SWITCHING: Vietnamese-English] {text}"
        return text

    def maintain_context(self, messages: list[dict]) -> list[dict]:
        """Đảm bảo context được duy trì qua language switches."""
        # Track language preference qua conversation
        # Nếu patient chuyển từ VN sang EN, không reset context
        return messages
```

### 8.3 Medical Terminology

**File:** `services/ai-agent-service/app/nlp/medical_terminology.py`

**Mục đích:** Bidirectional translation Vietnamese ↔ English medical terms (FR99, FR100)

```python
MEDICAL_TERMS = {
    # Triệu chứng
    "đau đầu": "headache",
    "đau bụng": "abdominal pain",
    "sốt": "fever",
    "ho": "cough",
    "khó thở": "dyspnea",
    "buồn nôn": "nausea",
    "nôn": "vomiting",
    "tiêu chảy": "diarrhea",
    "táo bón": "constipation",
    "chóng mặt": "dizziness",
    "mệt mỏi": "fatigue",
    "phát ban": "rash",
    "ngứa": "pruritus",
    "đau ngực": "chest pain",
    "đau khớp": "joint pain",
    "sưng": "swelling/edema",

    # Bệnh lý
    "tiểu đường": "diabetes mellitus",
    "cao huyết áp": "hypertension",
    "hen suyễn": "asthma",
    "viêm phổi": "pneumonia",
    "viêm ruột thừa": "appendicitis",
    "sỏi thận": "kidney stones/nephrolithiasis",
    "nhiễm trùng đường tiểu": "urinary tract infection",

    # Thuốc (thường dùng)
    "thuốc hạ sốt": "antipyretic/acetaminophen",
    "thuốc giảm đau": "analgesic",
    "kháng sinh": "antibiotic",
    "thuốc ho": "cough suppressant",

    # Regional variants (Bắc vs Nam)
    "cảm cúm": "influenza",       # Bắc
    "cảm": "cold/influenza",      # Nam (shorter form)
    "bịnh": "disease/illness",    # Nam
    "bệnh": "disease/illness",   # Bắc
}
```

---

## 9. Confidence Scoring System

### 9.1 Thiết kế

**File:** `services/ai-agent-service/app/domain/services/confidence_scorer.py`

**4 Factors với Weighted Average:**

```python
class ConfidenceScorer:
    WEIGHTS = {
        "llm_confidence": 0.40,       # 40%
        "guideline_match": 0.30,      # 30%
        "data_completeness": 0.20,    # 20%
        "historical_accuracy": 0.10,  # 10%
    }

    async def calculate(
        self,
        screening_result: dict,
        order_recommendations: list[dict],
        intake_data: dict,
        patient_id: str,
    ) -> tuple[float, dict]:
        """Tính confidence score. Trả về (score, breakdown)."""

        # Factor 1: LLM Confidence (40%)
        # — Dựa trên token probabilities và perplexity từ LLM response
        llm_score = self._calculate_llm_confidence(screening_result)

        # Factor 2: Clinical Guidelines Match (30%)
        # — Cross-reference recommendations với clinical guidelines databases
        guideline_score = await self._check_guideline_adherence(
            order_recommendations, screening_result
        )

        # Factor 3: Data Completeness (20%)
        # — Intake data có đủ thông tin cho diagnosis không
        completeness_score = self._assess_data_completeness(intake_data)

        # Factor 4: Historical Accuracy (10%)
        # — Accuracy của AI cho similar cases trong quá khứ
        historical_score = await self._get_historical_accuracy(
            patient_id, screening_result
        )

        # Weighted average
        total = (
            llm_score * self.WEIGHTS["llm_confidence"]
            + guideline_score * self.WEIGHTS["guideline_match"]
            + completeness_score * self.WEIGHTS["data_completeness"]
            + historical_score * self.WEIGHTS["historical_accuracy"]
        )

        breakdown = {
            "llm_confidence": llm_score,
            "guideline_match": guideline_score,
            "data_completeness": completeness_score,
            "historical_accuracy": historical_score,
            "total": total,
        }

        return total, breakdown
```

### 9.2 Thresholds & Actions

| Score | Level | Action |
|-------|-------|--------|
| 85-100% | **HIGH** | Proceed — recommendations đáng tin cậy |
| 70-84% | **MEDIUM** | Flag cho MD — MD cần review cẩn thận |
| <70% | **LOW** | Escalate — AI recommendation chỉ mang tính tham khảo, MD quyết định |

### 9.3 Feedback Loop

MD approval/rejection được log và sử dụng để cập nhật `historical_accuracy`:

```python
async def record_feedback(self, case_id: str, md_decision: str, md_corrections: dict):
    """Ghi nhận feedback từ MD để cải thiện accuracy."""
    await self.feedback_repo.save({
        "case_id": case_id,
        "ai_recommendation": await self.get_recommendation(case_id),
        "md_decision": md_decision,  # "approved", "modified", "rejected"
        "md_corrections": md_corrections,
        "timestamp": datetime.utcnow(),
    })
```

---

## 10. Kafka Event Integration

### 10.1 Events Produced bởi ai-agent-service

| Event Type | Khi nào | Payload chính |
|------------|---------|---------------|
| `care.case.created` | Sau khi Screening hoàn thành | case_id, patient_id, severity, flow_type |
| `order.recommendation.generated` | Sau khi Proposer + Critic approve | case_id, recommendations[], confidence_score |
| `care.case.escalated` | Emergency detected hoặc low confidence | case_id, escalation_reason, severity |

### 10.2 Events Consumed bởi ai-agent-service

| Event Type | Từ service nào | Action |
|------------|---------------|--------|
| `care.case.created` | clinical-workflow-service | Trigger agent workflow (nếu case tạo từ service khác) |

### 10.3 Event Schema

```python
# events/schemas.py
from pydantic import BaseModel
from datetime import datetime
import uuid

class KafkaEventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str                     # "care.case.created"
    event_version: str = "1.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    source_service: str = "ai-agent-service"
    correlation_id: str                 # case_id — ordered per patient case
    tenant: dict                        # {"organization_id": str, "patient_id": str}
    payload: dict                       # Event-specific data
    metadata: dict                      # {"actor_id": str, "actor_role": str}
```

### 10.4 Producer Configuration

```python
# events/producers.py
from confluent_kafka import Producer

class KafkaEventProducer:
    def __init__(self, settings: Settings):
        self.producer = Producer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "acks": "all",              # Đợi tất cả replicas confirm
            "retries": 5,              # Retry 5 lần
            "enable.idempotence": True, # Exactly-once semantics
            "max.in.flight.requests.per.connection": 1,  # Đảm bảo ordering
        })

    async def publish(self, topic: str, event: KafkaEventEnvelope):
        """Publish event với case_id làm partition key."""
        self.producer.produce(
            topic=topic,
            key=event.correlation_id.encode(),  # Partition key = case_id
            value=event.model_dump_json().encode(),
        )
        self.producer.flush()
```

### 10.5 Consumer Configuration

```python
# events/consumers.py
from confluent_kafka import Consumer

class KafkaEventConsumer:
    def __init__(self, settings: Settings):
        self.consumer = Consumer({
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": "ai-agent-service-group",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,  # Manual commit sau khi xử lý thành công
        })

    async def start(self):
        self.consumer.subscribe(["care-flow-events"])
        # Event processing loop...
```

---

## 11. Database Schema

### 11.1 Tables thuộc sở hữu ai-agent-service

**agent_sessions:**
```sql
CREATE TABLE agent_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID NOT NULL,
    case_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    agent_type VARCHAR(50) NOT NULL,   -- 'intake', 'screening', 'proposer', 'critic'
    state_snapshot JSONB,               -- CareFlowState snapshot
    messages JSONB DEFAULT '[]'::jsonb, -- Chat message history
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'interrupted'
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- RLS Policy
ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY agent_sessions_tenant ON agent_sessions
    USING (organization_id = current_setting('app.organization_id')::uuid);

-- Indexes
CREATE INDEX idx_agent_sessions_case_id ON agent_sessions(case_id);
CREATE INDEX idx_agent_sessions_patient_id ON agent_sessions(patient_id);
CREATE INDEX idx_agent_sessions_status ON agent_sessions(status) WHERE status = 'active';
```

**screening_results:**
```sql
CREATE TABLE screening_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL UNIQUE,
    patient_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    severity VARCHAR(20) NOT NULL,      -- 'emergency', 'urgent', 'routine'
    clinical_assessment TEXT NOT NULL,
    differential_diagnoses JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence_score DECIMAL(5,2),
    confidence_breakdown JSONB,
    is_emergency BOOLEAN DEFAULT false,
    raw_llm_response JSONB,            -- Encrypted LLM response (audit)
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE screening_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY screening_results_tenant ON screening_results
    USING (organization_id = current_setting('app.organization_id')::uuid);
```

**phi_mappings:**
```sql
CREATE TABLE phi_mappings (
    mapping_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id UUID NOT NULL,
    encrypted_mapping BYTEA NOT NULL,   -- AES-256 encrypted JSON mapping
    phi_types_found TEXT[] NOT NULL,     -- ['name', 'dob', 'phone']
    created_at TIMESTAMPTZ DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL     -- TTL: 24 hours default
);

CREATE INDEX idx_phi_mappings_case_id ON phi_mappings(case_id);
CREATE INDEX idx_phi_mappings_expires ON phi_mappings(expires_at);
```

**cultural_expressions:**
```sql
CREATE TABLE cultural_expressions (
    expression_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vietnamese_text VARCHAR(200) NOT NULL UNIQUE,
    variants JSONB DEFAULT '[]'::jsonb,
    medical_meaning TEXT NOT NULL,
    medical_terms TEXT[] NOT NULL,
    context_clues JSONB DEFAULT '[]'::jsonb,
    confidence DECIMAL(3,2) NOT NULL,
    region VARCHAR(20) DEFAULT 'all',   -- 'all', 'northern', 'southern'
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_cultural_expressions_text ON cultural_expressions
    USING gin(to_tsvector('simple', vietnamese_text));
```

### 11.2 Alembic Migration

```python
# alembic/versions/001_initial_schema.py
def upgrade():
    # Create all tables above
    # Enable RLS
    # Create indexes
    # Seed cultural_expressions with initial 50+ expressions

def downgrade():
    # Drop all tables
```

---

## 12. API Endpoints

### 12.1 Chat API

**POST /api/v1/chat**

```python
# Request
{
    "message": "Tôi bị đau bụng 2 ngày rồi",
    "session_id": null,          # null = new session
    "language": "vi"             # "vi", "en", "auto"
}

# Response
{
    "data": {
        "response": "Xin chào! Tôi là trợ lý y tế AI. Bạn có thể mô tả chi tiết hơn về cơn đau bụng không? Đau ở vị trí nào?",
        "session_id": "uuid",
        "agent_state": "intake",     # Agent hiện tại đang xử lý
        "is_complete": false,
        "detected_language": "vi",
    },
    "meta": {
        "request_id": "uuid",
        "timestamp": "2026-02-26T10:30:00Z"
    }
}
```

**WebSocket /api/v1/chat/ws** (real-time chat)

```python
# Connect: ws://host/api/v1/chat/ws?session_id=uuid&token=jwt
# Client sends: {"message": "text"}
# Server sends: {"response": "text", "agent_state": "intake", "typing": false}
```

### 12.2 Screening API

**POST /api/v1/screening/start**

```python
# Request
{
    "patient_id": "uuid",
    "initial_complaint": "Đau bụng bên phải dưới 2 ngày"
}

# Response (201 Created)
{
    "data": {
        "case_id": "uuid",
        "session_id": "uuid",
        "status": "in_progress",
        "flow_type": null        # Xác định sau screening
    },
    "meta": { "request_id": "uuid", "timestamp": "..." }
}
```

**GET /api/v1/screening/{case_id}/status**

```python
# Response
{
    "data": {
        "case_id": "uuid",
        "status": "awaiting_vn_md_review",  # in_progress, awaiting_vn_md_review, awaiting_us_md_review, completed
        "current_station": 6,
        "flow_type": "prescription",
        "confidence_score": 87.5,
        "severity": "urgent",
    },
    "meta": { ... }
}
```

**GET /api/v1/screening/{case_id}/results**

```python
# Response
{
    "data": {
        "screening_result": { /* clinical assessment */ },
        "differential_diagnoses": [ /* danh sách */ ],
        "order_recommendations": [ /* nếu đã qua Proposer */ ],
        "critic_validation": { /* nếu đã qua Critic */ },
        "confidence_score": 87.5,
        "confidence_breakdown": { /* chi tiết */ },
    },
    "meta": { ... }
}
```

**POST /api/v1/screening/{case_id}/resume** (Resume sau human interrupt)

```python
# Request (từ MD dashboard sau khi review)
{
    "action": "approve",          # "approve", "modify", "reject"
    "draft_orders": [ /* nếu VN MD tạo draft */ ],
    "modifications": { /* nếu MD sửa */ },
    "reviewer_id": "uuid",
    "reviewer_role": "vnmd"       # "vnmd", "usmd"
}

# Response
{
    "data": {
        "status": "resumed",
        "next_station": 7,
    }
}
```

---

## 13. Security & PHI Protection

### 13.1 Zero-Trust Architecture

```
Internet ──▶ Istio Ingress Gateway ──▶ ai-agent-service
                (TLS 1.3)              (mTLS between services)
                (JWT validation)        (RBAC per endpoint)
                (Rate limiting)         (PHI de-identification)
                                        (Audit logging 100%)
```

### 13.2 JWT Validation

```python
# core/security.py
from jose import jwt, JWTError

async def validate_jwt(token: str) -> dict:
    """Validate Cognito JWT token."""
    # 1. Fetch JWKS from Cognito
    # 2. Verify signature
    # 3. Check expiration
    # 4. Extract claims (user_id, role, organization_id)
    payload = jwt.decode(token, key, algorithms=["RS256"])
    return {
        "user_id": payload["sub"],
        "role": payload["custom:role"],       # patient, vnmd, usmd, admin
        "organization_id": payload["custom:org_id"],
    }
```

### 13.3 RBAC per Endpoint

| Endpoint | Patient | VN MD | US MD | Admin |
|----------|---------|-------|-------|-------|
| POST /chat | ✅ | ❌ | ❌ | ❌ |
| POST /screening/start | ✅ | ❌ | ❌ | ✅ |
| GET /screening/{id}/results | ✅ (own) | ✅ (assigned) | ✅ (assigned) | ✅ |
| POST /screening/{id}/resume | ❌ | ✅ | ✅ | ❌ |

### 13.4 Audit Logging Middleware

```python
# middleware/audit.py
class AuditMiddleware:
    async def __call__(self, request, call_next):
        # Log mọi request
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "api.request",
            "method": request.method,
            "path": request.url.path,
            "actor_id": request.state.user_id,
            "actor_role": request.state.user_role,
            "actor_ip": request.client.host,
            "correlation_id": request.headers.get("X-Compass-Correlation-Id"),
            "service": "ai-agent-service",
        }
        response = await call_next(request)
        audit_entry["status_code"] = response.status_code
        await publish_audit_event(audit_entry)
        return response
```

### 13.5 Quy tắc PHI bất di bất dịch

1. **KHÔNG BAO GIỜ** gửi PHI tới external LLM APIs
2. **KHÔNG BAO GIỜ** log PHI trong error messages hoặc application logs
3. **KHÔNG BAO GIỜ** trả PHI trong API error responses
4. **LUÔN LUÔN** de-identify trước LLM call
5. **LUÔN LUÔN** audit log mọi PHI access
6. **LUÔN LUÔN** mã hóa PHI mappings trong database (AES-256)
7. **LUÔN LUÔN** đặt TTL cho PHI mappings (24 giờ default)

---

## 14. Error Handling & Resilience

### 14.1 Exception Hierarchy

```python
# core/exceptions.py

class CompassBaseException(Exception):
    """Base exception cho toàn bộ service."""
    def __init__(self, message: str, code: str, details: dict = None):
        self.message = message
        self.code = code
        self.details = details or {}

class ValidationError(CompassBaseException):
    """Input validation failures."""
    pass

class AuthorizationError(CompassBaseException):
    """RBAC violations."""
    pass

class PHIAccessError(CompassBaseException):
    """PHI access policy violations — BLOCK ngay."""
    pass

class ClinicalSafetyError(CompassBaseException):
    """HIGHEST PRIORITY — patient safety risk.
    Trigger immediate MD notification."""
    pass

class LLMError(CompassBaseException):
    """LLM call failures."""
    pass

class LLMTimeoutError(LLMError):
    pass

class LLMRateLimitError(LLMError):
    pass

class LLMHallucinationError(LLMError):
    """Phát hiện hallucination trong LLM response."""
    pass
```

### 14.2 Global Exception Handler

```python
# main.py
@app.exception_handler(CompassBaseException)
async def compass_exception_handler(request, exc):
    status_map = {
        "ValidationError": 400,
        "AuthorizationError": 403,
        "PHIAccessError": 403,
        "ClinicalSafetyError": 500,
        "LLMError": 503,
    }
    status_code = status_map.get(type(exc).__name__, 500)

    # ClinicalSafetyError → immediate MD notification
    if isinstance(exc, ClinicalSafetyError):
        await notify_on_call_md(exc)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,  # KHÔNG chứa PHI
                "request_id": request.state.request_id,
            }
        }
    )
```

### 14.3 Circuit Breaker

```python
# LLM Gateway đã tích hợp circuit breaker:
# - 5 failures liên tiếp → circuit OPEN
# - Đợi 60 giây → circuit HALF-OPEN
# - 3 test requests thành công → circuit CLOSE
# - Khi OPEN: fail fast, không gọi LLM → trả error ngay
```

### 14.4 Graceful Degradation

| Tình huống | Xử lý |
|-----------|-------|
| LLM primary (GPT-4) down | Fallback sang Claude (backup) |
| Cả GPT-4 và Claude down | Queue case cho human MD review |
| Emergency + LLM down | Immediate escalation tới US MD (bypass AI) |
| Kafka producer fail | Dead letter queue → retry sau |
| Database down | Return cached data (Redis) + flag degraded |
| PHI de-identification fail | **BLOCK LLM call** — không bao giờ gửi PHI |

---

## 15. Testing Strategy

### 15.1 Unit Tests

**Mỗi component có unit test riêng:**

```python
# tests/unit/test_intake_agent.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_llm_gateway():
    gateway = AsyncMock()
    gateway.generate.return_value = LLMResponse(
        content="Xin chào! Bạn có thể mô tả triệu chứng?",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        finish_reason="stop",
    )
    return gateway

async def test_intake_collects_symptoms(mock_llm_gateway):
    """Intake Agent thu thập đầy đủ triệu chứng."""
    state = create_test_state(messages=[
        HumanMessage(content="Tôi bị đau bụng 2 ngày rồi")
    ])
    result = await intake_node(state, llm_gateway=mock_llm_gateway)
    assert result["detected_language"] == "vi"

async def test_intake_detects_emergency():
    """Intake Agent phát hiện triệu chứng khẩn cấp."""
    state = create_test_state(messages=[
        HumanMessage(content="Tôi bị đau ngực rất nặng, khó thở")
    ])
    result = await intake_node(state)
    assert result["is_emergency"] is True
```

### 15.2 LLM Mocking

```python
# tests/conftest.py
@pytest.fixture
def mock_llm_responses():
    """Predefined LLM responses cho deterministic testing."""
    return {
        "screening": LLMResponse(
            content=json.dumps({
                "severity": "urgent",
                "clinical_assessment": "Suspected acute appendicitis",
                "differential_diagnoses": [...],
            }),
            model="gpt-4",
            usage={...},
            finish_reason="stop",
        ),
        "proposal": LLMResponse(...),
        "critic": LLMResponse(...),
    }
```

### 15.3 Integration Tests (Testcontainers)

```python
# tests/integration/test_prescription_flow.py
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.kafka import KafkaContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture(scope="session")
def kafka():
    with KafkaContainer() as kf:
        yield kf

async def test_full_prescription_flow(postgres, kafka, mock_llm_responses):
    """Test toàn bộ Prescription Flow từ intake đến completion."""
    # 1. Start screening
    response = await client.post("/api/v1/screening/start", json={
        "patient_id": test_patient_id,
        "initial_complaint": "Đau bụng phải dưới",
    })
    case_id = response.json()["data"]["case_id"]

    # 2. Simulate chat messages
    await client.post("/api/v1/chat", json={
        "message": "Đau 2 ngày, sốt nhẹ, chán ăn",
        "session_id": response.json()["data"]["session_id"],
    })

    # 3. Verify screening completed
    status = await client.get(f"/api/v1/screening/{case_id}/status")
    assert status.json()["data"]["status"] == "awaiting_vn_md_review"

    # 4. Resume with VN MD review
    await client.post(f"/api/v1/screening/{case_id}/resume", json={
        "action": "approve",
        "reviewer_role": "vnmd",
    })

    # 5. Verify Kafka events published
    events = consume_events(kafka, "care-flow-events")
    assert any(e["event_type"] == "care.case.created" for e in events)
    assert any(e["event_type"] == "order.recommendation.generated" for e in events)
```

### 15.4 Vietnamese NLP Tests

```python
# tests/unit/test_cultural_mapper.py
async def test_cultural_expression_mapping():
    mapper = CulturalMapper(mock_repo)
    result = await mapper.map_expressions("Tôi bị nóng trong người")
    assert len(result) == 1
    assert result[0]["original"] == "nóng trong"
    assert "inflammation" in result[0]["medical_terms"]

async def test_code_switching():
    switcher = CodeSwitcher()
    lang = switcher.detect_language("Con bị fever 3 ngày rồi")
    assert lang == "mixed"
```

### 15.5 Security Tests

```python
async def test_phi_never_sent_to_llm():
    """Verify PHI không bao giờ xuất hiện trong LLM request."""
    # Intercept outgoing LLM calls
    # Assert no PHI patterns in request body

async def test_rbac_patient_cannot_resume():
    """Patient không thể resume screening (chỉ MD mới được)."""
    response = await client.post(
        f"/api/v1/screening/{case_id}/resume",
        headers={"Authorization": f"Bearer {patient_token}"},
        json={"action": "approve"},
    )
    assert response.status_code == 403
```

### 15.6 Test Coverage Targets

| Component | Coverage Target |
|-----------|----------------|
| Agents (intake, screening, proposer, critic) | >90% |
| LLM Gateway | >95% |
| PHI De-identification | **100%** (safety-critical) |
| NLP Pipeline | >90% |
| Confidence Scorer | >90% |
| API Endpoints | >85% |
| Kafka Events | >85% |

---

## 16. Thứ tự triển khai

### Phase 1 — Foundation

**Mục tiêu:** Xây dựng nền tảng cho ai-agent-service.

| # | Task | Dependencies | File chính |
|---|------|-------------|------------|
| 1 | Project scaffold | Không | Cấu trúc thư mục |
| 2 | `pyproject.toml` + install dependencies | Task 1 | `pyproject.toml` |
| 3 | `config.py` + `.env` | Task 2 | `app/config.py` |
| 4 | **`state.py`** — CareFlowState schema | Task 2 | `app/agents/state.py` |
| 5 | Database models + Alembic migrations | Task 3 | `app/domain/models/` |
| 6 | **`phi_deidentifier.py`** — PHI pipeline | Task 3 | `app/domain/services/phi_deidentifier.py` |
| 7 | **`llm_gateway.py`** — LLM integration | Task 3, 6 | `app/domain/services/llm_gateway.py` |
| 8 | `main.py` + middleware + health check | Task 3 | `app/main.py` |
| 9 | Kafka producer/consumer setup | Task 3 | `app/events/` |
| 10 | Docker + docker-compose | Task 8 | `Dockerfile`, `docker-compose.yml` |

### Phase 2 — Core Agents

**Mục tiêu:** Implement 5 agents + NLP pipeline.

| # | Task | Dependencies | File chính |
|---|------|-------------|------------|
| 11 | Agent tools (patient_lookup, drug_interaction, etc.) | Phase 1 | `app/agents/tools/` |
| 12 | Agent prompts (intake, screening, proposer, critic) | Phase 1 | `app/agents/prompts/` |
| 13 | **Vietnamese NLP Pipeline** | Phase 1 | `app/nlp/` |
| 14 | Cultural expressions seed data | Task 13 | Alembic migration |
| 15 | **Intake Agent** | Task 7, 11, 12, 13 | `app/agents/intake_agent.py` |
| 16 | **Screening Agent** + confidence_scorer | Task 7, 11, 12 | `app/agents/screening_agent.py` |
| 17 | **Proposer Agent** | Task 7, 11, 12 | `app/agents/proposer_agent.py` |
| 18 | **Critic Agent** | Task 7, 11, 12 | `app/agents/critic_agent.py` |
| 19 | Supervisor Agent (routing) | Task 15-18 | `app/agents/supervisor.py` |

### Phase 3 — MVP Care Flow

**Mục tiêu:** Prescription Flow hoàn chỉnh end-to-end.

| # | Task | Dependencies | File chính |
|---|------|-------------|------------|
| 20 | **Prescription Flow graph** | Phase 2 | `app/agents/graphs/prescription_flow.py` |
| 21 | Human interrupt points (VN MD, US MD) | Task 20 | LangGraph checkpointer config |
| 22 | Kafka event publishing trong flow | Task 9, 20 | `app/events/producers.py` |
| 23 | Priority routing logic | Task 20 | Trong prescription_flow.py |

### Phase 4 — API & Security

**Mục tiêu:** REST API + WebSocket + security đầy đủ.

| # | Task | Dependencies | File chính |
|---|------|-------------|------------|
| 24 | Chat API endpoint | Phase 3 | `app/api/v1/routes/chat.py` |
| 25 | Screening API endpoints | Phase 3 | `app/api/v1/routes/screening.py` |
| 26 | WebSocket chat | Task 24 | Trong chat.py |
| 27 | JWT validation (Cognito) | Phase 1 | `app/core/security.py` |
| 28 | RBAC middleware | Task 27 | `app/core/security.py` |
| 29 | Audit logging middleware | Phase 1 | `app/middleware/audit.py` |

### Phase 5 — Remaining Flows

**Mục tiêu:** 3 care flows còn lại.

| # | Task | Dependencies | File chính |
|---|------|-------------|------------|
| 30 | Emergency Flow graph | Phase 3 | `app/agents/graphs/emergency_flow.py` |
| 31 | Lab/Imaging Flow graph | Phase 3 | `app/agents/graphs/lab_flow.py` |
| 32 | Monitoring Flow graph | Phase 3 | `app/agents/graphs/monitoring_flow.py` |

### Phase 6 — Testing & Deployment

**Mục tiêu:** Test suite hoàn chỉnh + production-ready.

| # | Task | Dependencies | File chính |
|---|------|-------------|------------|
| 33 | Unit tests cho mỗi agent | Phase 2 | `tests/unit/` |
| 34 | Unit tests cho LLM Gateway, PHI | Phase 1 | `tests/unit/` |
| 35 | Integration tests (testcontainers) | Phase 4 | `tests/integration/` |
| 36 | NLP tests | Phase 2 | `tests/unit/` |
| 37 | Security tests | Phase 4 | `tests/unit/` |
| 38 | Dockerfile optimize (multi-stage) | Phase 4 | `Dockerfile` |
| 39 | Kubernetes manifests | Task 38 | `infrastructure/kubernetes/` |
| 40 | Istio config (mTLS, rate limiting) | Task 39 | `infrastructure/istio/` |

---

## Phụ lục A: Sơ đồ luồng dữ liệu tổng thể

```
Patient (Vietnamese-American)
    │
    │ Chat message (Vietnamese/English/Mixed)
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI AGENT SERVICE                          │
│                                                              │
│  Message ──▶ NLP Pipeline ──▶ De-identify PHI               │
│                    │                   │                      │
│                    ▼                   ▼                      │
│              Cultural Mapper    PHI Deidentifier             │
│              Code Switcher      [REF-xxx] tokens             │
│                    │                   │                      │
│                    ▼                   ▼                      │
│              ┌──────────┐      ┌──────────────┐             │
│              │  INTAKE   │────▶│  LLM GATEWAY  │             │
│              │  Agent    │     │  (GPT-4/Claude)│             │
│              └──────┬───┘     └──────────────┘             │
│                     │                                        │
│                     ▼                                        │
│              ┌──────────┐                                    │
│              │SCREENING  │ → severity, differential          │
│              │  Agent    │ → confidence score                │
│              └──────┬───┘                                    │
│                     │                                        │
│                     ▼                                        │
│              ┌──────────┐                                    │
│              │ PROPOSER  │ → order recommendations           │
│              │  Agent    │ → drug checks, allergy checks    │
│              └──────┬───┘                                    │
│                     │                                        │
│                     ▼                                        │
│              ┌──────────┐                                    │
│              │  CRITIC   │ → validated/rejected              │
│              │  Agent    │ → safety net layer 1             │
│              └──────┬───┘                                    │
│                     │                                        │
│                     ▼                                        │
│              Kafka Event: order.recommendation.generated     │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
              ┌──────────────┐
              │ VN MD Review  │ → Tạo Draft Orders (safety net layer 2)
              └──────┬───────┘
                     │
                     ▼
              ┌──────────────┐
              │ US MD Approve │ → Ký duyệt (safety net layer 3)
              └──────┬───────┘
                     │
                     ▼
              Actual Order → EMR / Pharmacy / Lab
```

---

## Phụ lục B: FR Coverage Map

| FR | Mô tả | Agent/Component |
|----|-------|----------------|
| FR9 | Symptom Intake with Contextual Follow-up | Intake Agent |
| FR10 | Clinical Screening & Differential Diagnosis | Screening Agent |
| FR11 | Treatment Plan Recommendations | Proposer Agent |
| FR12 | Drug Interaction Checking | Proposer Agent → drug_interaction tool |
| FR13 | Allergy Screening | Proposer Agent → allergy_checker tool |
| FR14 | Emergency Symptom Detection | Screening Agent → emergency_detector tool |
| FR15 | Clinical Reasoning & Confidence Scores | Confidence Scorer + Critic Agent |
| FR16 | AI Critic Agent Validation | Critic Agent |
| FR97 | Cultural Health Expression Recognition | NLP: Cultural Mapper |
| FR98 | Code-Switching Context Maintenance | NLP: Code Switcher |
| FR99 | Natural Vietnamese Responses | Agent prompts + NLP pipeline |
| FR100 | Culturally-Appropriate Medical Explanations | Agent prompts + Cultural Mapper |

---

> **Ghi chú cuối:** Tài liệu này là blueprint cho `ai-agent-service`. Các service khác (patient-service, clinical-workflow-service, prescription-service, etc.) sẽ cần blueprint riêng. Architecture tổng thể đã được document trong `_bmad-output/planning-artifacts/architecture.md`.
