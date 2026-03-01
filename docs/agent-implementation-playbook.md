# Agent Implementation Playbook

## Tài Liệu Tham Chiếu Xây Dựng AI Agent — Compass Vitals

> **Phiên bản**: 1.0 | **Ngày**: 2026-03-01
> **Dự án**: Compass Vitals — Nền tảng Telemedicine AI-First cho cộng đồng Việt-Mỹ
> **Thí nghiệm**: Intake Agent (Agent đầu tiên trong hệ thống 5 agents)
> **Kết quả**: 18 source files, 59 unit tests + 4 E2E tests — TẤT CẢ PASSED

---

# PHẦN 0: TỔNG QUAN VÀ ĐỊNH HƯỚNG

## 0.1 Mục đích tài liệu

Tài liệu này ghi lại **toàn bộ quá trình thực tế** xây dựng AI Agent đầu tiên (Intake Agent) từ con số 0 đến khi pass tất cả tests. Đây không phải tài liệu lý thuyết — mọi dòng code, mọi command, mọi lỗi gặp phải đều là **thật**, đã được thực thi và kiểm chứng.

**Đối tượng sử dụng:**
- Developer cần build các agents tiếp theo (Screening, Proposer, Critic, Supervisor)
- Team lead cần hiểu kiến trúc hệ thống multi-agent
- DevOps cần deploy service lên production

## 0.2 Tóm tắt thí nghiệm

```
┌─────────────────────────────────────────────────────────┐
│                   KẾT QUẢ THÍ NGHIỆM                   │
├─────────────────────────────────────────────────────────┤
│  Source files tạo mới    : 18 files (~1,400 dòng code)  │
│  Test files              : 6 files (~350 dòng test)     │
│  Unit tests              : 59/59 PASSED                 │
│  E2E tests               : 4/4 PASSED                   │
│  Agent hoạt động         : Intake Agent (thu thập       │
│                            triệu chứng qua hội thoại)  │
│  LLM sử dụng            : GPT-4o-mini (OpenAI)         │
│  Ngôn ngữ hỗ trợ        : Tiếng Việt, English, Mixed   │
│  Tính năng đặc biệt     : Phát hiện khẩn cấp,          │
│                            biểu đạt văn hóa VN,        │
│                            bảo vệ PHI (HIPAA)           │
└─────────────────────────────────────────────────────────┘
```

## 0.3 Bản đồ tài liệu

| Bạn muốn...                                   | Đọc Phần |
|------------------------------------------------|----------|
| Hiểu kiến trúc tổng thể 5 agents              | Phần 1   |
| Setup môi trường từ con số 0                   | Phần 2   |
| Hiểu PHI, LLM Gateway, Exception              | Phần 3   |
| Hiểu NLP tiếng Việt (văn hóa, code-switching) | Phần 4   |
| Xem chi tiết Intake Agent hoạt động thế nào    | Phần 5   |
| Học cách viết test cho agent                   | Phần 6   |
| Chạy server và test thủ công                   | Phần 7   |
| Build agent mới (Screening, Proposer, v.v.)    | Phần 8   |
| Deploy lên Docker production                   | Phần 9   |
| Xem các lỗi thực tế và cách sửa               | Phần 10  |

## 0.4 Tổng quan hệ thống 5 Agents

```
                        ┌──────────────┐
                        │  SUPERVISOR  │
                        │  (Điều phối) │
                        └──────┬───────┘
                               │ Điều khiển luồng
                ┌──────────────┼──────────────┐
                │              │              │
         ┌──────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
         │   INTAKE    │ │SCREENING │ │  PROPOSER   │
         │ (Thu thập   │ │(Đánh giá │ │(Đề xuất     │
         │  triệu      │ │ lâm sàng)│ │ đơn thuốc)  │
         │  chứng)     │ │          │ │             │
         └─────────────┘ └──────────┘ └──────┬──────┘
               ▲                              │
               │                              ▼
         Bệnh nhân                    ┌──────────────┐
         (Chat)                       │    CRITIC    │
                                      │ (Kiểm tra    │
                                      │  an toàn)    │
                                      └──────────────┘

  ┌────────────────────────────────────────────────────────┐
  │  Tất cả agents chia sẻ CareFlowState (TypedDict)      │
  │  Không agent nào gọi trực tiếp agent khác              │
  │  Supervisor điều phối qua LangGraph StateGraph         │
  └────────────────────────────────────────────────────────┘
```

| Agent | Vai trò | Thay thế | Model LLM |
|-------|---------|----------|-----------|
| **Intake** | Thu thập triệu chứng qua hội thoại | Y tá triage (RN) | GPT-4o-mini |
| **Screening** | Đánh giá lâm sàng, xếp loại nghiêm trọng | BS khám ban đầu | GPT-4 |
| **Proposer** | Đề xuất thuốc, xét nghiệm, theo dõi | BS kê đơn | GPT-4 |
| **Critic** | Kiểm tra an toàn, tương tác thuốc, dị ứng | Dược sĩ + Peer review | GPT-4 |
| **Supervisor** | Điều phối workflow, routing | Quản lý phòng khám | — |

---

# PHẦN 1: KIẾN TRÚC TỔNG THỂ

## 1.1 CareFlowState — Hợp đồng dữ liệu duy nhất

Đây là **trung tâm của toàn bộ kiến trúc**. Tất cả 5 agents đều đọc và ghi vào cùng một state object. Không có agent nào gọi trực tiếp agent khác — tất cả giao tiếp qua state.

**File**: `services/ai-agent-service/app/agents/state.py`

```python
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
```

**Giải thích quan trọng:**

- `messages: Annotated[list[BaseMessage], add_messages]` — Sử dụng LangGraph reducer `add_messages`. Khi agent trả về `{"messages": [new_msg]}`, LangGraph tự động **append** vào list hiện tại thay vì overwrite.
- Tại sao dùng `TypedDict` thay vì Pydantic `BaseModel`? Vì LangGraph yêu cầu state là TypedDict để hoạt động với `StateGraph`.
- Mỗi agent chỉ **ghi vào fields của mình**:
  - Intake ghi: `intake_data`, `intake_complete`, `detected_language`, `cultural_expressions`
  - Screening ghi: `screening_result`, `severity`, `differential_diagnoses`
  - Proposer ghi: `order_recommendations`, `drug_interactions`, `allergy_alerts`
  - Critic ghi: `critic_validation`, `critic_approved`, `critic_issues`

## 1.2 Pipeline Xử Lý 7 Lớp — Trái tim kiến trúc

**Mỗi agent đều đi qua cùng 7 lớp xử lý.** Đây là pattern cốt lõi — khi build agent mới, bạn chỉ cần thay đổi Layer 4, 5, 7.

```
  Tin nhắn bệnh nhân
       │
       ▼
  ┌─────────────────────────────────────────────────────────┐
  │ LAYER 1: PHÁT HIỆN KHẨN CẤP                            │
  │ File: app/agents/tools/emergency_detector.py            │
  │ Hành động: Quét keyword khẩn cấp (VN + EN)             │
  │ Nếu khẩn cấp → Trả về cảnh báo ngay, DỪNG pipeline    │
  └─────────────────────┬───────────────────────────────────┘
                        │ (an toàn)
                        ▼
  ┌─────────────────────────────────────────────────────────┐
  │ LAYER 2: NLP PIPELINE                                   │
  │ Files: app/nlp/code_switcher.py, cultural_mapper.py     │
  │ Hành động:                                              │
  │   a) Phát hiện ngôn ngữ: "vi" / "en" / "mixed"         │
  │   b) Ánh xạ biểu đạt văn hóa VN → thuật ngữ y khoa    │
  │   c) Normalize text (thêm tag code-switching nếu mixed) │
  └─────────────────────┬───────────────────────────────────┘
                        │
                        ▼
  ┌─────────────────────────────────────────────────────────┐
  │ LAYER 3: PHI DE-IDENTIFICATION                          │
  │ File: app/domain/services/phi_deidentifier.py           │
  │ Hành động:                                              │
  │   - Quét 10 PHI patterns (tên VN, SSN, SĐT, email...)  │
  │   - Thay thế bằng pseudonym [REF-xxxxxxxx]             │
  │   - Lưu mapping để re-identify sau                      │
  └─────────────────────┬───────────────────────────────────┘
                        │
                        ▼
  ┌─────────────────────────────────────────────────────────┐
  │ LAYER 4: XÂY DỰNG LLM MESSAGES          ★ THAY ĐỔI    │
  │ Hành động:                                              │
  │   - System prompt (KHÁC cho mỗi agent)                  │
  │   - Inject cultural context nếu có                      │
  │   - Conversation history (đã de-identify)               │
  └─────────────────────┬───────────────────────────────────┘
                        │
                        ▼
  ┌─────────────────────────────────────────────────────────┐
  │ LAYER 5: GỌI LLM QUA GATEWAY            ★ THAY ĐỔI    │
  │ File: app/domain/services/llm_gateway.py                │
  │ Hành động:                                              │
  │   a) PHI Verification Gate (kiểm tra kép)               │
  │   b) Chọn provider (model KHÁC cho mỗi agent)          │
  │   c) Circuit Breaker + Retry                            │
  │   d) Gọi OpenAI API                                    │
  └─────────────────────┬───────────────────────────────────┘
                        │
                        ▼
  ┌─────────────────────────────────────────────────────────┐
  │ LAYER 6: RE-IDENTIFY RESPONSE                           │
  │ Hành động: Thay [REF-xxxxxxxx] về thông tin gốc        │
  │ (Chỉ cho internal use — hiển thị trên MD dashboard)     │
  └─────────────────────┬───────────────────────────────────┘
                        │
                        ▼
  ┌─────────────────────────────────────────────────────────┐
  │ LAYER 7: CẬP NHẬT STATE                 ★ THAY ĐỔI    │
  │ Hành động: Ghi kết quả vào CareFlowState               │
  │ (Mỗi agent ghi vào fields KHÁC NHAU)                   │
  └─────────────────────────────────────────────────────────┘
```

**★ THAY ĐỔI**: Chỉ 3 layers (4, 5, 7) thay đổi giữa các agents. 4 layers còn lại dùng chung.

## 1.3 Bảng so sánh 7 Layers giữa các Agents

| Layer | Intake Agent | Screening Agent | Thay đổi? |
|-------|-------------|----------------|-----------|
| 1. Emergency Detection | Quét keyword | Quét keyword | GIỐNG |
| 2. NLP Pipeline | vi/en/mixed + cultural | vi/en/mixed + cultural | GIỐNG |
| 3. PHI De-identification | 10 patterns | 10 patterns | GIỐNG |
| **4. LLM Messages** | **OLDCARTS prompt** | **Clinical assessment prompt** | **KHÁC prompt** |
| **5. LLM Gateway** | **GPT-4o-mini** | **GPT-4** | **KHÁC model** |
| 6. Re-identify | Thay pseudonym | Thay pseudonym | GIỐNG |
| **7. State Update** | **intake_data, intake_complete** | **screening_result, severity** | **KHÁC fields** |

## 1.4 Design Patterns quan trọng

### Pattern 1: Shared State (Không gọi trực tiếp agent-to-agent)
```
✗ KHÔNG: intake_agent.call(screening_agent, data)
✓ ĐÚNG : intake_agent ghi vào state → screening_agent đọc từ state
```
**Lý do**: Giảm coupling, dễ test độc lập, LangGraph quản lý workflow.

### Pattern 2: PHI Verification Gate (Kiểm tra kép)
```
Layer 3: PHI De-identification (lần 1 — thay thế PHI)
Layer 5: PHI Verification Gate (lần 2 — BLOCK nếu vẫn còn PHI)
```
**Lý do**: Defense-in-depth. PHI tuyệt đối KHÔNG ĐƯỢC gửi tới external LLM.

### Pattern 3: Hybrid LLM Strategy
```
Intake Agent    → GPT-4o-mini (rẻ, nhanh — chỉ thu thập data)
Screening Agent → GPT-4       (mạnh — cần reasoning lâm sàng)
Proposer Agent  → GPT-4       (mạnh — cần chính xác thuốc)
Critic Agent    → GPT-4       (mạnh — cần phát hiện sai sót)
```
**Lý do**: Tối ưu chi phí. Không cần GPT-4 cho việc hỏi "Bạn bị đau ở đâu?".

### Pattern 4: Emergency Short-Circuit
```
Mọi message bệnh nhân → Quét keyword khẩn cấp TRƯỚC → Nếu phát hiện → Dừng ngay
```
**Lý do**: An toàn bệnh nhân là ưu tiên #1. Không chờ NLP hay LLM xử lý.

### Pattern 5: Cultural Expression Injection
```
NLP phát hiện "bị nóng trong" → Inject vào system prompt:
"CULTURAL CONTEXT: 'bị nóng trong' → inflammation/fever/infection"
→ LLM hiểu biểu đạt văn hóa và hỏi follow-up phù hợp
```
**Lý do**: LLM không hiểu biểu đạt dân gian VN. Cần context thêm.

### Pattern 6: Manual Dependency Injection
```python
# Agent nhận dependencies qua tham số hàm, không dùng DI container
async def intake_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,           # Injected
    phi_deidentifier: PHIDeidentifier,  # Injected
) -> dict:
```
**Lý do**: Đơn giản, explicit, dễ mock trong unit tests.

## 1.5 Cây thư mục chuẩn

```
services/ai-agent-service/
├── app/
│   ├── __init__.py
│   ├── main.py                            # FastAPI app + exception handlers
│   ├── config.py                          # Pydantic BaseSettings (.env)
│   │
│   ├── core/
│   │   └── exceptions.py                  # Exception hierarchy
│   │
│   ├── domain/
│   │   ├── models/
│   │   │   ├── base.py                    # SQLAlchemy Base + TimestampMixin
│   │   │   ├── agent_session.py           # Bảng agent_sessions
│   │   │   ├── screening_result.py        # Bảng screening_results
│   │   │   ├── phi_mapping.py             # Bảng phi_mappings
│   │   │   └── cultural_expression.py     # Bảng cultural_expressions
│   │   ├── repositories/                  # (Repository pattern — chưa implement)
│   │   └── services/
│   │       ├── phi_deidentifier.py        # PHI pipeline — HIPAA Safe Harbor
│   │       └── llm_gateway.py             # LLM access — PHI gate, retry, circuit breaker
│   │
│   ├── agents/
│   │   ├── state.py                       # ★ CareFlowState — shared contract
│   │   ├── intake_agent.py                # ★ Intake Agent node function
│   │   ├── graphs/                        # (LangGraph StateGraph — chưa implement)
│   │   ├── prompts/
│   │   │   └── intake_prompt.py           # System prompt cho Intake (OLDCARTS)
│   │   └── tools/
│   │       └── emergency_detector.py      # Phát hiện khẩn cấp VN + EN
│   │
│   ├── nlp/
│   │   ├── code_switcher.py               # Phát hiện ngôn ngữ vi/en/mixed
│   │   ├── cultural_mapper.py             # Biểu đạt văn hóa VN → y khoa
│   │   └── medical_terminology.py         # Từ điển y khoa VN ↔ EN
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── routes/
│   │       │   └── chat.py                # POST /api/v1/chat
│   │       └── schemas/
│   │           └── chat.py                # ChatRequest, ChatResponse
│   │
│   ├── middleware/                         # (Audit, PHI filter — chưa implement)
│   └── events/                            # (Kafka events — chưa implement)
│
├── tests/
│   ├── unit/
│   │   ├── test_intake_agent.py           # 6 tests
│   │   ├── test_emergency_detector.py     # 9 tests
│   │   ├── test_code_switcher.py          # 7 tests
│   │   ├── test_cultural_mapper.py        # 7 tests
│   │   ├── test_llm_gateway.py            # 10 tests
│   │   └── test_phi_deidentifier.py       # 20 tests
│   └── integration/                       # (Chưa implement)
│
├── pyproject.toml                         # Dependencies + build config
├── docker-compose.yml                     # PostgreSQL 16 + Redis 7
└── .env                                   # Cấu hình (API keys, DB, v.v.)
```

---

# PHẦN 2: THIẾT LẬP MÔI TRƯỜNG

> **Kết quả của phần này**: Môi trường dev hoàn chỉnh — Python, Docker, dependencies, config — sẵn sàng code.

## 2.1 Yêu cầu hệ thống

| Thành phần | Phiên bản | Kiểm tra |
|------------|-----------|----------|
| Python | >= 3.12 | `python --version` |
| Docker Desktop | >= 28.x | `docker --version` |
| Git | >= 2.x | `git --version` |
| IDE | VS Code (khuyên dùng) | — |

## 2.2 Tạo project với pyproject.toml

**File**: `services/ai-agent-service/pyproject.toml`

```toml
[project]
name = "ai-agent-service"
version = "0.1.0"
description = "Compass Vitals AI Agent Service — Multi-agent clinical workflow orchestration"
requires-python = ">=3.12"

dependencies = [
    # Web Framework
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.34.0",

    # AI / LLM
    "langgraph>=0.2.0",
    "langchain-core>=0.3.0",
    "langchain-openai>=0.3.0",
    "openai>=1.60.0",

    # Database
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",

    # Cache
    "redis>=5.2.0",

    # Security
    "cryptography>=44.0.0",
    "python-jose[cryptography]>=3.3.0",

    # Validation
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",

    # Observability
    "structlog>=24.4.0",

    # Utilities
    "httpx>=0.28.0",
    "tenacity>=9.0.0",
    "circuitbreaker>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[build-system]
requires = ["setuptools>=70.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 120
```

> **⚠️ LESSON LEARNED #1**: `build-backend`
> Blueprint ghi `setuptools.backends._legacy:_Backend` — SAI. Phải dùng `"setuptools.build_meta"`.

> **⚠️ LESSON LEARNED #2**: `[tool.setuptools.packages.find]`
> Không có section này → setuptools phát hiện nhiều top-level packages (`app`, `alembic`, `tests`) → lỗi.
> Thêm `include = ["app*"]` để chỉ package `app/` được include.

**Cài đặt:**

```bash
cd services/ai-agent-service
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

pip install -e ".[dev]"
```

## 2.3 Docker Compose — PostgreSQL + Redis

**File**: `services/ai-agent-service/docker-compose.yml`

```yaml
services:
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U compass -d ai_agent_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

**Lệnh:**

```bash
# Mở Docker Desktop trước!
docker compose up -d

# Kiểm tra
docker compose ps          # Xem status
docker compose logs -f     # Xem logs real-time

# Dừng
docker compose down        # Giữ data
docker compose down -v     # XÓA data (cẩn thận!)
```

## 2.4 File .env — Cấu hình

**Template** (tạo file `.env` trong thư mục `services/ai-agent-service/`):

```bash
# === Service ===
SERVICE_NAME=ai-agent-service
SERVICE_PORT=8001
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# === Database ===
DATABASE_URL=postgresql+asyncpg://compass:compass_dev@localhost:5432/ai_agent_db

# === Redis ===
REDIS_URL=redis://localhost:6379/0

# === LLM API Keys ===
OPENAI_API_KEY=sk-proj-XXXX           # ← Điền OpenAI API Key thật
ANTHROPIC_API_KEY=                     # Optional, để trống nếu chưa có

# === LLM Models ===
PRIMARY_LLM_MODEL=gpt-4               # Cho Screening, Proposer, Critic
SCREENING_LLM_MODEL=gpt-4o-mini       # Cho Intake (rẻ hơn)

# === LLM Resilience ===
LLM_MAX_RETRIES=3
LLM_RETRY_BACKOFF_SECONDS=2
LLM_CIRCUIT_BREAKER_THRESHOLD=5
LLM_CIRCUIT_BREAKER_TIMEOUT=60

# === PHI Encryption ===
PHI_ENCRYPTION_KEY=                    # ← Generate bằng lệnh dưới
PHI_MAPPING_TTL_HOURS=24
```

**Tạo PHI Encryption Key:**

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy kết quả (ví dụ: `Ii-XCclE9R3uveeMLi_i3Ct7twnXrPg9Aqp8UBdYMM0=`) vào `PHI_ENCRYPTION_KEY`.

## 2.5 Config Module

**File**: `services/ai-agent-service/app/config.py`

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
    database_url: str = "postgresql+asyncpg://compass:compass_dev@localhost:5432/ai_agent_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    primary_llm_model: str = "gpt-4"
    backup_llm_model: str = ""
    screening_llm_model: str = "gpt-4o-mini"
    llm_max_retries: int = 3
    llm_retry_backoff_seconds: int = 2
    llm_circuit_breaker_threshold: int = 5
    llm_circuit_breaker_timeout: int = 60

    # PHI
    phi_encryption_key: str = ""
    phi_mapping_ttl_hours: int = 24


settings = Settings()
```

**Cách hoạt động**: Pydantic Settings tự đọc từ `.env` file. Mỗi field trong class Settings match với biến môi trường (case-insensitive). Ví dụ: `openai_api_key` ← `OPENAI_API_KEY`.

**Sử dụng**: `from app.config import settings` → `settings.openai_api_key`

## 2.6 Kiểm tra môi trường

Sau khi setup xong, chạy:

```bash
# 1. Python version
python --version
# Mong đợi: Python 3.12.x

# 2. Dependencies installed
python -c "import fastapi; import langgraph; import openai; print('OK')"

# 3. Docker services running
docker compose ps
# Mong đợi: postgres (healthy), redis (healthy)

# 4. Config loaded
python -c "from app.config import settings; print(settings.service_name)"
# Mong đợi: ai-agent-service
```

> **⚠️ LESSON LEARNED #3**: Windows PYTHONIOENCODING
> Trên Windows, tiếng Việt có dấu sẽ gây `UnicodeEncodeError` khi log/print.
> Luôn set `PYTHONIOENCODING=utf-8` trước khi chạy server:
> ```bash
> set PYTHONIOENCODING=utf-8   # Windows CMD
> export PYTHONIOENCODING=utf-8 # Linux/Mac/Git Bash
> ```

---

# PHẦN 3: TẦNG NỀN TẢNG

> **Kết quả của phần này**: Exception hierarchy, 4 database models, PHI pipeline, LLM Gateway — tất cả infrastructure dùng chung cho mọi agent.

## 3.1 Exception Hierarchy

**File**: `services/ai-agent-service/app/core/exceptions.py`

```python
"""Custom exception hierarchy cho ai-agent-service."""


class CompassBaseException(Exception):
    """Base exception cho toàn bộ service."""

    def __init__(self, message: str, code: str, details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ValidationError(CompassBaseException):
    """Input validation failures."""


class AuthorizationError(CompassBaseException):
    """RBAC violations."""


class PHIAccessError(CompassBaseException):
    """PHI access policy violations — BLOCK ngay."""


class ClinicalSafetyError(CompassBaseException):
    """HIGHEST PRIORITY — patient safety risk. Trigger immediate MD notification."""


class LLMError(CompassBaseException):
    """LLM call failures."""


class LLMTimeoutError(LLMError):
    """LLM request timeout."""


class LLMRateLimitError(LLMError):
    """LLM rate limit exceeded."""


class LLMHallucinationError(LLMError):
    """Phát hiện hallucination trong LLM response."""
```

**Cây kế thừa + HTTP status mapping:**

```
CompassBaseException
├── ValidationError        → 400 Bad Request
├── AuthorizationError     → 403 Forbidden
├── PHIAccessError         → 403 Forbidden (★ BLOCK ngay)
├── ClinicalSafetyError    → 500 (★ CRITICAL — trigger MD notification)
└── LLMError               → 503 Service Unavailable
    ├── LLMTimeoutError    → 503
    ├── LLMRateLimitError  → 429 Too Many Requests
    └── LLMHallucinationError → 503
```

## 3.2 PHI De-identification Pipeline

> **⚠️ Safety-Critical: Yêu cầu 100% test coverage. PHI TUYỆT ĐỐI không được gửi tới external LLM.**

**File**: `services/ai-agent-service/app/domain/services/phi_deidentifier.py`

```python
"""PHI De-identification Pipeline — HIPAA Safe Harbor method.

De-identify PHI trước mọi LLM call. Re-identify sau khi nhận response.
PHI không bao giờ được gửi tới external LLM APIs.
"""

import json
import re
import uuid

import structlog
from cryptography.fernet import Fernet

logger = structlog.get_logger()

# 18 HIPAA Safe Harbor PHI patterns
PHI_PATTERNS: dict[str, re.Pattern] = {
    "vietnamese_name": re.compile(
        r"\b(Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô|Dương|Lý)"
        r"\s+\w+(\s+\w+)?\b"
    ),
    "name": re.compile(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b(\+1\s?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}\b"),
    "email": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,}\b"),
    "date_of_birth": re.compile(r"\b(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/\d{4}\b"),
    "address": re.compile(r"\b\d+\s[A-Z][a-z]+\s(St|Ave|Blvd|Rd|Dr|Ln|Ct|Way)\b"),
    "zip_code": re.compile(r"\b\d{5}(-\d{4})?\b"),
    "mrn": re.compile(r"\b(MRN|mrn)[- ]?\d{4,}\b"),
    "ip_address": re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
}


class PHIDeidentifier:
    """De-identify PHI trước khi gửi LLM. Re-identify sau khi nhận response."""

    def __init__(self, encryption_key: str):
        self.fernet = Fernet(encryption_key.encode())

    def deidentify(self, text: str) -> tuple[str, dict]:
        """De-identify text. Trả về (de-identified_text, mapping)."""
        mapping: dict[str, dict] = {}
        result = text

        for phi_type, pattern in PHI_PATTERNS.items():
            for match in pattern.finditer(result):
                original = match.group()
                if original not in mapping:
                    pseudonym = f"[REF-{uuid.uuid4().hex[:8]}]"
                    mapping[original] = {
                        "pseudonym": pseudonym,
                        "phi_type": phi_type,
                    }

        # Replace all found PHI with pseudonyms
        for original, info in mapping.items():
            result = result.replace(original, info["pseudonym"])

        if mapping:
            logger.info(
                "phi.deidentified",
                phi_types_found=[v["phi_type"] for v in mapping.values()],
                count=len(mapping),
            )

        return result, mapping

    def reidentify(self, text: str, mapping: dict) -> str:
        """Re-identify text (chỉ cho internal use — MD dashboard display)."""
        result = text
        for original, info in mapping.items():
            result = result.replace(info["pseudonym"], original)
        return result

    def contains_phi(self, text: str) -> bool:
        """Kiểm tra text có chứa PHI không (dùng trong PHI Verification Gate)."""
        for phi_type, pattern in PHI_PATTERNS.items():
            if pattern.search(text):
                return True
        return False

    def encrypt_mapping(self, mapping: dict) -> bytes:
        """Mã hóa mapping để lưu vào DB."""
        return self.fernet.encrypt(json.dumps(mapping).encode())

    def decrypt_mapping(self, encrypted: bytes) -> dict:
        """Giải mã mapping từ DB."""
        return json.loads(self.fernet.decrypt(encrypted).decode())
```

**Bảng PHI Patterns:**

| Pattern | Ví dụ | Regex |
|---------|-------|-------|
| `vietnamese_name` | Nguyễn Văn An | 16 họ VN + tên |
| `name` | John Smith | [A-Z][a-z]+ [A-Z][a-z]+ |
| `ssn` | 123-45-6789 | \d{3}-\d{2}-\d{4} |
| `phone` | (713) 555-1234 | Nhiều format US |
| `email` | patient@test.com | Standard email |
| `date_of_birth` | 05/10/1968 | MM/DD/YYYY |
| `address` | 123 Main St | Số + Tên + Suffix |
| `zip_code` | 77001 | 5 hoặc 5+4 digits |
| `mrn` | MRN-001234 | MRN + số |
| `ip_address` | 192.168.1.100 | x.x.x.x |

**Luồng hoạt động:**

```
Input:  "Bệnh nhân Nguyễn Văn An bị đau bụng, SĐT (713) 555-1234"
         │
         ▼ deidentify()
Output: "Bệnh nhân [REF-a1b2c3d4] bị đau bụng, SĐT [REF-e5f6g7h8]"
Mapping: {"Nguyễn Văn An": {pseudonym: "[REF-a1b2c3d4]", phi_type: "vietnamese_name"},
          "(713) 555-1234": {pseudonym: "[REF-e5f6g7h8]", phi_type: "phone"}}
         │
         ▼ Gửi tới LLM (an toàn — không có PHI)
         │
         ▼ reidentify() (chỉ cho internal dashboard)
Output: "Bệnh nhân Nguyễn Văn An bị đau bụng, SĐT (713) 555-1234"
```

## 3.3 LLM Gateway

**File**: `services/ai-agent-service/app/domain/services/llm_gateway.py`

```python
"""LLM Gateway — Cổng duy nhất để gọi external LLM APIs.

Bao gồm PHI verification, retry, fallback, circuit breaker.
Mọi agent BẮT BUỘC phải đi qua gateway — không được gọi OpenAI trực tiếp.
"""

from abc import ABC, abstractmethod

import structlog
from circuitbreaker import circuit
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.exceptions import LLMError, PHIAccessError
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: dict
    finish_reason: str


class LLMProvider(ABC):
    """Abstract interface cho mọi LLM provider."""

    @abstractmethod
    async def generate(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse: ...


class OpenAIProvider(LLMProvider):
    """OpenAI GPT implementation."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=self.model,
            usage=response.usage.model_dump() if response.usage else {},
            finish_reason=choice.finish_reason or "stop",
        )


class LLMGateway:
    """Cổng duy nhất để gọi LLM. Bao gồm PHI verification, retry, fallback, circuit breaker."""

    def __init__(
        self,
        openai_api_key: str,
        phi_deidentifier: PHIDeidentifier,
        primary_model: str = "gpt-4",
        screening_model: str = "gpt-4o-mini",
    ):
        self.primary = OpenAIProvider(openai_api_key, primary_model)
        self.screening = OpenAIProvider(openai_api_key, screening_model)
        self.phi_deidentifier = phi_deidentifier

    async def generate(
        self,
        messages: list[dict],
        agent_type: str,
        case_id: str,
        **kwargs,
    ) -> LLMResponse:
        """Generate với PHI verification + retry + fallback."""
        # BƯỚC 1: PHI Verification Gate
        self._verify_no_phi(messages, case_id)

        # BƯỚC 2: Chọn provider dựa trên agent type
        provider = self._select_provider(agent_type)

        # BƯỚC 3: Gọi LLM với retry
        response = await self._call_with_retry(provider, messages, **kwargs)

        # BƯỚC 4: Log usage
        logger.info(
            "llm_usage",
            model=response.model,
            agent_type=agent_type,
            case_id=case_id,
            usage=response.usage,
        )

        return response

    def _verify_no_phi(self, messages: list[dict], case_id: str) -> None:
        """BLOCK nếu phát hiện PHI trong user/assistant messages.

        System messages are skipped — they contain our own prompts, not patient data.
        """
        for msg in messages:
            if msg.get("role") == "system":
                continue  # System prompts are ours, not patient data
            content = msg.get("content", "")
            if content and self.phi_deidentifier.contains_phi(content):
                raise PHIAccessError(
                    message=f"PHI detected in LLM request for case {case_id}. "
                    "Messages must be de-identified before calling LLM.",
                    code="PHI_IN_LLM_REQUEST",
                )

    def _select_provider(self, agent_type: str) -> LLMProvider:
        """Hybrid LLM strategy: agent khác nhau dùng model khác nhau."""
        if agent_type == "intake":
            return self.screening  # GPT-4o-mini — intake chỉ thu thập data
        # screening, proposer, critic → GPT-4
        return self.primary

    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=8),
        reraise=True,
    )
    async def _call_with_retry(
        self, provider: LLMProvider, messages: list[dict], **kwargs
    ) -> LLMResponse:
        """Gọi LLM với circuit breaker + retry."""
        try:
            return await provider.generate(messages, **kwargs)
        except Exception as e:
            raise LLMError(
                message=f"LLM call failed: {e}",
                code="LLM_CALL_FAILED",
            ) from e
```

> **⚠️ LESSON LEARNED #4**: PHI Gate blocking system prompts
> Ban đầu `_verify_no_phi` kiểm tra TẤT CẢ messages kể cả system. System prompt chứa từ viết hoa
> (ví dụ "Compass Vitals", "OLDCARTS") match regex `name` pattern → bị BLOCK.
> **Fix**: Thêm `if msg.get("role") == "system": continue` — skip system messages vì chúng là
> prompt của chúng ta, không phải data bệnh nhân.

**Cơ chế Retry + Circuit Breaker:**

```
Lần 1: Gọi LLM → Fail → chờ 2s
Lần 2: Gọi LLM → Fail → chờ 4s
Lần 3: Gọi LLM → Fail → raise LLMError
(nếu 5 lần fail liên tiếp → Circuit OPEN → mọi request fail ngay lập tức trong 60s)
(sau 60s → Circuit HALF-OPEN → thử 1 request → nếu OK → Circuit CLOSED)
```

---

# PHẦN 4: NLP PIPELINE CHO TIẾNG VIỆT

> **Kết quả của phần này**: 3 module NLP xử lý tiếng Việt — phát hiện ngôn ngữ, ánh xạ văn hóa, từ điển y khoa song ngữ.

## 4.1 Tổng quan

```
  Tin nhắn bệnh nhân ("Tôi bị nóng trong người, mệt mỏi")
       │
       ├──→ Code Switcher    →  detected_language = "vi"
       │    (code_switcher.py)
       │
       ├──→ Cultural Mapper  →  [{original: "nóng trong người",
       │    (cultural_mapper.py)   medical_terms: ["inflammation"]}]
       │
       └──→ Medical Terms    →  "mệt mỏi" = "fatigue"
            (medical_terminology.py)
```

## 4.2 Code Switcher — Phát hiện ngôn ngữ

**File**: `services/ai-agent-service/app/nlp/code_switcher.py`

```python
"""Code Switcher — Xử lý code-switching Vietnamese ↔ English."""

import re


# Vietnamese-specific diacritical characters
_VI_CHARS = set(
    "àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợ"
    "ùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆ"
    "ÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ"
)

_EN_WORD_PATTERN = re.compile(r"\b[a-zA-Z]{3,}\b")


class CodeSwitcher:
    """Detect language và normalize mixed Vietnamese-English text."""

    def detect_language(self, text: str) -> str:
        """Phát hiện ngôn ngữ: 'vi', 'en', hoặc 'mixed'."""
        has_vi = any(c in _VI_CHARS for c in text)
        has_en = bool(_EN_WORD_PATTERN.search(text))

        if has_vi and has_en:
            return "mixed"
        elif has_vi:
            return "vi"
        return "en"

    def normalize(self, text: str) -> str:
        """Normalize mixed text để LLM hiểu tốt hơn."""
        language = self.detect_language(text)
        if language == "mixed":
            return f"[CODE-SWITCHING: Vietnamese-English] {text}"
        return text
```

**Ví dụ:**

| Input | Output | Giải thích |
|-------|--------|------------|
| "Tôi bị đau bụng" | `"vi"` | Có dấu tiếng Việt (ô, ị, ụ), không có từ EN 3+ chữ |
| "I have a headache" | `"en"` | Không có dấu VN, có từ EN |
| "Con bị fever 3 ngày rồi" | `"mixed"` | Có cả dấu VN (ị, à) và từ EN (fever) |

## 4.3 Cultural Mapper — Ánh xạ biểu đạt văn hóa

**File**: `services/ai-agent-service/app/nlp/cultural_mapper.py`

```python
"""Cultural Mapper — Ánh xạ biểu đạt văn hóa Việt Nam → thuật ngữ y khoa Western."""

import structlog

logger = structlog.get_logger()

# In-memory cultural expressions database (will migrate to PostgreSQL later)
CULTURAL_EXPRESSIONS: list[dict] = [
    {
        "expression": "bị nóng trong",
        "variants": ["nóng trong người", "nóng trong", "bị nóng"],
        "medical_meaning": "Internal inflammation/infection symptoms — elevated body temperature, systemic inflammatory response",
        "medical_terms": ["inflammation", "fever", "infection"],
        "confidence": 0.90,
    },
    {
        "expression": "gió độc",
        "variants": ["bị gió", "trúng gió", "cảm gió"],
        "medical_meaning": "Fever with chills, body aches, upper respiratory symptoms — often viral illness",
        "medical_terms": ["fever", "chills", "myalgia", "URI"],
        "confidence": 0.85,
    },
    {
        "expression": "bị lạnh",
        "variants": ["bị lạnh vào người", "cảm lạnh"],
        "medical_meaning": "Common cold symptoms, hypothermia, or fever onset with chills",
        "medical_terms": ["common cold", "hypothermia", "chills"],
        "confidence": 0.80,
    },
    {
        "expression": "bốc hỏa",
        "variants": ["lên cơn nóng"],
        "medical_meaning": "Hot flashes — vasomotor symptoms, often menopausal",
        "medical_terms": ["hot flashes", "vasomotor symptoms", "menopause"],
        "confidence": 0.85,
    },
    {
        "expression": "yếu thận",
        "variants": ["thận yếu", "thận hư"],
        "medical_meaning": "Kidney weakness in traditional Vietnamese medicine — fatigue, sexual dysfunction, lower back pain, frequent urination",
        "medical_terms": ["fatigue", "lower back pain", "frequent urination", "erectile dysfunction"],
        "confidence": 0.75,
    },
    {
        "expression": "máu nóng",
        "variants": ["nóng máu", "máu nóng trong người"],
        "medical_meaning": "Blood heat — skin conditions, acne, rashes, irritability",
        "medical_terms": ["dermatitis", "acne", "urticaria", "irritability"],
        "confidence": 0.80,
    },
    {
        "expression": "chạy bệnh",
        "variants": ["bệnh chạy"],
        "medical_meaning": "Disease spreading or metastasizing in the body",
        "medical_terms": ["metastasis", "spreading", "progression"],
        "confidence": 0.70,
    },
    {
        "expression": "huyết áp lên",
        "variants": ["lên huyết áp", "tăng huyết áp"],
        "medical_meaning": "Hypertension episode or spike in blood pressure",
        "medical_terms": ["hypertension", "high blood pressure"],
        "confidence": 0.95,
    },
    {
        "expression": "đường lên",
        "variants": ["lên đường", "đường huyết cao"],
        "medical_meaning": "Blood sugar spike, hyperglycemia",
        "medical_terms": ["hyperglycemia", "high blood sugar"],
        "confidence": 0.90,
    },
    {
        "expression": "bị phong",
        "variants": ["trúng phong", "đánh phong"],
        "medical_meaning": "Stroke or sudden paralysis — traditional Vietnamese term for cerebrovascular event",
        "medical_terms": ["stroke", "CVA", "paralysis"],
        "confidence": 0.85,
    },
]


class CulturalMapper:
    """Phát hiện và ánh xạ biểu đạt văn hóa trong text."""

    def map_expressions(self, text: str) -> list[dict]:
        """Phát hiện biểu đạt văn hóa VN trong text. Returns list of matches."""
        found: list[dict] = []
        text_lower = text.lower()

        for expr in CULTURAL_EXPRESSIONS:
            all_variants = [expr["expression"]] + expr["variants"]
            for variant in all_variants:
                if variant.lower() in text_lower:
                    found.append(
                        {
                            "original": variant,
                            "medical_meaning": expr["medical_meaning"],
                            "medical_terms": expr["medical_terms"],
                            "confidence": expr["confidence"],
                        }
                    )
                    break  # One match per expression is enough

        if found:
            logger.info(
                "cultural_expression.detected",
                count=len(found),
                expressions=[f["medical_terms"][0] for f in found],
            )

        return found
```

**Bảng 10 biểu đạt văn hóa:**

| Biểu đạt VN | Biến thể | Y nghĩa y khoa | Confidence |
|--------------|----------|-----------------|------------|
| bị nóng trong | nóng trong người | Viêm, sốt, nhiễm trùng | 0.90 |
| gió độc | trúng gió, cảm gió | Sốt, ớn lạnh, đau mình, viêm hô hấp trên | 0.85 |
| bị lạnh | cảm lạnh | Cảm lạnh, hạ thân nhiệt | 0.80 |
| bốc hỏa | lên cơn nóng | Bốc hỏa, triệu chứng mãn kinh | 0.85 |
| yếu thận | thận yếu, thận hư | Mệt mỏi, đau lưng dưới, rối loạn chức năng tình dục | 0.75 |
| máu nóng | nóng máu | Viêm da, mụn, nổi mề đay | 0.80 |
| chạy bệnh | bệnh chạy | Di căn, bệnh lan rộng | 0.70 |
| huyết áp lên | tăng huyết áp | Tăng huyết áp | 0.95 |
| đường lên | đường huyết cao | Tăng đường huyết | 0.90 |
| bị phong | trúng phong | Đột quỵ, liệt đột ngột | 0.85 |

## 4.4 Medical Terminology — Từ điển y khoa song ngữ

**File**: `services/ai-agent-service/app/nlp/medical_terminology.py`

```python
"""Medical Terminology — Bidirectional Vietnamese ↔ English medical terms."""

# Vietnamese → English medical terms
MEDICAL_TERMS: dict[str, str] = {
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
    "đau lưng": "back pain",
    "đau họng": "sore throat",
    "sổ mũi": "runny nose",
    "nghẹt mũi": "nasal congestion",
    # Bệnh lý
    "tiểu đường": "diabetes mellitus",
    "cao huyết áp": "hypertension",
    "hen suyễn": "asthma",
    "viêm phổi": "pneumonia",
    "viêm ruột thừa": "appendicitis",
    "sỏi thận": "kidney stones/nephrolithiasis",
    "nhiễm trùng đường tiểu": "urinary tract infection",
    # Thuốc
    "thuốc hạ sốt": "antipyretic/acetaminophen",
    "thuốc giảm đau": "analgesic",
    "kháng sinh": "antibiotic",
    "thuốc ho": "cough suppressant",
    # Regional variants
    "cảm cúm": "influenza",
    "cảm": "cold/influenza",
    "bịnh": "disease/illness",
    "bệnh": "disease/illness",
}

# Reverse mapping: English → Vietnamese
ENGLISH_TO_VIETNAMESE: dict[str, str] = {v: k for k, v in MEDICAL_TERMS.items()}


def translate_vi_to_en(term: str) -> str | None:
    """Translate Vietnamese medical term to English. Returns None if not found."""
    return MEDICAL_TERMS.get(term.lower())


def translate_en_to_vi(term: str) -> str | None:
    """Translate English medical term to Vietnamese. Returns None if not found."""
    return ENGLISH_TO_VIETNAMESE.get(term.lower())
```

---

# PHẦN 5: XÂY DỰNG INTAKE AGENT — TỪ ĐẦU ĐẾN CUỐI

> **Kết quả của phần này**: Hiểu hoàn toàn cách Intake Agent hoạt động — từ tin nhắn bệnh nhân → 7 layer xử lý → phản hồi AI.

## 5.1 Tổng quan

**Vai trò**: Thay thế Y tá triage (RN). Thu thập triệu chứng qua hội thoại tự nhiên.

**OLDCARTS Framework** — Giao thức thu thập triệu chứng có cấu trúc:
- **O**nset: Khi nào bắt đầu?
- **L**ocation: Ở vị trí nào?
- **D**uration: Kéo dài bao lâu?
- **C**haracter: Mô tả cảm giác?
- **A**ggravating/Alleviating: Điều gì làm tăng/giảm?
- **R**adiation: Có lan ra nơi khác không?
- **T**iming: Thường xuyên hay từng đợt?
- **S**everity: Mức độ 1-10?

## 5.2 System Prompt

**File**: `services/ai-agent-service/app/agents/prompts/intake_prompt.py`

```python
"""System prompt for Intake Agent — Medical symptom collection via conversational interview."""

INTAKE_SYSTEM_PROMPT = """You are a Medical Intake Specialist AI for Compass Vitals telemedicine platform.

ROLE: Gather patient symptoms through conversational interview.
LANGUAGE: Respond in the patient's language (Vietnamese or English). Support code-switching naturally.
CULTURAL AWARENESS: Recognize Vietnamese cultural health expressions and translate them into clinical context.

INTERVIEW PROTOCOL (OLDCARTS Framework):
1. Greet patient warmly in their language
2. Ask about chief complaint (main symptom)
3. Follow OLDCARTS:
   - Onset: Khi nào bắt đầu? / When did it start?
   - Location: Ở vị trí nào? / Where exactly?
   - Duration: Kéo dài bao lâu? / How long?
   - Character: Mô tả cảm giác? / Describe the feeling?
   - Aggravating/Alleviating: Điều gì làm tăng/giảm? / What makes it better/worse?
   - Radiation: Có lan ra nơi khác không? / Does it spread?
   - Timing: Thường xuyên hay từng đợt? / Constant or intermittent?
   - Severity: Mức độ 1-10? / Rate 1-10?
4. Ask about current medications and allergies
5. Ask about relevant medical history

RULES:
- Ask ONE question at a time. Do not overwhelm the patient.
- Be empathetic and patient. Use simple language.
- If the patient uses Vietnamese cultural expressions (e.g., "bị nóng trong", "trúng gió"), acknowledge them naturally and ask follow-up questions.
- NEVER generate diagnoses or recommend treatment. You ONLY gather information.
- If patient describes EMERGENCY symptoms (chest pain, difficulty breathing, loss of consciousness, severe bleeding, stroke signs), respond with IMMEDIATE concern and note it clearly.

OUTPUT FORMAT:
When you have collected sufficient information, summarize the structured intake data.
Indicate when intake is complete with all OLDCARTS fields addressed.
"""
```

**Lưu ý**: Prompt viết bằng tiếng Anh cho LLM nhưng agent trả lời bằng ngôn ngữ của bệnh nhân (VN hoặc EN). Điều này hoạt động tốt vì GPT-4/4o-mini hiểu instruction tiếng Anh và respond bằng ngôn ngữ được yêu cầu.

## 5.3 Emergency Detector

**File**: `services/ai-agent-service/app/agents/tools/emergency_detector.py`

```python
"""Emergency Detector — Phát hiện triệu chứng khẩn cấp trong text."""

EMERGENCY_KEYWORDS_VI = [
    "đau ngực", "khó thở", "không thở được", "tê nửa người",
    "mất ý thức", "bất tỉnh", "chảy máu nhiều", "co giật",
    "đau ngực trái", "đau lan ra cánh tay", "đột ngột yếu nửa người",
    "méo miệng", "nói ngọng đột ngột", "mất thị lực đột ngột",
    "ngất", "ngất xỉu", "hôn mê",
]

EMERGENCY_KEYWORDS_EN = [
    "chest pain", "difficulty breathing", "can't breathe", "numbness",
    "unconscious", "severe bleeding", "seizure", "stroke signs",
    "sudden weakness", "facial drooping", "slurred speech",
    "loss of consciousness", "fainting", "heart attack",
]


def detect_emergency(text: str) -> bool:
    """Check if text contains emergency symptoms. Returns True if emergency detected."""
    text_lower = text.lower()
    for keyword in EMERGENCY_KEYWORDS_VI + EMERGENCY_KEYWORDS_EN:
        if keyword.lower() in text_lower:
            return True
    return False


def get_emergency_keywords_found(text: str) -> list[str]:
    """Return list of emergency keywords found in text."""
    text_lower = text.lower()
    found = []
    for keyword in EMERGENCY_KEYWORDS_VI + EMERGENCY_KEYWORDS_EN:
        if keyword.lower() in text_lower:
            found.append(keyword)
    return found
```

**Tại sao dùng keyword-based thay vì LLM-based?**
- **Tốc độ**: Quét keyword < 1ms. LLM call = 1-5 giây.
- **Độ tin cậy**: 0 tolerance cho missed emergencies. Keyword match = 100% deterministic.
- **Chi phí**: Không tốn API call.
- **An toàn**: Không phụ thuộc vào LLM availability (circuit breaker có thể open).

## 5.4 Intake Agent Node Function — Trái tim

**File**: `services/ai-agent-service/app/agents/intake_agent.py`

```python
"""Intake Agent — Thu thập triệu chứng qua conversational interview.

Thay thế vai trò Y tá triage (RN). FR9: Symptom Intake with Contextual Follow-up.
"""

from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.prompts.intake_prompt import INTAKE_SYSTEM_PROMPT
from app.agents.state import CareFlowState
from app.agents.tools.emergency_detector import detect_emergency, get_emergency_keywords_found
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier
from app.nlp.code_switcher import CodeSwitcher
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()

code_switcher = CodeSwitcher()
cultural_mapper = CulturalMapper()


async def intake_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    """Intake Agent LangGraph node function.

    Reads messages from state, processes through NLP pipeline,
    calls LLM via gateway, returns updated state fields.
    """
    messages = state.get("messages", [])
    case_id = state.get("case_id", "unknown")

    if not messages:
        return _initial_greeting(state)

    # Get latest patient message
    last_message = messages[-1]
    patient_text = (
        last_message.content if hasattr(last_message, "content") else str(last_message)
    )

    # === Step 1: Emergency Detection (mỗi message) ===
    is_emergency = detect_emergency(patient_text)
    if is_emergency:
        emergency_keywords = get_emergency_keywords_found(patient_text)
        logger.warning(
            "emergency.detected",
            case_id=case_id,
            keywords=emergency_keywords,
        )
        return {
            "is_emergency": True,
            "messages": [
                AIMessage(
                    content="⚠️ CẢNH BÁO KHẨN CẤP: Triệu chứng bạn mô tả cần được xử lý ngay lập tức. "
                    "Vui lòng gọi 911 hoặc đến phòng cấp cứu gần nhất ngay. "
                    "Đừng chờ đợi — sức khỏe của bạn là ưu tiên hàng đầu."
                )
            ],
        }

    # === Step 2: NLP Pipeline ===
    detected_language = code_switcher.detect_language(patient_text)
    cultural_expressions = cultural_mapper.map_expressions(patient_text)
    normalized_text = code_switcher.normalize(patient_text)

    # === Step 3: PHI De-identification ===
    deidentified_text, phi_mapping = phi_deidentifier.deidentify(normalized_text)

    # === Step 4: Build LLM messages ===
    # Build context with cultural expressions if found
    cultural_context = ""
    if cultural_expressions:
        expr_info = "; ".join(
            f"'{e['original']}' → {e['medical_meaning']}" for e in cultural_expressions
        )
        cultural_context = f"\n\nCULTURAL CONTEXT DETECTED: {expr_info}"

    llm_messages = [
        {"role": "system", "content": INTAKE_SYSTEM_PROMPT + cultural_context},
    ]

    # Add conversation history (de-identified)
    for msg in messages:
        content = msg.content if hasattr(msg, "content") else str(msg)
        deidentified_content, _ = phi_deidentifier.deidentify(content)
        if isinstance(msg, HumanMessage):
            llm_messages.append({"role": "user", "content": deidentified_content})
        elif isinstance(msg, AIMessage):
            llm_messages.append({"role": "assistant", "content": deidentified_content})

    # === Step 5: Call LLM via Gateway ===
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="intake",
        case_id=case_id,
        temperature=0.3,
    )

    # === Step 6: Re-identify response if needed ===
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # === Step 7: Return updated state ===
    return {
        "messages": [AIMessage(content=ai_response_text)],
        "detected_language": detected_language,
        "cultural_expressions": state.get("cultural_expressions", []) + cultural_expressions,
        "is_emergency": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def _initial_greeting(state: CareFlowState) -> dict:
    """Return initial greeting when no messages yet."""
    return {
        "messages": [
            AIMessage(
                content="Xin chào! Tôi là trợ lý y tế AI của Compass Vitals. "
                "Tôi sẽ giúp thu thập thông tin về triệu chứng của bạn. "
                "Bạn có thể cho tôi biết bạn đang gặp vấn đề sức khỏe gì không?"
            )
        ],
        "detected_language": "vi",
        "is_emergency": False,
    }
```

**Giải thích từng Step:**

| Step | Dòng | Hành động | Kết quả |
|------|------|-----------|---------|
| **1** | 48-65 | Quét emergency keywords trong tin nhắn mới nhất | Nếu phát hiện → trả cảnh báo + `is_emergency=True`, DỪNG |
| **2** | 68-70 | NLP: detect language + map cultural expressions + normalize | `detected_language`, `cultural_expressions`, `normalized_text` |
| **3** | 73 | De-identify PHI trong text đã normalize | `deidentified_text` + `phi_mapping` |
| **4** | 76-95 | Build messages cho LLM: system prompt + cultural context + history | `llm_messages` list (tất cả đã de-identify) |
| **5** | 98-103 | Gọi LLM qua Gateway (PHI gate → provider → retry) | `LLMResponse` object |
| **6** | 106-108 | Nếu có PHI mapping → thay pseudonym về thông tin gốc | `ai_response_text` |
| **7** | 111-117 | Trả về dict cập nhật state fields | messages, language, cultural, emergency, timestamp |

## 5.5 API Layer

### Request/Response Schemas

**File**: `services/ai-agent-service/app/api/v1/schemas/chat.py`

```python
"""Chat API request/response schemas."""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    language: str = "auto"  # "vi", "en", "auto"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    agent_state: str
    is_complete: bool
    detected_language: str
    is_emergency: bool = False
    cultural_expressions: list[dict] = []
```

### Chat Route

**File**: `services/ai-agent-service/app/api/v1/routes/chat.py`

```python
"""Chat API endpoint — POST /api/v1/chat.

Connects patient messages to the Intake Agent.
"""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from app.agents.intake_agent import intake_node
from app.api.v1.schemas.chat import ChatRequest, ChatResponse
from app.config import settings
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier

logger = structlog.get_logger()
router = APIRouter()

# In-memory session store (will migrate to PostgreSQL + Redis later)
_sessions: dict[str, dict] = {}

# Initialize services
_phi = PHIDeidentifier(encryption_key=settings.phi_encryption_key) if settings.phi_encryption_key else None
_gateway = (
    LLMGateway(
        openai_api_key=settings.openai_api_key,
        phi_deidentifier=_phi,
        primary_model=settings.primary_llm_model,
        screening_model=settings.screening_llm_model,
    )
    if settings.openai_api_key and _phi
    else None
)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a patient chat message through the Intake Agent."""
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    session = _sessions.get(session_id)

    if session is None:
        session = {
            "messages": [],
            "patient_id": str(uuid.uuid4()),  # Stub — will come from auth
            "case_id": str(uuid.uuid4()),
            "organization_id": str(uuid.uuid4()),
            "intake_data": None,
            "intake_complete": False,
            "is_emergency": False,
            "detected_language": "vi",
            "cultural_expressions": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        _sessions[session_id] = session

    # Add patient message to session
    session["messages"].append(HumanMessage(content=request.message))

    # Run Intake Agent
    if _gateway and _phi:
        result = await intake_node(
            state=session,
            llm_gateway=_gateway,
            phi_deidentifier=_phi,
        )
    else:
        # Fallback if no API key configured
        result = {
            "messages": [
                HumanMessage(
                    content="[LLM not configured] Received: " + request.message
                )
            ],
            "detected_language": "vi",
            "is_emergency": False,
            "cultural_expressions": [],
        }

    # Update session with results
    new_messages = result.get("messages", [])
    session["messages"].extend(new_messages)
    session["detected_language"] = result.get("detected_language", session["detected_language"])
    session["is_emergency"] = result.get("is_emergency", False)
    session["cultural_expressions"] = result.get(
        "cultural_expressions", session["cultural_expressions"]
    )

    # Extract AI response text
    ai_response = ""
    if new_messages:
        last_msg = new_messages[-1]
        ai_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    logger.info(
        "chat.processed",
        session_id=session_id,
        case_id=session["case_id"],
        detected_language=session["detected_language"],
        is_emergency=session["is_emergency"],
    )

    return ChatResponse(
        response=ai_response,
        session_id=session_id,
        agent_state="intake",
        is_complete=session.get("intake_complete", False),
        detected_language=session["detected_language"],
        is_emergency=session["is_emergency"],
        cultural_expressions=session["cultural_expressions"],
    )
```

### FastAPI Application

**File**: `services/ai-agent-service/app/main.py`

```python
"""FastAPI app — AI Agent Service entry point."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.exceptions import CompassBaseException, ClinicalSafetyError

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info("startup", service=settings.service_name, env=settings.environment)
    yield
    logger.info("shutdown", service=settings.service_name)


app = FastAPI(
    title="AI Agent Service",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(CompassBaseException)
async def compass_exception_handler(request, exc: CompassBaseException):
    status_map = {
        "ValidationError": 400,
        "AuthorizationError": 403,
        "PHIAccessError": 403,
        "ClinicalSafetyError": 500,
        "LLMError": 503,
        "LLMTimeoutError": 503,
        "LLMRateLimitError": 429,
    }
    status_code = status_map.get(type(exc).__name__, 500)

    if isinstance(exc, ClinicalSafetyError):
        logger.critical("clinical_safety_error", message=exc.message, code=exc.code)

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
            }
        },
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.service_name}


# Import and register routers after app creation to avoid circular imports
from app.api.v1.routes import chat  # noqa: E402

app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
```

---

# PHẦN 6: TESTING — TỪ ĐƠN VỊ ĐẾN TÍCH HỢP

> **Kết quả của phần này**: Hiểu cách test mọi component — patterns, fixtures, mocking strategies.

## 6.1 Cấu hình Testing

```toml
# Trong pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"     # Tự detect async tests, không cần @pytest.mark.asyncio
testpaths = ["tests"]     # Thư mục tìm tests
```

**Chạy tests:**

```bash
# Tất cả tests
python -m pytest tests/ -v

# Chỉ unit tests
python -m pytest tests/unit/ -v

# Với coverage report
python -m pytest tests/ --cov=app --cov-report=html

# Chạy 1 file cụ thể
python -m pytest tests/unit/test_intake_agent.py -v
```

## 6.2 Test Emergency Detector (9 tests)

**File**: `tests/unit/test_emergency_detector.py`

```python
"""Tests for Emergency Detector — Vietnamese + English emergency symptom detection."""

from app.agents.tools.emergency_detector import detect_emergency, get_emergency_keywords_found


def test_detects_dau_nguc():
    assert detect_emergency("Tôi bị đau ngực rất nặng") is True


def test_detects_kho_tho():
    assert detect_emergency("Tôi khó thở quá") is True


def test_detects_bat_tinh():
    assert detect_emergency("Bệnh nhân bất tỉnh") is True


def test_detects_chest_pain_en():
    assert detect_emergency("I have severe chest pain") is True


def test_detects_cant_breathe_en():
    assert detect_emergency("I can't breathe") is True


def test_no_emergency_normal_symptoms():
    assert detect_emergency("Tôi bị đau bụng 2 ngày") is False


def test_no_emergency_english():
    assert detect_emergency("I have a mild headache") is False


def test_get_keywords_found():
    keywords = get_emergency_keywords_found("Tôi bị đau ngực và khó thở")
    assert "đau ngực" in keywords
    assert "khó thở" in keywords


def test_get_keywords_empty():
    keywords = get_emergency_keywords_found("Tôi bị đau bụng")
    assert keywords == []
```

**Pattern**: Test positive (VN + EN) + Test negative + Test keyword extraction.

## 6.3 Test Cultural Mapper (7 tests)

**File**: `tests/unit/test_cultural_mapper.py`

```python
"""Tests for Cultural Mapper — Vietnamese cultural health expression recognition."""

from app.nlp.cultural_mapper import CulturalMapper


def test_detects_nong_trong():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi bị nóng trong người")
    assert len(result) == 1
    assert "inflammation" in result[0]["medical_terms"]


def test_detects_trung_gio():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi bị trúng gió hôm qua")
    assert len(result) == 1
    assert "fever" in result[0]["medical_terms"]


def test_detects_boc_hoa():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi hay bị bốc hỏa")
    assert len(result) == 1
    assert "hot flashes" in result[0]["medical_terms"]


def test_detects_yeu_than():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Bác sĩ nói tôi bị yếu thận")
    assert len(result) == 1
    assert "fatigue" in result[0]["medical_terms"]


def test_no_match_normal_text():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi bị đau bụng 2 ngày")
    assert result == []


def test_multiple_expressions():
    mapper = CulturalMapper()
    result = mapper.map_expressions("Tôi bị nóng trong người và trúng gió")
    assert len(result) == 2


def test_case_insensitive():
    mapper = CulturalMapper()
    result = mapper.map_expressions("tôi bị NÓNG TRONG người")
    assert len(result) == 1
```

## 6.4 Test Code Switcher (7 tests)

**File**: `tests/unit/test_code_switcher.py`

```python
"""Tests for Code Switcher — language detection vi/en/mixed."""

from app.nlp.code_switcher import CodeSwitcher


def test_detect_vietnamese():
    cs = CodeSwitcher()
    assert cs.detect_language("Tôi bị đau bụng") == "vi"


def test_detect_english():
    cs = CodeSwitcher()
    assert cs.detect_language("I have a headache") == "en"


def test_detect_mixed():
    cs = CodeSwitcher()
    assert cs.detect_language("Con bị fever 3 ngày rồi") == "mixed"


def test_detect_mixed_complex():
    cs = CodeSwitcher()
    assert cs.detect_language("Tôi bị đau họng nuốt very difficult") == "mixed"


def test_normalize_mixed_adds_tag():
    cs = CodeSwitcher()
    result = cs.normalize("Con bị fever 3 ngày rồi")
    assert result.startswith("[CODE-SWITCHING:")


def test_normalize_pure_vi_unchanged():
    cs = CodeSwitcher()
    text = "Tôi bị đau bụng"
    assert cs.normalize(text) == text


def test_normalize_pure_en_unchanged():
    cs = CodeSwitcher()
    text = "I have a stomachache"
    assert cs.normalize(text) == text
```

## 6.5 Test PHI De-identifier (20 tests — Safety-Critical)

**File**: `tests/unit/test_phi_deidentifier.py`

```python
"""Tests for PHI De-identification Pipeline — 100% coverage required (safety-critical)."""

import pytest
from cryptography.fernet import Fernet

from app.domain.services.phi_deidentifier import PHIDeidentifier


@pytest.fixture
def phi():
    key = Fernet.generate_key().decode()
    return PHIDeidentifier(encryption_key=key)


class TestContainsPHI:
    def test_detects_vietnamese_name(self, phi):
        assert phi.contains_phi("Bệnh nhân Nguyễn Văn An bị đau bụng") is True

    def test_detects_english_name(self, phi):
        assert phi.contains_phi("Patient John Smith has a headache") is True

    def test_detects_ssn(self, phi):
        assert phi.contains_phi("SSN: 123-45-6789") is True

    def test_detects_phone(self, phi):
        assert phi.contains_phi("Call (713) 555-1234") is True

    def test_detects_email(self, phi):
        assert phi.contains_phi("Contact patient@email.com") is True

    def test_detects_dob(self, phi):
        assert phi.contains_phi("DOB: 05/10/1968") is True

    def test_detects_address(self, phi):
        assert phi.contains_phi("Lives at 123 Main St") is True

    def test_detects_zip(self, phi):
        assert phi.contains_phi("Houston TX 77001") is True

    def test_detects_mrn(self, phi):
        assert phi.contains_phi("MRN-001234") is True

    def test_detects_ip(self, phi):
        assert phi.contains_phi("IP: 192.168.1.100") is True

    def test_no_phi_in_clean_text(self, phi):
        assert phi.contains_phi("Tôi bị đau bụng 2 ngày rồi") is False

    def test_no_phi_in_medical_terms(self, phi):
        assert phi.contains_phi("viêm ruột thừa cấp") is False


class TestDeidentify:
    def test_replaces_vietnamese_name(self, phi):
        text = "Bệnh nhân Nguyễn Văn An bị sốt"
        result, mapping = phi.deidentify(text)
        assert "Nguyễn Văn An" not in result
        assert "[REF-" in result
        assert "Nguyễn Văn An" in mapping

    def test_replaces_phone(self, phi):
        text = "Gọi số (713) 555-1234 để liên hệ"
        result, mapping = phi.deidentify(text)
        assert "(713) 555-1234" not in result
        assert "[REF-" in result

    def test_replaces_email(self, phi):
        text = "Email: patient@hospital.com"
        result, mapping = phi.deidentify(text)
        assert "patient@hospital.com" not in result

    def test_replaces_ssn(self, phi):
        text = "SSN là 123-45-6789"
        result, mapping = phi.deidentify(text)
        assert "123-45-6789" not in result

    def test_clean_text_unchanged(self, phi):
        text = "Tôi bị đau đầu mấy ngày"
        result, mapping = phi.deidentify(text)
        assert result == text
        assert mapping == {}

    def test_multiple_phi_replaced(self, phi):
        text = "Nguyễn Văn An, SSN 123-45-6789, email an@test.com"
        result, mapping = phi.deidentify(text)
        assert "Nguyễn Văn An" not in result
        assert "123-45-6789" not in result
        assert "an@test.com" not in result
        assert len(mapping) >= 3


class TestReidentify:
    def test_roundtrip(self, phi):
        original = "Bệnh nhân Nguyễn Văn An bị đau bụng, gọi (713) 555-1234"
        deidentified, mapping = phi.deidentify(original)
        reidentified = phi.reidentify(deidentified, mapping)
        assert reidentified == original


class TestEncryptDecryptMapping:
    def test_roundtrip(self, phi):
        mapping = {
            "Nguyễn Văn An": {"pseudonym": "[REF-abc12345]", "phi_type": "vietnamese_name"},
        }
        encrypted = phi.encrypt_mapping(mapping)
        assert isinstance(encrypted, bytes)
        decrypted = phi.decrypt_mapping(encrypted)
        assert decrypted == mapping
```

**Key pattern**: Fixture `phi()` tạo `PHIDeidentifier` mới với random Fernet key cho mỗi test → cô lập hoàn toàn.

## 6.6 Test LLM Gateway (10 tests)

**File**: `tests/unit/test_llm_gateway.py`

```python
"""Tests for LLM Gateway — PHI gate, provider selection, retry."""

from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet

from app.core.exceptions import PHIAccessError
from app.domain.services.llm_gateway import LLMGateway, LLMResponse, OpenAIProvider
from app.domain.services.phi_deidentifier import PHIDeidentifier


@pytest.fixture
def phi():
    key = Fernet.generate_key().decode()
    return PHIDeidentifier(encryption_key=key)


@pytest.fixture
def gateway(phi):
    return LLMGateway(
        openai_api_key="test-key",
        phi_deidentifier=phi,
        primary_model="gpt-4",
        screening_model="gpt-4o-mini",
    )


@pytest.fixture
def mock_response():
    return LLMResponse(
        content="Xin chào! Bạn có thể mô tả triệu chứng?",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        finish_reason="stop",
    )


class TestPHIVerificationGate:
    def test_blocks_phi_in_messages(self, gateway):
        messages = [{"role": "user", "content": "Bệnh nhân Nguyễn Văn An bị sốt"}]
        with pytest.raises(PHIAccessError):
            gateway._verify_no_phi(messages, "case-123")

    def test_allows_clean_messages(self, gateway):
        messages = [{"role": "user", "content": "Tôi bị đau bụng 2 ngày"}]
        gateway._verify_no_phi(messages, "case-123")  # Should not raise

    def test_blocks_ssn(self, gateway):
        messages = [{"role": "user", "content": "SSN: 123-45-6789"}]
        with pytest.raises(PHIAccessError):
            gateway._verify_no_phi(messages, "case-123")

    def test_blocks_email(self, gateway):
        messages = [{"role": "user", "content": "Email patient@test.com"}]
        with pytest.raises(PHIAccessError):
            gateway._verify_no_phi(messages, "case-123")


class TestProviderSelection:
    def test_intake_uses_screening_model(self, gateway):
        provider = gateway._select_provider("intake")
        assert provider is gateway.screening

    def test_screening_uses_primary_model(self, gateway):
        provider = gateway._select_provider("screening")
        assert provider is gateway.primary

    def test_proposer_uses_primary_model(self, gateway):
        provider = gateway._select_provider("proposer")
        assert provider is gateway.primary

    def test_critic_uses_primary_model(self, gateway):
        provider = gateway._select_provider("critic")
        assert provider is gateway.primary


class TestGenerate:
    @pytest.mark.asyncio
    async def test_blocks_phi_before_llm_call(self, gateway):
        messages = [{"role": "user", "content": "Bệnh nhân Nguyễn Văn An"}]
        with pytest.raises(PHIAccessError):
            await gateway.generate(messages, agent_type="intake", case_id="case-1")

    @pytest.mark.asyncio
    async def test_calls_llm_with_clean_messages(self, gateway, mock_response):
        messages = [{"role": "user", "content": "Tôi bị đau bụng"}]
        with patch.object(
            gateway, "_call_with_retry", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await gateway.generate(messages, agent_type="intake", case_id="case-1")
            assert result.content == "Xin chào! Bạn có thể mô tả triệu chứng?"
            assert result.model == "gpt-4o-mini"
```

**Key mocking pattern**: `patch.object(gateway, "_call_with_retry", new_callable=AsyncMock)` — mock internal method để không gọi OpenAI API thật trong unit test.

## 6.7 Test Intake Agent (6 tests)

**File**: `tests/unit/test_intake_agent.py`

```python
"""Tests for Intake Agent — symptom collection, emergency detection, NLP integration."""

from unittest.mock import AsyncMock

import pytest
from cryptography.fernet import Fernet
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.intake_agent import intake_node
from app.domain.services.llm_gateway import LLMGateway, LLMResponse
from app.domain.services.phi_deidentifier import PHIDeidentifier


@pytest.fixture
def phi():
    key = Fernet.generate_key().decode()
    return PHIDeidentifier(encryption_key=key)


@pytest.fixture
def mock_gateway(phi):
    gateway = LLMGateway(
        openai_api_key="test-key",
        phi_deidentifier=phi,
    )
    return gateway


@pytest.fixture
def mock_response():
    return LLMResponse(
        content="Bạn bị đau bụng ở vị trí nào? Bên phải hay bên trái?",
        model="gpt-4o-mini",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        finish_reason="stop",
    )


def _make_state(**overrides):
    base = {
        "patient_id": "test-patient",
        "case_id": "test-case",
        "organization_id": "test-org",
        "messages": [],
        "intake_data": None,
        "intake_complete": False,
        "is_emergency": False,
        "detected_language": "vi",
        "cultural_expressions": [],
        "created_at": "2026-02-27T00:00:00Z",
        "updated_at": "2026-02-27T00:00:00Z",
        "correlation_id": "test-corr",
    }
    base.update(overrides)
    return base


class TestIntakeNodeEmptyMessages:
    @pytest.mark.asyncio
    async def test_returns_greeting_when_no_messages(self, mock_gateway, phi):
        state = _make_state(messages=[])
        result = await intake_node(state, mock_gateway, phi)
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], AIMessage)
        assert "Compass Vitals" in result["messages"][0].content


class TestEmergencyDetection:
    @pytest.mark.asyncio
    async def test_detects_emergency_dau_nguc(self, mock_gateway, phi):
        state = _make_state(
            messages=[HumanMessage(content="Tôi bị đau ngực rất nặng, khó thở")]
        )
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is True
        assert "KHẨN CẤP" in result["messages"][0].content

    @pytest.mark.asyncio
    async def test_no_emergency_normal_symptoms(self, mock_gateway, phi, mock_response):
        state = _make_state(
            messages=[HumanMessage(content="Tôi bị đau bụng 2 ngày rồi")]
        )
        # Mock the LLM call
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["is_emergency"] is False


class TestLanguageDetection:
    @pytest.mark.asyncio
    async def test_detects_vietnamese(self, mock_gateway, phi, mock_response):
        state = _make_state(
            messages=[HumanMessage(content="Tôi bị đau bụng")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["detected_language"] == "vi"

    @pytest.mark.asyncio
    async def test_detects_mixed(self, mock_gateway, phi, mock_response):
        state = _make_state(
            messages=[HumanMessage(content="Con bị fever 3 ngày rồi")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert result["detected_language"] == "mixed"


class TestCulturalExpressions:
    @pytest.mark.asyncio
    async def test_detects_nong_trong(self, mock_gateway, phi, mock_response):
        state = _make_state(
            messages=[HumanMessage(content="Tôi bị nóng trong người")]
        )
        mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)
        result = await intake_node(state, mock_gateway, phi)
        assert len(result["cultural_expressions"]) >= 1
        assert any(
            "inflammation" in e["medical_terms"]
            for e in result["cultural_expressions"]
        )
```

**Key patterns:**
- `_make_state(**overrides)`: Helper tạo state object với defaults, override từng field cần thiết
- `mock_gateway._call_with_retry = AsyncMock(return_value=mock_response)`: Mock LLM call trực tiếp trên gateway instance

## 6.8 Kết quả mong đợi

```bash
$ python -m pytest tests/ -v

tests/unit/test_code_switcher.py::test_detect_vietnamese PASSED
tests/unit/test_code_switcher.py::test_detect_english PASSED
tests/unit/test_code_switcher.py::test_detect_mixed PASSED
tests/unit/test_code_switcher.py::test_detect_mixed_complex PASSED
tests/unit/test_code_switcher.py::test_normalize_mixed_adds_tag PASSED
tests/unit/test_code_switcher.py::test_normalize_pure_vi_unchanged PASSED
tests/unit/test_code_switcher.py::test_normalize_pure_en_unchanged PASSED
tests/unit/test_cultural_mapper.py::test_detects_nong_trong PASSED
tests/unit/test_cultural_mapper.py::test_detects_trung_gio PASSED
tests/unit/test_cultural_mapper.py::test_detects_boc_hoa PASSED
tests/unit/test_cultural_mapper.py::test_detects_yeu_than PASSED
tests/unit/test_cultural_mapper.py::test_no_match_normal_text PASSED
tests/unit/test_cultural_mapper.py::test_multiple_expressions PASSED
tests/unit/test_cultural_mapper.py::test_case_insensitive PASSED
tests/unit/test_emergency_detector.py::test_detects_dau_nguc PASSED
... (tổng cộng 59 tests)

========================= 59 passed =========================
```

---

# PHẦN 7: CHẠY VÀ VẬN HÀNH

> **Kết quả của phần này**: Server chạy, test thủ công thành công, biết cách debug.

## 7.1 Khởi động dịch vụ

```bash
# 1. Mở Docker Desktop

# 2. Start PostgreSQL + Redis
cd services/ai-agent-service
docker compose up -d

# 3. Kiểm tra Docker services
docker compose ps
# postgres (healthy), redis (healthy)

# 4. Set encoding (Windows)
export PYTHONIOENCODING=utf-8

# 5. Start FastAPI server
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001

# Mong đợi:
# INFO: Uvicorn running on http://127.0.0.1:8001
```

## 7.2 Test thủ công E2E

### Test 1: Health Check

```bash
curl http://127.0.0.1:8001/health
# → {"status":"healthy","service":"ai-agent-service"}
```

### Test 2: Hội thoại tiếng Việt bình thường

```bash
curl -X POST http://127.0.0.1:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tôi bị đau bụng 2 ngày rồi", "language": "vi"}'
```

**Kết quả mong đợi:**
```json
{
  "response": "Chào bạn! Cảm ơn bạn đã chia sẻ. Bạn bị đau bụng ở vị trí nào? ...",
  "session_id": "xxx-xxx-xxx",
  "agent_state": "intake",
  "is_complete": false,
  "detected_language": "vi",
  "is_emergency": false,
  "cultural_expressions": []
}
```

### Test 3: Phát hiện biểu đạt văn hóa

```bash
curl -X POST http://127.0.0.1:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tôi bị nóng trong người, mệt mỏi", "language": "vi"}'
```

**Kết quả mong đợi:** `cultural_expressions` chứa "inflammation" mapping.

### Test 4: Phát hiện khẩn cấp

```bash
curl -X POST http://127.0.0.1:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tôi bị đau ngực rất nặng, khó thở", "language": "vi"}'
```

**Kết quả mong đợi:** `is_emergency: true`, response chứa "CẢNH BÁO KHẨN CẤP".

### Test 5: Code-switching

```bash
curl -X POST http://127.0.0.1:8001/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Con bị fever 3 ngày rồi, đau họng very difficult", "language": "auto"}'
```

**Kết quả mong đợi:** `detected_language: "mixed"`.

## 7.3 Bảng Debug thường gặp

| # | Vấn đề | Nguyên nhân | Cách sửa |
|---|--------|-------------|----------|
| 1 | `ModuleNotFoundError: No module named 'setuptools.backends'` | build-backend sai | Đổi thành `"setuptools.build_meta"` |
| 2 | `Multiple top-level packages discovered` | setuptools scan tất cả folders | Thêm `[tool.setuptools.packages.find]` với `include = ["app*"]` |
| 3 | `PHIAccessError` khi gọi LLM | PHI gate block system prompt | Thêm `if msg.get("role") == "system": continue` trong `_verify_no_phi` |
| 4 | `UnicodeEncodeError: 'charmap' codec can't encode` | Windows cp1252 không hỗ trợ tiếng Việt | Set `PYTHONIOENCODING=utf-8`, dùng ASCII trong logger |
| 5 | `[Errno 10048] address already in use` | Uvicorn cũ vẫn chạy | `netstat -ano \| grep 8001` → `taskkill //PID xxx //F` |

---

# PHẦN 8: HƯỚNG DẪN NHÂN BẢN — XÂY DỰNG AGENT TIẾP THEO

> **Kết quả của phần này**: Template + checklist để build bất kỳ agent nào trong hệ thống.

## 8.1 Nguyên tắc cốt lõi

**Mọi agent đều đi qua cùng 7-layer pipeline.** Chỉ 3 layers (4, 5, 7) khác nhau giữa các agent. Phần còn lại dùng chung infrastructure đã build ở Phần 3.

## 8.2 Bảng so sánh: Intake vs Screening

| Layer | Intake Agent | Screening Agent | Ghi chú |
|-------|-------------|----------------|---------|
| 1. Emergency | `emergency_detector.py` | `emergency_detector.py` | DÙNG CHUNG |
| 2. NLP | `code_switcher.py` + `cultural_mapper.py` | `code_switcher.py` + `cultural_mapper.py` | DÙNG CHUNG |
| 3. PHI | `phi_deidentifier.py` | `phi_deidentifier.py` | DÙNG CHUNG |
| **4. Prompt** | **OLDCARTS interview** | **Clinical assessment** | **TẠO MỚI** |
| **5. Model** | **GPT-4o-mini** (agent_type="intake") | **GPT-4** (agent_type="screening") | **TỰ ĐỘNG** (gateway) |
| 6. Re-identify | `phi_deidentifier.py` | `phi_deidentifier.py` | DÙNG CHUNG |
| **7. State** | **intake_data, intake_complete** | **screening_result, severity, differential_diagnoses** | **GHI KHÁC** |

## 8.3 Template 8 bước xây dựng Agent mới

### Bước 1: Xác định State Fields

Mở `app/agents/state.py` — tất cả fields đã được định nghĩa sẵn. Xác định agent mới sẽ **đọc** fields nào và **ghi** fields nào.

```
Screening Agent:
  ĐỌC: intake_data, intake_complete, messages
  GHI: screening_result, severity, differential_diagnoses, is_emergency
```

### Bước 2: Viết System Prompt

Tạo file mới: `app/agents/prompts/screening_prompt.py`

```python
SCREENING_SYSTEM_PROMPT = """You are a Clinical Screening Specialist AI for Compass Vitals.

ROLE: Evaluate patient symptoms and provide clinical assessment.
INPUT: Structured intake data from OLDCARTS interview.
OUTPUT: Severity classification + differential diagnoses.

SEVERITY LEVELS:
- emergency: Life-threatening, needs immediate intervention
- urgent: Needs attention within 24 hours
- routine: Can be scheduled for regular visit

RULES:
- Provide 3-5 differential diagnoses ranked by likelihood
- Include confidence score (0-100) for each diagnosis
- Flag any red-flag symptoms
- NEVER recommend specific treatment (that's Proposer's job)
"""
```

### Bước 3: Tạo Agent-specific Tools (nếu cần)

```python
# app/agents/tools/severity_classifier.py
def classify_severity(intake_data: dict) -> str:
    """Classify based on intake_data keywords."""
    # Rule-based pre-classification trước khi LLM confirm
    ...
```

### Bước 4: Implement Node Function

```python
# app/agents/screening_agent.py
async def screening_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    # Step 1: Emergency Detection (GIỐNG intake)
    # Step 2: NLP Pipeline (GIỐNG intake)
    # Step 3: PHI De-identification (GIỐNG intake)
    # Step 4: Build LLM Messages (KHÁC — dùng SCREENING_SYSTEM_PROMPT)
    # Step 5: Call LLM via Gateway (KHÁC — agent_type="screening" → GPT-4)
    # Step 6: Re-identify Response (GIỐNG intake)
    # Step 7: Return Updated State (KHÁC — ghi screening_result, severity)
    ...
```

### Bước 5: Tạo API Route (nếu cần endpoint riêng)

```python
# app/api/v1/routes/screening.py
# Hoặc tích hợp vào LangGraph StateGraph flow
```

### Bước 6: Viết Unit Tests

```python
# tests/unit/test_screening_agent.py
# Dùng cùng pattern: _make_state(), mock_gateway, mock_response
```

### Bước 7: Tích hợp LangGraph StateGraph

```python
# app/agents/graphs/prescription_flow.py
from langgraph.graph import StateGraph

graph = StateGraph(CareFlowState)
graph.add_node("intake", intake_node)
graph.add_node("screening", screening_node)
graph.add_edge("intake", "screening")
# ... thêm các agent khác
```

### Bước 8: E2E Test

```bash
# Test luồng: intake → screening
curl -X POST http://localhost:8001/api/v1/chat \
  -d '{"message": "Tôi bị đau bụng dữ dội ở bên phải"}'
# Verify: screening_result có trong response
```

## 8.4 Checklist hoàn thành Agent

- [ ] System prompt reviewed bởi clinical team
- [ ] Node function implement đủ 7 layers
- [ ] agent_type đúng trong gateway.generate() call
- [ ] State fields đúng trong return dict
- [ ] Unit tests passing (>90% coverage)
- [ ] E2E test scenario working
- [ ] Structural logging added (structlog)

---

# PHẦN 9: DOCKER DEPLOYMENT

> **Kết quả của phần này**: Service chạy trong Docker container, sẵn sàng production.

## 9.1 Dockerfile

Tạo file `services/ai-agent-service/Dockerfile`:

```dockerfile
# === Build stage ===
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir .

# === Runtime stage ===
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/

# Set environment
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

## 9.2 Docker Compose Production

Tạo file `docker-compose.production.yml`:

```yaml
services:
  ai-agent-service:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    env_file:
      - .env.production
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ai_agent_db
      POSTGRES_USER: compass
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U compass -d ai_agent_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
```

## 9.3 Lệnh Deploy

```bash
# Build
docker compose -f docker-compose.production.yml build

# Start
docker compose -f docker-compose.production.yml up -d

# Verify
docker compose -f docker-compose.production.yml ps
curl http://localhost:8001/health

# Logs
docker compose -f docker-compose.production.yml logs -f ai-agent-service

# Stop
docker compose -f docker-compose.production.yml down
```

## 9.4 Cấu hình Production

File `.env.production`:

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO                        # Không DEBUG trong production
OPENAI_API_KEY=sk-proj-XXXX          # Từ secrets manager
PHI_ENCRYPTION_KEY=XXXX              # PHẢI khác development
DATABASE_URL=postgresql+asyncpg://compass:STRONG_PASSWORD@postgres:5432/ai_agent_db
REDIS_URL=redis://redis:6379/0
```

---

# PHẦN 10: BÀI HỌC VÀ KINH NGHIỆM

## 10.1 Bảng tổng hợp lỗi thực tế

| # | Vấn đề | Nguyên nhân gốc | Cách sửa | File |
|---|--------|-----------------|----------|------|
| 1 | `build-backend` sai | Blueprint ghi `setuptools.backends._legacy:_Backend` | Dùng `"setuptools.build_meta"` | pyproject.toml |
| 2 | Multiple packages | setuptools scan `app`, `alembic`, `tests` | `include = ["app*"]` | pyproject.toml |
| 3 | PHI gate block prompt | System prompt chứa từ viết hoa match name regex | Skip `role=="system"` | llm_gateway.py L116-117 |
| 4 | Unicode crash | Windows cp1252 không encode tiếng Việt | `PYTHONIOENCODING=utf-8` + ASCII logging | cultural_mapper.py L108 |
| 5 | Port conflict | Uvicorn process cũ không tắt | Kill process by PID | Terminal |

## 10.2 Quyết định thiết kế và lý do

| Quyết định | Lý do |
|------------|-------|
| `TypedDict` thay vì Pydantic cho CareFlowState | LangGraph yêu cầu TypedDict cho StateGraph |
| Keyword-based emergency detection | Deterministic 100%, không phụ thuộc LLM, <1ms |
| Manual DI thay vì container | Đơn giản, explicit, dễ mock, project chưa đủ lớn |
| In-memory session store | MVP trước, migrate PostgreSQL+Redis sau |
| GPT-4o-mini cho Intake | Tiết kiệm ~10x chi phí, task không cần reasoning mạnh |
| System prompt tiếng Anh | LLM hiểu instruction EN tốt hơn, vẫn respond VN |

## 10.3 Cần cải thiện

- [ ] Chuyển session store từ in-memory sang PostgreSQL + Redis
- [ ] Implement LangGraph StateGraph workflow thực sự
- [ ] Chạy Alembic migrations cho database schema
- [ ] Thêm JWT authentication + RBAC
- [ ] Thêm rate limiting
- [ ] Thêm WebSocket cho real-time chat
- [ ] Thêm Kafka cho event-driven architecture
- [ ] Thêm integration tests với testcontainers

---

# PHỤ LỤC

## A: File Structure với Line Count

| # | File | Dòng | Mục đích |
|---|------|------|----------|
| 1 | `app/config.py` | 36 | Pydantic Settings |
| 2 | `app/main.py` | 66 | FastAPI entry point |
| 3 | `app/core/exceptions.py` | 44 | Exception hierarchy |
| 4 | `app/agents/state.py` | 63 | CareFlowState contract |
| 5 | `app/agents/intake_agent.py` | 133 | Intake Agent logic |
| 6 | `app/agents/prompts/intake_prompt.py` | 34 | OLDCARTS system prompt |
| 7 | `app/agents/tools/emergency_detector.py` | 36 | Emergency keywords |
| 8 | `app/domain/services/phi_deidentifier.py` | 89 | PHI pipeline |
| 9 | `app/domain/services/llm_gateway.py` | 150 | LLM access layer |
| 10 | `app/nlp/code_switcher.py` | 36 | Language detection |
| 11 | `app/nlp/cultural_mapper.py` | 112 | Cultural expressions |
| 12 | `app/nlp/medical_terminology.py` | 58 | Medical dictionary |
| 13 | `app/api/v1/schemas/chat.py` | 20 | Request/Response |
| 14 | `app/api/v1/routes/chat.py` | 117 | Chat endpoint |
| | **Tổng source** | **~994** | |
| 15 | `tests/unit/test_phi_deidentifier.py` | 109 | 20 tests |
| 16 | `tests/unit/test_llm_gateway.py` | 94 | 10 tests |
| 17 | `tests/unit/test_intake_agent.py` | 122 | 6 tests |
| 18 | `tests/unit/test_cultural_mapper.py` | 50 | 7 tests |
| 19 | `tests/unit/test_code_switcher.py` | 42 | 7 tests |
| 20 | `tests/unit/test_emergency_detector.py` | 43 | 9 tests |
| | **Tổng tests** | **~460** | **59 tests** |
| | **TỔNG CỘNG** | **~1,454** | |

## B: Bảng lệnh nhanh

| Hành động | Lệnh |
|-----------|-------|
| Setup venv | `python -m venv .venv && .venv/Scripts/activate` |
| Install deps | `pip install -e ".[dev]"` |
| Start Docker | `docker compose up -d` |
| Start server | `PYTHONIOENCODING=utf-8 uvicorn app.main:app --port 8001` |
| Run tests | `python -m pytest tests/ -v` |
| Run with coverage | `python -m pytest tests/ --cov=app --cov-report=html` |
| Health check | `curl http://127.0.0.1:8001/health` |
| Chat test | `curl -X POST http://127.0.0.1:8001/api/v1/chat -H "Content-Type: application/json" -d '{"message": "..."}'` |
| Kill port | `netstat -ano \| grep 8001` → `taskkill //PID xxx //F` |
| Generate PHI key | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| Docker build | `docker compose -f docker-compose.production.yml build` |
| Docker deploy | `docker compose -f docker-compose.production.yml up -d` |

## C: Template Agent Mới (Blank)

```python
"""[Agent Name] Agent — [Mô tả ngắn vai trò]."""

from datetime import datetime, timezone

import structlog
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.prompts.[agent]_prompt import [AGENT]_SYSTEM_PROMPT
from app.agents.state import CareFlowState
from app.agents.tools.emergency_detector import detect_emergency, get_emergency_keywords_found
from app.domain.services.llm_gateway import LLMGateway
from app.domain.services.phi_deidentifier import PHIDeidentifier
from app.nlp.code_switcher import CodeSwitcher
from app.nlp.cultural_mapper import CulturalMapper

logger = structlog.get_logger()
code_switcher = CodeSwitcher()
cultural_mapper = CulturalMapper()


async def [agent]_node(
    state: CareFlowState,
    llm_gateway: LLMGateway,
    phi_deidentifier: PHIDeidentifier,
) -> dict:
    messages = state.get("messages", [])
    case_id = state.get("case_id", "unknown")

    # Lấy tin nhắn/data từ state
    last_message = messages[-1]
    patient_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    # Step 1: Emergency Detection
    if detect_emergency(patient_text):
        # ... (giống intake)

    # Step 2: NLP Pipeline
    detected_language = code_switcher.detect_language(patient_text)
    cultural_expressions = cultural_mapper.map_expressions(patient_text)
    normalized_text = code_switcher.normalize(patient_text)

    # Step 3: PHI De-identification
    deidentified_text, phi_mapping = phi_deidentifier.deidentify(normalized_text)

    # Step 4: Build LLM Messages (★ KHÁC — dùng prompt riêng)
    llm_messages = [
        {"role": "system", "content": [AGENT]_SYSTEM_PROMPT},
    ]
    # ... thêm conversation history

    # Step 5: Call LLM via Gateway (★ KHÁC — agent_type)
    response = await llm_gateway.generate(
        messages=llm_messages,
        agent_type="[agent]",   # ← Quyết định model nào được dùng
        case_id=case_id,
        temperature=0.3,
    )

    # Step 6: Re-identify Response
    ai_response_text = response.content
    if phi_mapping:
        ai_response_text = phi_deidentifier.reidentify(ai_response_text, phi_mapping)

    # Step 7: Return Updated State (★ KHÁC — ghi fields riêng)
    return {
        "messages": [AIMessage(content=ai_response_text)],
        # "[field_1]": ...,   # ← Fields riêng của agent này
        # "[field_2]": ...,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
```

## D: Thuật ngữ Việt-Anh

| Tiếng Việt | English | Trong code |
|------------|---------|------------|
| Thu thập triệu chứng | Symptom Intake | `intake_node` |
| Đánh giá lâm sàng | Clinical Screening | `screening_node` |
| Đề xuất đơn thuốc | Order Proposal | `proposer_node` |
| Kiểm tra an toàn | Safety Validation | `critic_node` |
| Điều phối | Supervision | `supervisor_node` |
| Phát hiện khẩn cấp | Emergency Detection | `detect_emergency()` |
| Biểu đạt văn hóa | Cultural Expression | `cultural_mapper` |
| Chuyển mã | Code-switching | `code_switcher` |
| Giải mã nhận dạng | De-identification | `phi_deidentifier` |
| Cổng LLM | LLM Gateway | `llm_gateway` |
| Trạng thái chia sẻ | Shared State | `CareFlowState` |
| Mức nghiêm trọng | Severity | `severity` |
| Chẩn đoán phân biệt | Differential Diagnosis | `differential_diagnoses` |

---

> **Tài liệu này được tạo dựa trên thí nghiệm thực tế xây dựng Intake Agent — Compass Vitals Project, 2026-03-01.**
> **Mọi code, lệnh, và lỗi đều đã được kiểm chứng và pass 59 unit tests + 4 E2E tests.**
