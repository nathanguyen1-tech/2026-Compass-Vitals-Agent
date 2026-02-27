---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/research/technical-ai-agent-frameworks-medical-healthcare-research-2026-02-24.md'
  - 'docs/service-3-access-to-care-247-high-level-flow.md'
workflowType: 'architecture'
lastStep: 8
status: 'complete'
completedAt: '2026-02-26'
project_name: '2026-Compass_Vitals_Agent'
user_name: 'AN-AI'
date: '2026-02-26'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
100 FRs across 13 capability areas defining a comprehensive AI-first telemedicine platform. Architecturally, these divide into 5 major subsystems:

1. **AI Agent Subsystem** (FR9-16, FR97-100): Multi-agent orchestration with Intake, Screening, Proposer, Critic agents + Vietnamese NLP pipeline. Requires LangGraph workflow engine, LLM integration layer (GPT-4 primary + Claude backup), confidence scoring, and cultural expression mapping database.

2. **Clinical Workflow Engine** (FR32-38): 4 parallel care flows (Emergency/Prescription/Lab/Monitoring) sharing common 7-station intake path, then diverging to flow-specific processing. Requires state machine implementation, event-driven transitions (Kafka), SLA timer enforcement, and 3-Stage Order Lifecycle (Recommendations → Draft → Actual).

3. **User Portal Subsystem** (FR1-8, FR17-24, FR25-31, FR58-64): Three distinct interfaces - Patient Portal (bilingual chat, care plan viewing), VN MD Dashboard (priority queue, draft order creation), US MD Dashboard (unified review, prescription signing). Requires role-based UI rendering and real-time data synchronization.

4. **Compliance & Security Layer** (FR65-78): Cross-cutting infrastructure including RBAC at 3 levels (API gateway, service, database), PHI encryption (AES-256/TLS 1.3), audit logging (100% coverage), PHI de-identification for LLM calls, US-only data residency, and consent management.

5. **Integration Hub** (FR39-51, FR79-84): External system connections including SureScripts (e-prescribing), Stripe (billing), Auth0/Cognito (identity), Twilio (SMS), FHIR R4 (data models). Phase 2 adds Epic/Cerner, LabCorp/Quest.

**Non-Functional Requirements:**
22 NFRs across 7 categories driving critical architectural decisions:

- **Performance** (NFR-P1-P5): <2s AI response, <500ms FHIR API, 500+ concurrent sessions → requires async architecture, connection pooling, CDN
- **Security** (NFR-S1-S5): Zero-trust, mTLS service mesh (Istio), VPN for VN MD access → foundational network architecture constraint
- **Scalability** (NFR-SC1-SC4): 500 → 10,000 users, 1,000+ LLM requests/min, multi-region ready → Kubernetes horizontal autoscaling, LLM rate limit management
- **Reliability** (NFR-R1-R4): 99.9% uptime, multi-AZ deployment, Kafka replication factor 3 → high availability architecture pattern
- **Compliance** (NFR-C1-C5): HIPAA, FDA SaMD, state licensing, data residency, BAAs → compliance-as-code approach required
- **Accessibility** (NFR-A1-A3): Vietnamese language first, elderly-friendly UI, WCAG deferred → cultural accessibility over general accessibility

**Scale & Complexity:**

- Primary domain: Full-stack AI-powered Healthcare SaaS Platform
- Complexity level: **Enterprise** (multi-agent AI + healthcare regulatory + cross-border operations + 4 parallel care flows)
- Estimated architectural components: ~15-20 microservices + 4-6 AI agents + 3 frontend apps + integration adapters

### Technical Constraints & Dependencies

1. **US-Only PHI Storage**: All patient data must reside in US cloud regions (HIPAA) → Cloud provider selection constrained to AWS/GCP HIPAA-eligible regions
2. **Cross-Border Access**: VN MD in Vietnam accessing US-based systems → VPN + mTLS mandatory, latency considerations (US-Vietnam ~200ms RTT)
3. **LLM API Dependencies**: GPT-4 + Claude external API calls → PHI de-identification pipeline required before every LLM call, rate limiting, cost management
4. **FHIR R4 Compliance**: July 2026 mandate → data models must be FHIR-native from day 1 (Patient, MedicationRequest, DiagnosticReport, CarePlan, Encounter, Observation)
5. **FDA SaMD Classification**: AI recommendations positioning as Clinical Decision Support → architecture must ensure "human in the loop" is enforced (not bypassable)
6. **State Medical Licensing**: US MD license verification per patient state → geographic routing engine required
7. **SureScripts Certification**: 3-6 month certification process → integration architecture needs early planning
8. **Kafka Event Ordering**: Care flow state transitions require strict ordering guarantees → partition key strategy critical
9. **Zero-Trust Mandate**: HIPAA 2026 updates → Istio service mesh mandatory, no implicit trust between services

### Cross-Cutting Concerns Identified

1. **Security & PHI Protection**: Every microservice must implement authentication, authorization, PHI encryption, and audit logging - not optional in any component
2. **Audit Trail**: Immutable, append-only logging of 100% PHI access across all services (7-year retention) → centralized logging infrastructure (ELK/CloudWatch)
3. **Multi-Tenancy**: Patient-level data isolation via PostgreSQL Row-Level Security → every query must include tenant context
4. **Event-Driven Architecture**: Kafka as backbone for care flow state transitions, notification dispatch, async processing → event schema governance needed
5. **AI Agent Orchestration**: LangGraph workflows span multiple services → agent state management, error recovery, human handoff points
6. **Vietnamese NLP**: Cultural expression mapping + code-switching affects all patient-facing AI interactions → centralized NLP service
7. **SLA Enforcement**: Tier-based priority queuing (Premium/Plus/Connect) → queue management, timer services, escalation workflows
8. **Error Handling**: Healthcare requires graceful degradation (never lose patient data, never block emergency flow) → circuit breakers, retry patterns, fallback workflows
9. **Observability**: Healthcare compliance requires comprehensive monitoring → distributed tracing, metrics, alerting for SLA violations

## Starter Template Evaluation

### Primary Technology Domain

**Full-stack AI-powered Healthcare Microservices Platform** — yêu cầu multi-component architecture:
- Backend API (FastAPI microservices)
- AI Agent orchestration (LangGraph)
- Frontend web apps (React — Patient Portal + MD Dashboards)
- Infrastructure (PostgreSQL, Redis, Kafka, Kubernetes, Istio)

### Starter Options Considered

**Option 1: Official Full Stack FastAPI Template** (fastapi.tiangolo.com)
- FastAPI 0.133.0 + SQLModel + PostgreSQL + React frontend
- Docker Compose, Traefik proxy, JWT auth
- Pros: Official, well-maintained, production patterns
- Cons: No Kafka, no AI agent setup, no HIPAA-specific controls, no FHIR

**Option 2: FastAPI-LangGraph Agent Production-Ready Template** (wassim249/fastapi-langgraph-agent-production-ready-template)
- FastAPI + LangGraph integration, GPT-4o/GPT-5 support, retry logic
- Pros: AI agent + API in one template, production patterns
- Cons: Single-service (not microservices), no PostgreSQL FHIR, no Kafka, no healthcare compliance

**Option 3: LangGraph Starter Kit** (ac12644/langgraph-starter-kit)
- Swarm + Supervisor patterns, memory management, HTTP endpoints
- Pros: Multi-agent patterns ready (Swarm = peer specialists, Supervisor = orchestrator)
- Cons: HTTP only (no Kafka), no FastAPI, no healthcare compliance

**Option 4: FastAPI Backend Starter Kit** (shiningflash/fastapi-backend-starter-kit)
- FastAPI + PostgreSQL + Celery + Redis + Docker + Alembic + Pytest
- Pros: Mature backend patterns, async, database migrations, testing
- Cons: No Kafka (uses Celery), no AI agents, no FHIR, no HIPAA

### Selected Starter: Custom Composite Starter

**Rationale for Selection:**

No single starter template on the market satisfies the unique combination of requirements for this healthcare AI platform:
1. Multi-agent AI orchestration (LangGraph) + Healthcare microservices (FastAPI)
2. FHIR-native data models + HIPAA compliance-by-design
3. Event-driven architecture (Kafka) + Zero-trust security (Istio)
4. 3 distinct frontend apps (Patient Portal + VN MD Dashboard + US MD Dashboard)

Custom composite approach cherry-picks best practices from researched templates while ensuring healthcare compliance from day 1.

**Initialization Approach:**

```bash
# Backend Microservices Scaffold
# Python 3.13+ | FastAPI 0.133.0 | LangGraph 1.0 | PostgreSQL 16 | Kafka

# Project structure initialization
mkdir -p compass-vitals/{services/{api-gateway,patient-service,clinical-workflow-service,ai-agent-service,prescription-service,lab-service,monitoring-service,notification-service,compliance-service},frontend/{patient-portal,vnmd-dashboard,usmd-dashboard},infrastructure/{docker,kubernetes,istio},shared/{fhir-models,security,events}}

# Python environment setup
python -m venv .venv && source .venv/bin/activate
pip install "fastapi[standard]>=0.133.0" "langgraph>=1.0" sqlalchemy alembic asyncpg "confluent-kafka" redis pydantic "fhir.resources" cryptography python-jose passlib

# Frontend setup (each app)
npm create vite@latest patient-portal -- --template react-ts
npm create vite@latest vnmd-dashboard -- --template react-ts
npm create vite@latest usmd-dashboard -- --template react-ts

# Infrastructure
docker compose up -d postgres redis kafka zookeeper
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- Python 3.13+ with full async/await (backend services)
- TypeScript 5.x with strict mode (frontend apps)
- Node.js 22 LTS (frontend tooling)

**Backend Framework:**
- FastAPI 0.133.0 with Pydantic v2 models
- SQLAlchemy 2.x async ORM + Alembic migrations
- AsyncPG for PostgreSQL connection pooling

**AI Agent Framework:**
- LangGraph 1.0 GA — graph-based workflow orchestration
- Supervisor pattern (central coordinator) + specialized medical agents
- Node caching + deferred nodes for complex multi-step workflows

**Data Layer:**
- PostgreSQL 16 with Row-Level Security (RLS) for multi-tenancy
- FHIR R4 native data models (fhir.resources library)
- Redis for session management + caching
- Apache Kafka for event-driven state transitions

**Frontend Stack:**
- React 19 + TypeScript + Vite 6
- 3 separate SPAs (Patient Portal, VN MD Dashboard, US MD Dashboard)
- TailwindCSS for styling
- React Query for server state management

**Testing Framework:**
- pytest + pytest-asyncio (backend)
- Vitest + React Testing Library (frontend)
- Integration tests with testcontainers (PostgreSQL, Kafka, Redis)

**Infrastructure:**
- Docker Compose (local development)
- Kubernetes manifests (production)
- Istio service mesh config (mTLS, zero-trust)
- GitHub Actions CI/CD pipelines

**Note:** Project initialization using this scaffold should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- FHIR data modeling strategy (hybrid relational + JSONB)
- PHI de-identification for LLM calls (structured separation)
- Cloud provider selection (AWS)
- Identity provider (AWS Cognito)
- Inter-service communication pattern (hybrid REST + Kafka)

**Important Decisions (Shape Architecture):**
- Order lifecycle state management (hybrid DB + Kafka events)
- API gateway pattern (Istio Ingress)
- VN MD secure access (ZTNA)
- Frontend state management (React Query + Zustand)
- Observability stack (OpenTelemetry + Grafana)

**Deferred Decisions (Post-MVP):**
- Multi-region deployment topology (Phase 2)
- CDN strategy for static assets (Phase 2)
- Advanced caching layers beyond Redis (when scale demands)

### Data Architecture

**FHIR Data Modeling: Hybrid Relational + JSONB**
- Rationale: PostgreSQL relational tables modeled after FHIR resources (patient, medication_request, diagnostic_report, observation, care_plan, encounter) with JSONB columns for FHIR extensions and non-standard attributes
- Benefit: Efficient SQL queries for clinical workflows (JOINs, indexes, RLS) + FHIR R4 API compliance for interoperability (July 2026 mandate)
- Affects: All services that touch patient data, FHIR API layer, database migrations

**Order Lifecycle State Management: Hybrid DB + Kafka Events**
- Rationale: 3-Stage Order Lifecycle (Recommendation → Draft → Actual) stored in PostgreSQL as current state with status columns and transition validation. Kafka events capture all state transitions for audit trail + downstream processing (notifications, SLA tracking)
- Benefit: Strong consistency for current state queries + complete audit trail for HIPAA compliance + event-driven downstream processing
- Kafka Partition Strategy: `case_id` as partition key → guarantees ordered transitions per patient case
- Affects: clinical-workflow-service, prescription-service, lab-service, monitoring-service, compliance-service

**PHI De-identification for LLM Calls: Structured Separation**
- Rationale: Separate PHI (name, DOB, SSN, address, phone) from clinical data (symptoms, vitals, history) at ingestion layer. LLM receives clinical tokens with pseudonymized reference IDs only. Re-identification happens post-LLM in secure service within trust boundary
- Benefit: Most reliable HIPAA compliance — PHI never leaves secure perimeter to external LLM APIs
- Implementation: De-identification service as mandatory middleware before ai-agent-service calls LLM APIs
- Affects: ai-agent-service, patient-service, compliance-service

**Multi-Tenancy: Composite Tenant Key (organization_id + patient_id)**
- Rationale: PostgreSQL RLS policies enforce `organization_id` + `patient_id` isolation. Future-proofs for B2B enterprise expansion (clinic groups, employer-sponsored plans) without re-architecture
- Implementation: Every table includes `organization_id` (default: platform org for direct consumers) + `patient_id` where applicable. RLS policies auto-filter based on JWT claims
- Affects: All database tables, all service queries, API gateway JWT validation

### Authentication & Security

**Identity Provider: AWS Cognito**
- Rationale: Native AWS integration (chosen cloud), HIPAA eligible, lower cost than Auth0 for MVP scale (500-10K users), supports MFA (SMS + TOTP), OAuth 2.0 + OIDC, user pools for different roles
- Configuration: Separate user pools for Patients vs MDs (different MFA requirements, session policies)
- Patient sessions: 15-minute idle timeout, MFA optional (SMS OTP)
- MD sessions: 60-minute idle timeout, MFA mandatory (TOTP authenticator app)
- Affects: All frontend apps, API gateway, all services

**API Gateway: Istio Ingress Gateway**
- Rationale: Already using Istio for service mesh → Istio Ingress Gateway reduces operational complexity. Handles TLS termination, rate limiting, JWT validation, request routing at mesh edge
- Rate Limiting: Per-tier rate limits (Premium: 100 req/min, Plus: 60 req/min, Connect: 30 req/min)
- Affects: All inbound traffic, all external API consumers

**VN MD Secure Access: Zero-Trust Network Access (ZTNA)**
- Rationale: Modern zero-trust approach via Cloudflare Access or AWS Verified Access. Identity-centric access control (device posture + identity verification), no VPN infrastructure to manage, integrates with Cognito identity
- Implementation: VN MD device enrolled → identity verified → access granted to specific services only (VN MD Dashboard, assigned patient cases) → every request re-authenticated
- Latency: ~200ms RTT US-Vietnam acceptable for dashboard interactions (not real-time chat)
- Affects: VN MD Dashboard frontend, API gateway policies, compliance-service (access logging)

### API & Communication Patterns

**Inter-Service Communication: Hybrid REST + Kafka (CQRS-lite)**
- Rationale: REST for synchronous queries (MD fetching patient data, dashboard loading) + Kafka for asynchronous commands/events (care flow state transitions, notifications, SLA timer triggers)
- REST: Internal services communicate via Istio mTLS, OpenAPI specs for contracts
- Kafka Topics: `care-flow-events`, `order-lifecycle-events`, `notification-events`, `audit-events`, `sla-timer-events`
- Affects: All services, event schema governance required

**API Versioning: URL Path (/api/v1/)**
- Rationale: Simple, explicit, works well with OpenAPI documentation and Istio routing rules
- Convention: `/api/v1/patients`, `/api/v1/cases`, `/api/v1/orders`
- Affects: All REST APIs, API documentation, frontend API clients

**Real-Time Communication: WebSocket via Istio**
- Rationale: MD dashboards require real-time updates (queue changes, case assignments, SLA countdown timers, new case notifications). WebSocket provides persistent bidirectional connection
- Implementation: WebSocket upgrade handled at Istio Ingress, routed to notification-service
- Fallback: SSE for environments where WebSocket blocked
- Affects: VN MD Dashboard, US MD Dashboard, notification-service

### Frontend Architecture

**State Management: React Query (TanStack Query) + Zustand**
- React Query: Server state management (API calls, caching, background refetching, optimistic updates)
- Zustand: Client state (UI state, form state, local preferences, WebSocket connection state)
- Rationale: Lightweight, modern, minimal boilerplate. React Query handles 90% of state needs (server data), Zustand for remaining 10% (UI-specific)
- Affects: All 3 frontend apps

**Repository Strategy: pnpm Workspaces Monorepo**
- Structure: Single repo with pnpm workspaces managing 3 frontend apps + shared packages
- Shared packages: `@compass/ui` (design system), `@compass/fhir-types` (TypeScript FHIR types), `@compass/auth` (Cognito hooks), `@compass/api-client` (generated from OpenAPI)
- Rationale: Shared component library across 3 apps, lighter than Turborepo/Nx for current team size, single CI/CD pipeline
- Affects: All frontend apps, CI/CD pipeline

**Component Library: Shadcn/ui**
- Rationale: TailwindCSS-based (already chosen), copy-paste ownership (no vendor dependency), accessible (Radix UI primitives), highly customizable for healthcare UI branding
- Customization: Vietnamese-friendly typography, elderly-accessible touch targets (44x44px minimum), high contrast medical alert colors
- Affects: All 3 frontend apps via shared `@compass/ui` package

### Infrastructure & Deployment

**Cloud Provider: AWS (HIPAA-compliant)**
- Services: EKS (Kubernetes), RDS PostgreSQL 16, MSK (Managed Kafka), ElastiCache Redis, Cognito, S3, CloudFront, Secrets Manager
- Regions: Primary us-east-1, DR us-west-2 (Phase 2)
- HIPAA: BAA with AWS, all services in HIPAA-eligible configuration
- Rationale: Largest healthcare cloud ecosystem, most BAA-ready services, team familiarity
- Affects: All infrastructure, deployment pipelines, cost structure

**CI/CD: GitHub Actions**
- Pipeline: PR checks (lint, test, security scan) → Build containers → Push to ECR → Deploy to EKS (staging → production)
- Security: SAST (Semgrep), dependency scanning (Dependabot), container scanning (Trivy)
- Rationale: Team-friendly, large ecosystem, works well with AWS
- Affects: All services and frontend apps

**Observability: OpenTelemetry + Grafana Stack**
- Metrics: Grafana Mimir (Prometheus-compatible, long-term storage)
- Logs: Grafana Loki (HIPAA audit logging, 7-year retention policy)
- Traces: Grafana Tempo (distributed tracing across microservices)
- Dashboards: Grafana (unified view — SLA compliance, system health, clinical workflow metrics)
- Instrumentation: OpenTelemetry SDK in all services (auto-instrumentation for FastAPI)
- Alerting: Grafana Alerting → PagerDuty (SLA violations, system errors, security events)
- Affects: All services, infrastructure, compliance reporting

**Secret Management: AWS Secrets Manager**
- Rationale: Native AWS integration, automatic rotation, audit trail via CloudTrail
- Secrets: Database credentials, API keys (OpenAI, Anthropic, SureScripts, Stripe, Twilio), mTLS certificates
- Access: Kubernetes External Secrets Operator syncs to K8s secrets
- Affects: All services requiring credentials

### Decision Impact Analysis

**Implementation Sequence:**
1. AWS infrastructure setup (EKS, RDS, MSK, Cognito, Secrets Manager)
2. Istio service mesh + Ingress Gateway configuration
3. Database schema with FHIR hybrid models + RLS policies
4. Shared libraries (fhir-models, security middleware, event schemas)
5. Core services (patient-service, compliance-service, api-gateway)
6. AI agent service (LangGraph + PHI de-identification pipeline)
7. Clinical workflow engine (care flow state machines + Kafka events)
8. Frontend apps (Patient Portal → VN MD Dashboard → US MD Dashboard)
9. Integration services (SureScripts, Stripe, Twilio)
10. Observability stack (Grafana + OpenTelemetry instrumentation)

**Cross-Component Dependencies:**
- AWS Cognito ↔ All services (JWT validation), All frontends (auth flows)
- Istio ↔ All service-to-service communication (mTLS enforcement)
- Kafka ↔ Clinical workflow engine, Order lifecycle, Notifications, SLA timers, Audit events
- PostgreSQL RLS ↔ All data access patterns (tenant isolation)
- PHI de-identification service ↔ AI agent service (mandatory middleware)
- FHIR models (shared library) ↔ All services touching patient data
- OpenTelemetry ↔ All services (instrumentation required for compliance)

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 25+ areas where AI agents could make different choices, organized into 5 pattern categories below.

### Naming Patterns

**Database Naming Conventions:**
- Tables: `snake_case`, plural → `patients`, `medication_requests`, `draft_orders`, `audit_logs`
- Columns: `snake_case` → `patient_id`, `created_at`, `organization_id`, `clinical_severity`
- Foreign keys: `{referenced_table_singular}_id` → `patient_id`, `case_id`, `order_id`
- Indexes: `idx_{table}_{columns}` → `idx_patients_organization_id`, `idx_draft_orders_status_case_id`
- Constraints: `{type}_{table}_{columns}` → `uq_patients_email`, `ck_orders_status_valid`
- Enums: `snake_case` types → `order_status`, `clinical_severity`, `subscription_tier`

**API Naming Conventions:**
- Endpoints: `snake_case`, plural nouns → `/api/v1/patients`, `/api/v1/care_cases`, `/api/v1/draft_orders`
- Route parameters: `{resource_id}` → `/api/v1/patients/{patient_id}/cases/{case_id}`
- Query parameters: `snake_case` → `?status=pending&subscription_tier=premium&page=1&page_size=20`
- Actions (non-CRUD): verbs as sub-resources → `POST /api/v1/draft_orders/{id}/approve`, `POST /api/v1/cases/{id}/escalate`
- Headers: Standard HTTP headers only; custom headers use `X-Compass-` prefix → `X-Compass-Tenant-Id`

**Code Naming Conventions:**

Backend (Python):
- Files: `snake_case.py` → `patient_service.py`, `fhir_models.py`, `audit_middleware.py`
- Classes: `PascalCase` → `PatientService`, `DraftOrderRepository`, `CareFlowStateMachine`
- Functions/methods: `snake_case` → `get_patient_by_id()`, `create_draft_order()`, `validate_phi_access()`
- Variables: `snake_case` → `patient_id`, `case_status`, `ai_confidence_score`
- Constants: `UPPER_SNAKE_CASE` → `MAX_RETRY_COUNT`, `SLA_PREMIUM_HOURS`, `PHI_ENCRYPTION_KEY`

Frontend (TypeScript/React):
- Components: `PascalCase.tsx` → `PatientChat.tsx`, `CaseQueue.tsx`, `OrderReviewCard.tsx`
- Hooks: `camelCase` prefixed `use` → `usePatientCases.ts`, `useWebSocket.ts`, `useAuth.ts`
- Utilities: `camelCase.ts` → `formatFhirDate.ts`, `calculatePriorityScore.ts`
- Types/Interfaces: `PascalCase` → `PatientProfile`, `DraftOrder`, `CaseStatus`
- API clients: `camelCase` → `patientApi.ts`, `caseApi.ts`, `orderApi.ts`

### Structure Patterns

**Backend Service Organization (per microservice):**
```
services/{service-name}/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app instance
│   ├── config.py               # Settings from env/secrets
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── routes/         # Route handlers (thin layer)
│   │   │   └── schemas/        # Pydantic request/response models
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dependencies.py     # FastAPI dependencies (DI)
│   │   ├── security.py         # Auth, RBAC checks
│   │   └── exceptions.py       # Custom exception classes
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── repositories/       # Database access layer
│   │   └── services/           # Business logic layer
│   ├── events/
│   │   ├── __init__.py
│   │   ├── producers.py        # Kafka event producers
│   │   └── consumers.py        # Kafka event consumers
│   └── middleware/
│       ├── __init__.py
│       ├── audit.py            # PHI access audit logging
│       └── phi_filter.py       # PHI de-identification
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── alembic/                    # Database migrations
├── Dockerfile
├── pyproject.toml
└── README.md
```

**Frontend App Organization (per app):**
```
frontend/{app-name}/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── features/               # Feature-based organization
│   │   ├── chat/
│   │   │   ├── components/
│   │   │   ├── hooks/
│   │   │   ├── api/
│   │   │   └── types.ts
│   │   ├── cases/
│   │   ├── orders/
│   │   └── monitoring/
│   ├── shared/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── utils/
│   ├── stores/                 # Zustand stores
│   └── config/
├── tests/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
└── package.json
```

**Test Location:** Co-located `tests/` directory per service/app with `unit/` and `integration/` subdirectories.

### Format Patterns

**API Response Format:**
```json
// Success response
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-02-26T10:30:00Z"
  }
}

// Paginated response
{
  "data": [ ... ],
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-02-26T10:30:00Z",
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_count": 150,
      "total_pages": 8
    }
  }
}

// Error response
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable error message",
    "details": [ ... ],
    "request_id": "uuid"
  }
}
```

**HTTP Status Code Usage:**
- `200` OK (GET success, PUT/PATCH success)
- `201` Created (POST success)
- `204` No Content (DELETE success)
- `400` Bad Request (validation errors)
- `401` Unauthorized (missing/invalid auth)
- `403` Forbidden (insufficient permissions/RBAC)
- `404` Not Found
- `409` Conflict (state transition violation)
- `422` Unprocessable Entity (business logic validation)
- `429` Too Many Requests (rate limiting)
- `500` Internal Server Error (unexpected failures)

**Date/Time Format:** ISO 8601 UTC in all APIs → `"2026-02-26T10:30:00Z"`. Frontend converts to local timezone for display.

**JSON Field Naming:** `snake_case` everywhere (API requests, responses, Kafka events, database JSONB). Frontend converts to camelCase at API client boundary only.

### Communication Patterns

**Kafka Event Naming:** `{domain}.{entity}.{action}` in lowercase dot notation:
- `care.case.created`, `care.case.escalated`
- `order.recommendation.generated`, `order.draft.created`, `order.draft.approved`, `order.actual.created`
- `prescription.transmitted`, `prescription.ready`
- `monitoring.checkin.completed`, `monitoring.case.closed`
- `audit.phi.accessed`, `audit.phi.modified`
- `sla.timer.started`, `sla.timer.warning`, `sla.timer.breached`

**Kafka Event Payload Structure:**
```json
{
  "event_id": "uuid",
  "event_type": "order.draft.approved",
  "event_version": "1.0",
  "timestamp": "2026-02-26T10:30:00Z",
  "source_service": "clinical-workflow-service",
  "correlation_id": "case-uuid",
  "tenant": {
    "organization_id": "uuid",
    "patient_id": "uuid"
  },
  "payload": { ... },
  "metadata": {
    "actor_id": "uuid",
    "actor_role": "vnmd"
  }
}
```

**Event Versioning:** Semantic versioning in `event_version` field. New fields = minor version (backward compatible). Breaking changes = major version (new topic).

### Process Patterns

**Error Handling (Backend):**
- Custom exception hierarchy: `CompassBaseException` → `ValidationError`, `AuthorizationError`, `PHIAccessError`, `ClinicalSafetyError`
- `ClinicalSafetyError` = highest priority, triggers immediate MD notification
- All exceptions caught by global FastAPI exception handler → consistent error response format
- PHI never appears in error messages or logs (sanitized before logging)
- All errors logged with `correlation_id` for distributed tracing

**Error Handling (Frontend):**
- React Error Boundaries per feature module (chat error doesn't crash dashboard)
- React Query `onError` callbacks for API errors → toast notifications
- Network errors → offline banner + retry mechanism
- Auth errors (401) → automatic redirect to login
- Vietnamese error messages for patient-facing UI, English for MD dashboards

**Loading State Pattern:**
- React Query manages loading/error/success states for all API calls
- Skeleton loading components (not spinners) for dashboard data
- Optimistic updates for MD actions (approve order → immediate UI update → revert if API fails)
- WebSocket reconnection: exponential backoff (1s, 2s, 4s, 8s, max 30s)

**Retry Pattern (Backend Services):**
- Idempotent operations: retry with exponential backoff (1s, 2s, 4s, max 3 retries)
- Non-idempotent operations: no automatic retry, return error for human decision
- LLM API calls: retry 3x with 2s backoff, then fallback to backup LLM (GPT-4 → Claude)
- Kafka producer: retry with acks=all, max 5 retries
- SureScripts: retry 3x, then queue for manual retry

**Validation Pattern:**
- API input validation: Pydantic models at route handler level
- Business validation: Service layer (clinical rules, RBAC, state transitions)
- Database validation: PostgreSQL constraints (NOT NULL, CHECK, UNIQUE) as last defense
- Frontend validation: Zod schemas matching Pydantic models (shared via OpenAPI codegen)

### Enforcement Guidelines

**All AI Agents MUST:**
1. Follow naming conventions exactly (snake_case Python, PascalCase components, snake_case API/JSON/DB)
2. Use the standard project structure (api/core/domain/events layers per service)
3. Include audit logging middleware for any service touching PHI
4. Use the standard API response format (data/meta/error envelope)
5. Use the standard Kafka event envelope (event_id, event_type, correlation_id, tenant, payload)
6. Never expose PHI in error messages, logs, or external API responses
7. Include `correlation_id` in all log entries for distributed tracing
8. Use feature-based organization in frontend (not type-based)
9. Write co-located tests in `tests/unit/` and `tests/integration/` directories

**Pattern Enforcement:**
- ESLint + Prettier (frontend) with custom rules matching naming conventions
- Ruff + Black (backend) with pyproject.toml configuration
- Pre-commit hooks validate naming and structure
- CI pipeline checks: lint, type-check, test, security scan
- OpenAPI schema validation ensures API format compliance

## Project Structure & Boundaries

### Complete Project Directory Structure

```
compass-vitals/
├── README.md
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci-backend.yml
│       ├── ci-frontend.yml
│       ├── cd-staging.yml
│       └── cd-production.yml
│
├── shared/                          # Cross-service shared libraries
│   ├── fhir-models/                 # FHIR R4 data models (Python package)
│   │   ├── pyproject.toml
│   │   ├── fhir_models/
│   │   │   ├── __init__.py
│   │   │   ├── patient.py
│   │   │   ├── medication_request.py
│   │   │   ├── diagnostic_report.py
│   │   │   ├── observation.py
│   │   │   ├── care_plan.py
│   │   │   ├── encounter.py
│   │   │   └── extensions.py
│   │   └── tests/
│   ├── security/                    # Shared security middleware (Python package)
│   │   ├── pyproject.toml
│   │   ├── compass_security/
│   │   │   ├── __init__.py
│   │   │   ├── jwt_validator.py
│   │   │   ├── rbac.py
│   │   │   ├── phi_filter.py
│   │   │   ├── audit_logger.py
│   │   │   ├── encryption.py
│   │   │   └── tenant_context.py
│   │   └── tests/
│   └── events/                      # Shared Kafka event schemas (Python package)
│       ├── pyproject.toml
│       ├── compass_events/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── care_flow.py
│       │   ├── order_lifecycle.py
│       │   ├── prescription.py
│       │   ├── monitoring.py
│       │   ├── audit.py
│       │   ├── sla.py
│       │   ├── producer.py
│       │   └── consumer.py
│       └── tests/
│
├── services/                        # Backend microservices
│   ├── api-gateway/                 # API routing + rate limiting
│   ├── patient-service/             # FR1-8, FR58-64: Patient management + accounts
│   │   ├── app/
│   │   │   ├── api/v1/routes/
│   │   │   │   ├── patients.py
│   │   │   │   ├── accounts.py
│   │   │   │   ├── subscriptions.py
│   │   │   │   └── medical_history.py
│   │   │   ├── domain/
│   │   │   │   ├── models/ (patient, subscription, medical_history, consent)
│   │   │   │   ├── repositories/
│   │   │   │   └── services/ (patient_service, subscription_service, onboarding_service)
│   │   │   ├── events/
│   │   │   └── middleware/
│   │   ├── tests/
│   │   ├── alembic/
│   │   └── Dockerfile
│   │
│   ├── ai-agent-service/            # FR9-16, FR97-100: AI agents + Vietnamese NLP
│   │   ├── app/
│   │   │   ├── api/v1/routes/ (screening, chat)
│   │   │   ├── domain/services/ (llm_gateway, phi_deidentifier, confidence_scorer)
│   │   │   ├── agents/              # LangGraph agent definitions
│   │   │   │   ├── supervisor.py
│   │   │   │   ├── intake_agent.py
│   │   │   │   ├── screening_agent.py
│   │   │   │   ├── proposer_agent.py
│   │   │   │   ├── critic_agent.py
│   │   │   │   └── graphs/ (prescription_flow, lab_flow, emergency_flow, monitoring_flow)
│   │   │   ├── nlp/                 # Vietnamese NLP pipeline
│   │   │   │   ├── cultural_mapper.py
│   │   │   │   ├── code_switcher.py
│   │   │   │   └── medical_terminology.py
│   │   │   ├── events/
│   │   │   └── middleware/
│   │   ├── tests/
│   │   └── Dockerfile
│   │
│   ├── clinical-workflow-service/    # FR32-38: Care flow orchestration
│   │   ├── app/
│   │   │   ├── api/v1/routes/ (cases, care_flows, sla)
│   │   │   ├── domain/
│   │   │   │   ├── models/ (care_case, order_recommendation, draft_order, actual_order)
│   │   │   │   └── services/ (case_service, order_lifecycle_service, priority_router, sla_timer_service)
│   │   │   ├── state_machines/ (base_flow, emergency_flow, prescription_flow, lab_flow, monitoring_flow)
│   │   │   ├── events/
│   │   │   └── middleware/
│   │   ├── tests/
│   │   ├── alembic/
│   │   └── Dockerfile
│   │
│   ├── prescription-service/         # FR39-45: Prescription management
│   │   ├── app/domain/services/ (prescription_service, drug_interaction_checker, allergy_screener, surescripts_client)
│   │   ├── tests/
│   │   └── Dockerfile
│   │
│   ├── lab-service/                  # FR46-51: Lab & diagnostic management
│   │   ├── app/domain/services/ (lab_order_service, result_parser, critical_value_alerter)
│   │   ├── tests/
│   │   └── Dockerfile
│   │
│   ├── monitoring-service/           # FR52-57: Monitoring & follow-up
│   │   ├── app/domain/services/ (protocol_service, checkin_scheduler, escalation_service)
│   │   ├── tests/
│   │   └── Dockerfile
│   │
│   ├── notification-service/         # FR8, WebSocket, SMS, push
│   │   ├── app/domain/services/ (websocket_manager, sms_service, email_service, push_service)
│   │   ├── tests/
│   │   └── Dockerfile
│   │
│   └── compliance-service/           # FR71-78: Audit, compliance, HIPAA
│       ├── app/domain/services/ (audit_service, license_verifier, consent_manager, breach_notifier)
│       ├── tests/
│       ├── alembic/
│       └── Dockerfile
│
├── frontend/                        # Frontend monorepo (pnpm workspaces)
│   ├── pnpm-workspace.yaml
│   ├── package.json
│   ├── tsconfig.base.json
│   ├── .eslintrc.cjs
│   ├── .prettierrc
│   ├── packages/                    # Shared packages (@compass/*)
│   │   ├── ui/                      # @compass/ui — Shadcn/ui design system
│   │   ├── fhir-types/              # @compass/fhir-types — TypeScript FHIR types
│   │   ├── auth/                    # @compass/auth — Cognito hooks + AuthProvider
│   │   └── api-client/              # @compass/api-client — OpenAPI generated clients
│   ├── apps/
│   │   ├── patient-portal/          # FR1-8: features/ (chat, care-plan, onboarding, account, records)
│   │   ├── vnmd-dashboard/          # FR17-24: features/ (queue, case-review, orders, video-call, history)
│   │   └── usmd-dashboard/          # FR25-31: features/ (unified-review, approval, audit-trail, analytics)
│   └── tools/
│       └── openapi-codegen/
│
├── infrastructure/
│   ├── docker/ (docker-compose.yml, docker-compose.test.yml)
│   ├── kubernetes/
│   │   ├── base/ (namespaces, service manifests)
│   │   ├── overlays/ (staging, production)
│   │   └── secrets/ (ExternalSecret definitions)
│   ├── istio/ (gateway, virtual-services, destination-rules, authorization-policies, rate-limit)
│   ├── terraform/
│   │   ├── modules/ (eks, rds, msk, elasticache, cognito, secrets-manager)
│   │   └── environments/ (staging, production)
│   └── grafana/ (dashboards, alerting-rules)
│
├── database/
│   ├── migrations/
│   ├── seeds/
│   └── schemas/ (rls-policies.sql, fhir-extensions.sql)
│
└── docs/
    ├── api/                         # OpenAPI specs per service
    ├── architecture/
    └── runbooks/
```

### Architectural Boundaries

**Service Boundaries (9 microservices):**

| Service | Owns Data | Produces Events | Consumes Events |
|---|---|---|---|
| patient-service | patients, subscriptions, consents | patient.* | — |
| ai-agent-service | agent_sessions, screening_results | care.case.*, order.recommendation.* | care.case.created |
| clinical-workflow-service | care_cases, order_recommendations, draft_orders, actual_orders | order.*, care.*, sla.* | order.recommendation.*, care.* |
| prescription-service | prescriptions, drug_interactions | prescription.* | order.actual.created |
| lab-service | lab_orders, lab_results | lab.* | order.actual.created |
| monitoring-service | monitoring_protocols, checkins | monitoring.* | order.actual.created, prescription.*, lab.* |
| notification-service | notification_preferences | — | ALL events (fan-out) |
| compliance-service | audit_logs, compliance_reports | audit.* | ALL events (audit) |
| api-gateway | rate_limit_counters | — | — |

**Data Boundaries:** Each service owns its database schema. No direct cross-service database access. All inter-service data access via REST APIs or Kafka events.

### Requirements to Structure Mapping

| FR Category | Backend Service | Frontend App | Frontend Feature |
|---|---|---|---|
| FR1-8 Patient Care | patient-service, ai-agent-service | patient-portal | chat/, care-plan/, records/ |
| FR9-16 AI Workflow | ai-agent-service | — | — |
| FR17-24 VN MD | clinical-workflow-service | vnmd-dashboard | queue/, case-review/, orders/ |
| FR25-31 US MD | clinical-workflow-service | usmd-dashboard | unified-review/, approval/ |
| FR32-38 Care Flows | clinical-workflow-service | — | — |
| FR39-45 Prescriptions | prescription-service | usmd-dashboard | approval/ |
| FR46-51 Lab/Imaging | lab-service | vnmd-dashboard, usmd-dashboard | case-review/ |
| FR52-57 Monitoring | monitoring-service | patient-portal | care-plan/ |
| FR58-64 Accounts | patient-service | patient-portal | onboarding/, account/ |
| FR65-70 Auth/Access | api-gateway, all services | all apps | @compass/auth |
| FR71-78 Compliance | compliance-service | usmd-dashboard | audit-trail/ |
| FR79-84 Integrations | prescription-service, notification-service | — | — |
| FR85-90 Admin | compliance-service | admin dashboard (Phase 2) | — |
| FR91-96 Emergency | ai-agent-service, clinical-workflow-service | patient-portal | chat/ (emergency mode) |
| FR97-100 Vietnamese NLP | ai-agent-service (nlp/) | patient-portal | chat/ |

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
All technology choices are compatible and work together without conflicts:
- Python async ecosystem: FastAPI 0.133.0 + SQLAlchemy 2.x async + asyncpg + LangGraph 1.0 — proven stack
- AWS native integration: EKS + RDS PostgreSQL 16 + MSK (Kafka) + ElastiCache (Redis) + Cognito — all HIPAA-eligible, single-vendor operational simplicity
- Frontend: React 19 + Vite 6 + TypeScript 5.x + TailwindCSS + Shadcn/ui — current stable versions, no version conflicts
- Infrastructure: Istio service mesh on EKS + Kafka + Grafana Stack — production-proven combination

**Pattern Consistency:**
- Naming conventions are internally consistent: snake_case (Python/DB/API/JSON), PascalCase (React components/Python classes), camelCase (TS hooks/utils)
- Layered service architecture (api/core/domain/events) applied uniformly across all 9 microservices
- Feature-based frontend organization consistent across all 3 SPAs
- Kafka event naming (`domain.entity.action`) and envelope structure uniform across all domain events

**Structure Alignment:**
- Directory structure directly maps to all architectural decisions
- Service boundaries enforce data ownership (no cross-service DB access)
- Shared libraries (fhir-models, security, events) properly centralized
- Infrastructure-as-code structure (Terraform, Kubernetes, Istio) supports deployment decisions

**Note:** Architecture specifies Python 3.13+ (upgraded from PRD's 3.11+) — this is an intentional improvement for better performance and typing support.

### Requirements Coverage Validation ✅

**Functional Requirements Coverage: 100/100 FRs mapped**

All 13 FR categories (FR1-FR100) have been mapped to specific backend services, frontend apps, and feature directories in the Requirements to Structure Mapping table. No orphaned requirements.

**Non-Functional Requirements Coverage: 22/22 NFRs addressed**

- Performance (NFR-P1-P5): async architecture + Redis caching + connection pooling + CDN
- Security (NFR-S1-S5): zero-trust (Istio mTLS) + ZTNA + Cognito MFA + PHI encryption + audit logging
- Scalability (NFR-SC1-SC4): EKS horizontal autoscaling + Kafka partitioning + Redis cluster mode
- Reliability (NFR-R1-R4): multi-AZ deployment + Kafka replication factor 3 + circuit breakers + retry patterns
- Compliance (NFR-C1-C5): PostgreSQL RLS + 100% audit logging + PHI de-identification + FHIR R4 native + consent management
- Accessibility (NFR-A1-A3): Vietnamese-first UI + elderly-friendly touch targets (44x44px) + high contrast alerts

### Implementation Readiness Validation ✅

**Decision Completeness:**
- All critical architectural decisions documented with specific technology versions
- 25+ AI agent conflict points identified and resolved with explicit patterns
- 9 mandatory enforcement rules defined for AI agent consistency
- Pattern enforcement tools specified (ESLint, Ruff, pre-commit hooks, CI checks)

**Structure Completeness:**
- Complete project tree with all directories and key files specified
- 9 microservices with internal module structure (routes, models, repositories, services, events)
- 3 frontend SPAs with feature-based organization and shared packages
- Infrastructure directories for Docker, Kubernetes, Istio, Terraform, Grafana

**Pattern Completeness:**
- API response format with success, paginated, and error examples
- Kafka event envelope with all required fields
- Error handling patterns for both backend (exception hierarchy) and frontend (error boundaries)
- Retry, validation, loading state patterns all specified with concrete rules

### Gap Analysis Results

**Critical Gaps:** None found. All critical decisions are complete for MVP implementation.

**Important Gaps (Non-blocking, Phase 2):**
1. **Mobile App Architecture** — PRD includes iOS/Android as target platforms. Current architecture focuses on web SPAs. Mobile decisions (React Native vs Flutter, push notification architecture, offline-first patterns) deferred to Phase 2
2. **Admin Dashboard** — FR85-90 administrative capabilities mapped to Phase 2. Will need separate UI architecture decisions
3. **Multi-Region DR** — us-west-2 disaster recovery deferred to Phase 2. Will require database replication strategy, Kafka MirrorMaker, EKS multi-cluster federation
4. **SureScripts Certification Timeline** — Integration architecture defined, but 3-6 month certification process requires early project planning coordination

**Nice-to-Have Gaps:**
- API documentation generation tooling (Swagger UI configuration per service)
- Database seeding scripts for development/testing environments
- Load testing infrastructure (k6 or Locust configuration)
- Developer onboarding documentation

### Validation Issues Addressed

No critical or blocking issues found during validation. The architecture is coherent, complete for MVP scope, and provides sufficient guidance for AI agent implementation.

The Python version upgrade (3.11+ → 3.13+) is an intentional improvement documented during architecture decisions and does not conflict with any PRD requirements.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context thoroughly analyzed (5 subsystems, 100 FRs, 22 NFRs)
- [x] Scale and complexity assessed (Enterprise level)
- [x] Technical constraints identified (9 constraints including HIPAA, FHIR, FDA SaMD)
- [x] Cross-cutting concerns mapped (9 concerns)

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions (FHIR, PHI, AWS, Cognito, REST+Kafka)
- [x] Technology stack fully specified (all versions verified via web search)
- [x] Integration patterns defined (REST sync + Kafka async, CQRS-lite)
- [x] Performance considerations addressed (async, caching, CDN, autoscaling)

**✅ Implementation Patterns**
- [x] Naming conventions established (DB, API, Code — Python + TypeScript)
- [x] Structure patterns defined (service layers, frontend features)
- [x] Communication patterns specified (Kafka events, API format, WebSocket)
- [x] Process patterns documented (error handling, retry, validation, loading states)

**✅ Project Structure**
- [x] Complete directory structure defined (all services, apps, infrastructure)
- [x] Component boundaries established (9 services with data ownership)
- [x] Integration points mapped (Kafka topics, REST APIs, shared libraries)
- [x] Requirements to structure mapping complete (100 FRs → services + features)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** HIGH — based on comprehensive validation across coherence, coverage, and readiness dimensions

**Key Strengths:**
1. **Healthcare-native design** — FHIR R4, PHI de-identification, HIPAA compliance built into every layer from day 1
2. **AI agent implementation clarity** — 25+ conflict points resolved, 9 mandatory rules, concrete examples for every pattern
3. **Clear service boundaries** — Data ownership table prevents service coupling, Kafka events for async communication
4. **Complete FR mapping** — Every functional requirement traceable to specific service + directory
5. **Production-proven stack** — All technology choices are battle-tested at scale (AWS, Kafka, PostgreSQL, FastAPI, React)

**Areas for Future Enhancement:**
1. Mobile app architecture decisions (Phase 2)
2. Multi-region disaster recovery topology (Phase 2)
3. Admin dashboard architecture (Phase 2)
4. Advanced caching strategies beyond Redis (when scale demands)
5. Load testing and performance benchmarking infrastructure

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented in this file
- Use implementation patterns consistently across all components
- Respect project structure and service boundaries (no cross-service DB access)
- Refer to this document for all architectural questions before making independent decisions
- When in doubt about a pattern, check the Enforcement Guidelines section

**First Implementation Priority:**
1. Execute project scaffold command (Custom Composite Starter initialization)
2. Set up AWS infrastructure (EKS, RDS, MSK, ElastiCache, Cognito)
3. Configure Istio service mesh + Ingress Gateway
4. Create shared libraries (fhir-models, security, events)
5. Implement database schema with FHIR hybrid models + RLS policies
