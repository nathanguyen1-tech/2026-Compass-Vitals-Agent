---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
workflowStatus: 'complete'
completedDate: '2026-02-25'
inputDocuments: ['docs/service-3-access-to-care-247-high-level-flow.md', '_bmad-output/planning-artifacts/research/technical-ai-agent-frameworks-medical-healthcare-research-2026-02-24.md']
workflowType: 'prd'
briefCount: 0
researchCount: 1
brainstormingCount: 0
projectDocsCount: 1
classification:
  projectType: 'saas_b2b_healthcare_platform'
  domain: 'healthcare_telemedicine'
  complexity: 'high'
  projectContext: 'greenfield'
  targetMarket: 'vietnamese_americans_in_us'
  platforms: ['web_app', 'mobile_app', 'api_backend']
  mvpPriority: 'prescription_flow'
technicalDecisions:
  aiFramework: 'CrewAI (POC) → LangGraph (Production)'
  llmPlatform: 'GPT-4 (primary) + Claude 3.5 (backup)'
  backend: 'Python 3.11+ FastAPI'
  database: 'PostgreSQL + FHIR extensions + Redis cache'
  cloud: 'AWS or GCP (HIPAA-compliant)'
  security: 'Zero-trust architecture, 5-layer HIPAA'
  integration: 'FHIR RESTful APIs + Event-driven (Kafka)'
productVision:
  vision: 'AI-first telemedicine platform phá bỏ rào cản y tế cho người Việt tại Mỹ - kết hợp AI Agents thông minh với bác sĩ Việt Nam (Vietnam-based) hiểu văn hóa và US MD compliance, mang đến chăm sóc nhanh, chính xác, phải chăng'
  differentiators:
    - 'Cultural-Linguistic Bridge: AI Chatbot song ngữ + VN MD hiểu văn hóa + AI hiểu cultural expressions (bị nóng trong, gió độc)'
    - 'AI-Powered Speed: 80% công việc chuyên môn do AI xử lý → phản hồi cực nhanh (Premium <1hr vs industry 4-8hr)'
    - 'Cost & Convenience: VN MD remote from Vietnam (lower cost) + 24/7 availability + mobile app'
  coreInsight: 'Người Việt ở Mỹ underserved bởi telemedicine (language + cultural + cost barriers). AI Agents + Vietnamese medical team = perfect solution.'
  valueProposition: 'Telemedicine tiếng Việt 24/7 với AI thông minh và bác sĩ Việt hiểu văn hóa - phản hồi cực nhanh (<1 giờ), chi phí thấp, giải quyết đúng vấn đề sức khỏe của người Việt ở Mỹ'
  uniqueAdvantages:
    - 'AI hiểu multi-language văn phong của người Việt (không chỉ translation, mà cultural understanding)'
    - 'Bác sĩ Việt Nam based in Vietnam (abundant supply, cultural fit, lower cost structure)'
    - 'Combination AI Intelligence + Cultural Understanding → Better diagnostic accuracy + engagement'
---

# Product Requirements Document - 2026-Compass_Vitals_Agent

**Author:** AN-AI
**Date:** 2026-02-24

---

## Executive Summary

**2026-Compass_Vitals_Agent** là nền tảng telemedicine AI-first phục vụ cộng đồng Vietnamese-Americans tại Mỹ - kết hợp **AI Agents chuyên môn hóa** xử lý 80% công việc lâm sàng với **đội ngũ bác sĩ Việt Nam** (based in Vietnam) hiểu văn hóa và **US MD** đảm bảo legal compliance. Platform cung cấp 4 luồng dịch vụ 24/7 (Emergency, Prescription, Lab/Imaging, Monitoring) qua AI Chatbot song ngữ (Vietnamese-English) trên Web và Mobile, phá bỏ các rào cản ngôn ngữ, văn hóa, và chi phí mà người Việt đang gặp phải khi tiếp cận y tế tại Mỹ.

**Target Users:** ~2.2 triệu người Việt sinh sống tại Mỹ, đặc biệt là thế hệ 1st generation (50+ tuổi) gặp khó khăn với English medical terminology và cultural disconnect với American healthcare system. Họ thường trì hoãn khám bệnh do language barrier, cost concerns ($500-2000 ER visit), và lack of Vietnamese-speaking doctors.

**Problem Being Solved:** Vietnamese-Americans bị underserved bởi existing telemedicine platforms (Teladoc, MDLive) không có Vietnamese language support, bác sĩ không hiểu cultural health beliefs ("bị nóng trong", "gió độc"), và thời gian phản hồi chậm (4-8 giờ). Điều này dẫn đến delayed care, miscommunication, unnecessary ER visits, và poor health outcomes.

### What Makes This Special

**Triple Differentiation Strategy:**

1. **Cultural-Linguistic Mastery**
   - AI Chatbot hiểu **multi-language và văn phong** của người Việt (không chỉ translation)
   - AI trained to map Vietnamese cultural expressions → Western medical terminology ("bị nóng trong" = internal inflammation/infection symptoms)
   - Bác sĩ Việt Nam giải thích diagnosis và treatment plan bằng tiếng Việt, sử dụng cultural context
   - **Differentiation moment**: Bệnh nhân nói "bị nóng trong" → AI hiểu ngay → Bác sĩ Việt confirm và explain bằng tiếng mẹ đẻ

2. **AI-Powered Hyper-Speed**
   - **80% công việc chuyên môn** (clinical screening, symptom analysis, order recommendations, drug interaction checking) được AI Agents xử lý tự động
   - Bác sĩ VN MD và US MD chỉ cần **review và approve** (20% effort) → productivity tăng 5x
   - **Thời gian phản hồi**: Premium <1 giờ, Plus <2 giờ, Connect <4 giờ (vs industry standard 4-8 giờ)
   - 24/7 availability với consistent quality (AI không nghỉ, không mệt)

3. **Cost Structure Advantage**
   - VN MD based in Vietnam → lower labor cost (Vietnam medical salary 1/10 US)
   - AI automation → reduce MD workload 80% → serve 5-10x more patients per MD
   - **Pricing**: $39-249/month subscription (vs competitor $50-100/visit or insurance-only)
   - Economics work: Lower cost structure + higher efficiency = affordable pricing + profitable margins

**Core Insight:** Existing telemedicine fails Vietnamese-Americans not because of technology gaps, but **cultural-linguistic gaps**. Solution = **AI Intelligence** (xử lý clinical work accurately) **+** **Vietnamese Cultural Understanding** (VN MD + AI trained on Vietnamese expressions) **→** Better diagnostic accuracy + Higher engagement + Lower cost + Faster response.

**Value Proposition:** Telemedicine tiếng Việt 24/7 với AI thông minh và bác sĩ Việt hiểu văn hóa - phản hồi cực nhanh (<1 giờ), chi phí thấp, giải quyết đúng vấn đề sức khỏe của người Việt ở Mỹ.

## Project Classification

**Project Type:** SaaS B2B Healthcare Platform (Multi-tenant telemedicine)
**Domain:** Healthcare - Telemedicine for Vietnamese-Americans
**Complexity:** HIGH (FDA SaMD considerations, HIPAA compliance, multi-state medical licensing, AI/ML in clinical settings)
**Project Context:** Greenfield - Brand new system
**Platforms:** Web App + Mobile App (iOS/Android) + API Backend (microservices)
**MVP Priority:** Prescription Flow (Luồng B) - 9 stations end-to-end

**Technical Foundation:**
- **AI Framework:** CrewAI (POC phase) → LangGraph (Production) - role-based multi-agent orchestration
- **LLM Platform:** GPT-4 (primary, 93.1% medical accuracy) + Claude 3.5 (long-context backup)
- **Architecture:** Multi-agent microservices + Zero-trust security + Event-driven (Kafka + FHIR Subscriptions)
- **Compliance:** HIPAA 5-layer architecture, FHIR-first data model (July 2026 mandate), FDA 510(k) pathway
- **Implementation Timeline:** 18 months (POC 3m → MVP 6m → Production 9m)
- **Cost Structure:** MVP $6K-13K/month (1K patients) → Production $28K-55K/month (10K patients)

---

## Success Criteria

### User Success

**Completion Moment:**
- Patient nhận được **comprehensive care plan** bao gồm tất cả services cần thiết: diagnosis rõ ràng, prescription (nếu cần thuốc), lab orders (nếu cần xét nghiệm), monitoring protocol (nếu cần theo dõi)
- Complete care journey từ symptom intake → final treatment plan trong **<3 giờ total** (Premium tier: <1hr initial response + <2hr final approval)
- **Zero ambiguity** về next steps - Patient biết chính xác phải làm gì tiếp theo (uống thuốc, đi xét nghiệm, theo dõi tại nhà, hoặc gọi 911)

**Emotional Success:**
- **"Nhẹ nhõm" (Relieved)**: Kết quả được giao **nhanh chóng** (Premium <1hr, Plus <2hr, Connect <4hr vs competitors 4-8hr) và **chính xác** (AI + VN MD + US MD triple validation)
- **"Được hiểu" (Understood)**: AI và bác sĩ hiểu cultural expressions ("bị nóng trong", "bị gió") - không struggle với English medical terminology
- **"Tự tin" (Empowered)**: Treatment plan giải thích rõ ràng bằng tiếng Việt với cultural context, patient hiểu và tin tưởng vào plan

**"Aha!" Differentiation Moments:**
- **Lần đầu chat tiếng Việt**: AI chatbot responds intelligently về symptoms bằng tiếng Việt
- **Giá trị vượt trội**: $39-249/month unlimited care vs $50-100/visit competitors
- **Tốc độ khác biệt**: Premium <1hr vs industry 4-8hr - "Wow, nhanh thật!"
- **Cultural understanding**: Bác sĩ Việt hiểu "bị nóng trong" không cần translation/explanation

### Business Success

**Early Success Indicators (6 months - Pilot Phase):**
- **500 active patients** enrolled và completed ≥1 full care journey (tất cả flows functional)
- **>70% monthly retention rate** - Patients continue subscription beyond first month
- **>90% prescription accuracy** validated vs board-certified MDs (zero medication errors)
- **MD satisfaction >4/5** - Vietnamese and US doctors trust AI system
- **Zero PHI breaches** - Perfect HIPAA compliance record

**Growth Targets (12-18 months - Production Scale):**
- **10,000 active patients** using platform monthly across all 4 flows
- **>75% retention rate** - Patients stay long-term (sticky product)
- **>95% clinical appropriateness** - MD approval rate for AI recommendations
- **40% wait time reduction** achieved vs traditional telemedicine benchmarks
- **<$5 per patient interaction** - LLM cost optimized via hybrid strategy

**"This Is Working" Signals (Success Validation):**
- **NPS >50** - Strong Net Promoter Score indicating word-of-mouth growth trong Vietnamese community
- **MD productivity 2x** - Each doctor handles 20 cases/day (vs 10 baseline), proving AI automation works
- **Customer renewal rate >80%** - Patients consistently renew subscriptions (not one-time users)
- **Zero medication errors maintained** - Clinical safety proven at scale
- **Organic referrals >30%** - Family/friends recommendations driving growth

### Technical Success

**AI Agent Performance:**
- **>90% medical accuracy** - AI recommendations align với board-certified MD decisions
- **AI response time**: Screening <2 minutes, Proposal <5 minutes (real-time performance)
- **<2% hallucination rate** - AI errors caught by Critic Agent + MD review safety net
- **100% drug interaction detection** - Safety-critical features perfect (zero misses)
- **100% allergy screening** - Patient safety paramount

**System Performance:**
- **99.9% uptime** (24/7 requirement) = Maximum 8.76 hours downtime per year
- **Support 500+ concurrent users** without performance degradation
- **API latency P95 <500ms** for FHIR calls (responsive user experience)
- **Complete care flow timing**: Emergency <15min, Prescription <2.5hr, Lab/Monitoring <4hr

**Compliance & Security Success:**
- **HIPAA compliance audit pass** - Zero violations, all requirements met
- **FDA regulatory pathway clarity** - 510(k) submission ready or exemption confirmed by Month 9
- **100% audit trail completeness** - Every PHI access logged và traceable
- **Zero security incidents** - No data breaches, no PHI leakage to LLMs, no unauthorized access

### Measurable Outcomes

**POC Phase Success Gate (Month 3):**
- ✅ **All 4 flows** demonstrated end-to-end với simulated patients (Emergency, Prescription, Lab, Monitoring)
- ✅ **>85% AI medical accuracy** in 50-100 test cases
- ✅ **<5% hallucination rate** - AI errors minimal and caught
- ✅ **MD satisfaction >4/5** - Doctors approve of AI assistance
- ✅ **Vietnamese chatbot validated** - Cultural expressions understood correctly
- ✅ **Go/No-Go decision**: Pass criteria → Proceed to MVP, Fail → Pivot or iterate

**MVP Phase Success Gate (Month 9):**
- ✅ **100-500 pilot patients** successfully onboarded và served
- ✅ **Zero medication errors** - Perfect safety record maintained
- ✅ **HIPAA compliance audit pass** - Security assessment completed
- ✅ **FDA pathway clear** - Regulatory strategy finalized (510(k) or exempt)
- ✅ **>70% retention rate** - Patients stay subscribed
- ✅ **Web + Mobile apps functional** - Full platform operational
- ✅ **Go/No-Go decision**: Pass → Scale to Production, Fail → Iterate on safety/compliance

**Production Phase Success Gate (Month 18):**
- ✅ **10,000+ patients supported** monthly across all flows
- ✅ **99.9% uptime achieved** - Proven reliability at scale
- ✅ **<$5 per patient LLM cost** - Economics validated
- ✅ **NPS >50** - Strong user advocacy
- ✅ **All 4 flows operational** - Complete service portfolio
- ✅ **Go/No-Go decision**: Pass → Expand features + geographies, Fail → Optimize before scaling

---

## Product Scope

### MVP - Minimum Viable Product (Months 1-9)

**Core Philosophy:** MVP MUST deliver **complete care journeys** với all 4 flows - vì real patient cases require integrated services (prescription + lab + monitoring, not isolated treatments).

**Must-Have Features (All 4 Care Flows Required):**

**1. Luồng A - Emergency Flow** (6 stations - CRITICAL for patient safety):
- AI detects emergency symptoms (chest pain, difficulty breathing, stroke signs)
- Immediate escalation to 911/ER within <15 minutes
- **Why MVP**: Cannot launch telemedicine without emergency handling - liability and patient safety

**2. Luồng B - Prescription Flow** (9 stations - PRIMARY use case):
- Full workflow: Intake → AI Screening → AI Proposal → Priority Routing → VN MD Review (Draft Orders) → US MD Unified Review → Convert to Actual Prescription
- 3-Stage Order Lifecycle (Recommendations → Draft Orders → Actual Orders)
- **Why MVP**: Core value proposition - most common patient need

**3. Luồng C - Lab/Imaging Flow** (9 stations - DIAGNOSTIC necessity):
- AI recommends lab tests when diagnosis unclear
- Lab orders created, tracked, results integrated
- **Why MVP**: Many cases need lab confirmation (không thể prescribe blindly) - e.g., diabetes screening, infection confirmation

**4. Luồng D - Monitoring Flow** (14 stations - CONTINUITY of care):
- Home monitoring protocols (24hr, 48hr, 72hr check-ins)
- AI-driven check-ins via chatbot
- MD review of progress
- **Why MVP**: Post-prescription follow-up essential (medication effectiveness, side effects), post-lab result tracking

**Critical Platform Features:**

**5. Vietnamese AI Chatbot (ABSOLUTELY REQUIRED - Core Differentiator):**
- ✅ **Text Chat** - Vietnamese + English bilingual (switching mid-conversation)
- ✅ **Cultural expression mapping** - "bị nóng trong", "gió độc", "bị lạnh" → medical terms
- ✅ **24/7 availability** - AI always on, MD review within SLA windows
- 🔄 **Voice Chat** - Defer to Phase 2/3 (text validates concept first, voice enhances accessibility for elderly)

**6. Web Application (REQUIRED for MVP):**
- ✅ **Patient Portal** - Symptom intake, chat interface, care plan viewing
- ✅ **VN MD Dashboard** - Review queue, draft order creation, patient history
- ✅ **US MD Dashboard** - Unified review interface for all draft orders

**7. Mobile Strategy (Phased Approach):**
- ✅ **MVP (Month 9)**: Mobile-responsive web (PWA) - Patients access via mobile browser
- 🔄 **Phase 2 (Month 10-12)**: Native apps (React Native iOS + Android) - Enhanced UX, push notifications
- **Rationale**: Mobile web validates demand faster, native apps add polish post-validation

**8. Compliance & Security (Non-Negotiable MVP Requirements):**
- ✅ HIPAA 5-layer security architecture
- ✅ Zero-trust implementation (Istio service mesh)
- ✅ FHIR-first data models (Patient, MedicationRequest, DiagnosticReport, CarePlan)
- ✅ Audit logging complete (100% PHI access tracked)
- ✅ AES-256 encryption (rest), TLS 1.3 (transit)

**MVP Deliverables (Month 9):**
- ✅ All 4 care flows production-ready
- ✅ Web application (patient + MD portals)
- ✅ Mobile-responsive web (PWA)
- ✅ Vietnamese AI chatbot (text-based)
- ✅ 100-500 pilot patients served
- ✅ HIPAA compliance certified
- ✅ FDA regulatory strategy clear

### Growth Features (Post-MVP - Months 10-18)

**Enhanced User Experience:**
- Voice AI Chatbot (Vietnamese speech-to-text + text-to-speech)
- Native mobile apps (iOS + Android) với push notifications
- Multi-modal AI (symptom photo analysis for skin conditions, throat issues)
- Offline mode (sync when reconnected)

**Advanced Integrations:**
- Epic/Cerner real-time FHIR bi-directional sync
- LabCorp/Quest Diagnostics live integration (automated order submission + result retrieval)
- Pharmacy integration (e-prescription transmission)
- Wearable device integration (real-time vitals for Monitoring Flow)

**Scale & Optimization:**
- Multi-region deployment (US East + West for redundancy)
- Advanced analytics dashboard (MD performance, patient outcomes, cost per case)
- Vietnamese NLP fine-tuning (custom medical terminology model)
- A/B testing framework (optimize AI prompts, UI flows)

### Vision (Future - 2027+)

**Autonomous AI Evolution:**
- Pioneer Model: 30-40% of routine prescription cases fully automated (AI → direct prescription, MD audit post-facto)
- Predictive healthcare: AI predicts deterioration before symptoms (wearables + EMR data)
- Personalized medicine: Pharmacogenomics-based drug selection

**Market Expansion:**
- Vietnam domestic market (leverage VN MD network already in Vietnam)
- Global Vietnamese diaspora (Canada, Australia, Europe)
- Other Asian-American communities (Chinese, Korean, Filipino - replicate model)

**Innovation Leadership:**
- Vietnamese medical AI research pioneer
- Open-source Vietnamese medical NLP models
- Industry standard setter for cultural-aware healthcare AI

---

## User Journeys

### Journey 1: Vietnamese-American Patient - "Lần Đầu Được Hiểu"

**Persona: Cô Lan Nguyễn**
- **Age**: 58 tuổi, 1st generation Vietnamese immigrant
- **Location**: Orange County, CA
- **Background**: Lived in US 25 years, still struggles với English medical terminology
- **Tech Comfort**: Basic smartphone use, prefers Vietnamese apps
- **Insurance**: Medicare + supplemental insurance

**Opening Scene - The Pain Point:**

Thứ Bảy, 10pm tối. Cô Lan đang xem TV thì cảm thấy sốt nóng, đo nhiệt độ: 38.5°C. Đau họng nuốt nước bọt cũng đau, lo lắng vì sốt đã 3 ngày chưa đỡ. Con gái suggest: "Mẹ gọi Teladoc đi, có bảo hiểm mà." Nhưng cô Lan ngại: "Con ơi, nói tiếng Anh con không rõ triệu chứng, sợ bác sĩ Mỹ không hiểu mẹ nói gì. Emergency room thì đắt lắm, $500-1000 đấy."

Cô nghĩ: "Thôi chịu đựng, mai đi bác sĩ Việt ở Little Saigon vậy" - nhưng appointment phải đợi 1 tuần, và đi lại cũng xa.

**Rising Action - Discovery:**

Con gái search Facebook group "Người Việt ở California" thấy nhiều người recommend Compass Vitals: "Telemedicine tiếng Việt, bác sĩ Việt Nam, AI thông minh, nhanh lắm!" Đăng ký gói Care Plus $99/month.

11pm đêm đó, cô Lan mở app trên điện thoại, bấm "Chat với Bác Sĩ Ngay". Màn hình hiện:

> **AI Bot**: "Chào cô, cô đang cảm thấy không khỏe à? Hãy cho tôi biết triệu chứng nhé. Cô có thể nói tiếng Việt thoải mái."

Cô Lan gõ (chậm, một ngón tay): "Con bị sốt 3 ngày rồi, đau họng nuốt khó lắm. Con sợ bị nóng trong."

> **AI Bot**: "Dạ, con hiểu ạ. Để con hỏi thêm vài câu để giúp cô nhé:
> - Sốt bao nhiêu độ ạ?
> - Đau họng từ ngày nào?
> - Có ho hay sổ mũi không ạ?
> - Có khó thở hay đau ngực không?"

Cô Lan impressed: "Ủa, nó hiểu 'bị nóng trong' luôn!" Chat thêm 5 phút, AI hỏi kỹ về symptoms, allergies, medications đang dùng. Cô cảm thấy AI **thông minh hơn mong đợi** - hỏi đúng trọng tâm, không waste time.

**Climax - The Magic Moment:**

11:25pm, điện thoại rung - notification: "Bác sĩ Minh đang xem xét case của cô, vui lòng chờ 10-15 phút."

11:40pm, Dr. Minh (VN MD from Vietnam) video call:

> **Dr. Minh** (tiếng Việt): "Chào cô Lan, tôi là bác sĩ Minh. Tôi đã xem kết quả AI screening của cô rồi. Theo triệu chứng - sốt 3 ngày, đau họng nuốt khó, không ho, không sổ mũi - cô bị nhiễm trùng họng (pharyngitis) đấy cô. Tôi sẽ kê đơn kháng sinh Amoxicillin 500mg cho cô. Cô uống mỗi 8 tiếng một viên, uống đủ 7 ngày nhé, đừng bỏ giữa chừng."

Cô Lan hỏi (tiếng Việt): "Thuốc này có tác dụng phụ không con?"

> **Dr. Minh**: "Có thể hơi buồn nôn, nhưng uống sau khi ăn sẽ đỡ. Nếu bị nổi mẩn đỏ (allergy) thì gọi lại cho bác sĩ ngay nhé."

Giải thích rõ ràng, dễ hiểu, **không cần struggle với medical English**. Cô Lan cảm thấy **relieved và understood** - lần đầu tiên experience này với telemedicine.

1:15am (2.25 giờ total từ khi chat), notification: "US MD đã approve prescription. Đơn thuốc đã sẵn sàng tại Walgreens gần nhà cô. Mang insurance card đi nhé!"

**Resolution - The New Reality:**

Sáng Chủ Nhật 9am, cô Lan đến Walgreens, pick up Amoxicillin. Copay $10 (insurance covers). Bắt đầu uống thuốc.

Ngày thứ 3 uống thuốc, AI chatbot message: "Cô Lan ơi, uống thuốc 3 ngày rồi, đau họng có đỡ chưa ạ? Còn sốt không?" Cô reply: "Đỡ nhiều rồi con, không sốt nữa, đau họng còn một chút." AI: "Tuyệt quá! Nhớ uống đủ 7 ngày để diệt hết vi khuẩn nhé cô."

Tuần sau, họp hội phụ nữ Việt Nam, cô Lan kể: "Chị em ơi, bây giờ có app khám bệnh tiếng Việt, bác sĩ Việt Nam, nhanh lắm, đêm khuya cũng được, mà rẻ nữa $99/tháng unlimited! Lần trước con bị đau họng, 11pm đêm chat với AI, 1 giờ đêm đã có đơn thuốc rồi. Không phải đi ER tốn tiền, không phải đợi appointment 2 tuần!"

3 người bạn đăng ký ngay trong tuần đó. Cô Lan becomes **brand advocate** - refer 5 người trong 2 tháng đầu.

**Key Journey Touchpoints:**
1. **Discovery** (Facebook group recommendation) → Trust signal
2. **First Chat** (AI hiểu "bị nóng trong") → "Aha!" moment
3. **VN MD Call** (Vietnamese explanation) → Emotional connection
4. **Fast Resolution** (<3 hours total) → Expectation exceeded
5. **Follow-up** (AI check-in Day 3) → Feeling cared for
6. **Advocacy** (Tell friends) → Viral growth loop

---

### Journey 2: VN MD (Vietnamese Doctor) - "Năng Suất Tăng 5X"

**Persona: Dr. Minh Trần**
- **Age**: 35 tuổi, General Practitioner
- **Location**: Hanoi, Vietnam
- **Background**: 8 years medical experience, graduated Hanoi Medical University, fluent English + Vietnamese
- **Current Income**: $800/month at public hospital Vietnam
- **Goal**: Supplement income để support family, mua nhà

**Opening Scene - The Opportunity:**

Dr. Minh đang làm việc tại bệnh viện công Hà Nội, handle 30-40 patients/day với mức lương $800/month. Paperwork overwhelming, burnout cao. Nghe về Compass Vitals recruitment: "Hiring Vietnam-based MDs, part-time remote, $25-35/hour, flexible schedule." Apply ngay, interview với platform (test medical knowledge + English communication), được hire.

**Rising Action - First Day Experience:**

Sau 1 tuần training (US medical guidelines, platform usage, HIPAA compliance), Dr. Minh ready cho first shift.

8pm Vietnam time (7am California time - morning peak hours). Login vào **VN MD Dashboard**. Màn hình shows:

> **Priority Queue** (sorted by urgency):
> 1. **Nguyễn Lan** (58F, pharyngitis suspected) - Premium tier - **AI Screening COMPLETE**
> 2. **Trần Hùng** (45M, UTI suspected) - Plus tier - **AI Screening COMPLETE**
> 3. **Lê Mai** (62F, hypertension follow-up) - Connect tier - **AI Screening COMPLETE**

Click vào case #1 (Cô Lan):

Dashboard shows **comprehensive AI analysis**:
- **Symptom Summary**: Fever 101.3°F x3 days, sore throat, difficulty swallowing, no cough, no dyspnea
- **AI Screening Transcript**: Full Vietnamese conversation với patient (10 Q&A exchanges)
- **AI Clinical Assessment**: Pharyngitis (bacterial suspected), severity: moderate, urgency: routine
- **AI Drug Recommendations**:
  - Primary: Amoxicillin 500mg PO q8h x7 days
  - Alternative (if penicillin allergy): Azithromycin 500mg PO daily x3 days
- **Drug Interaction Check**: None (patient not on other meds)
- **Allergy Check**: No known drug allergies
- **Clinical Guidelines**: Followed Infectious Disease Society guidelines

Dr. Minh impressed: "Wow, AI đã làm sẵn 80% công việc rồi. Screening thorough hơn cả nhiều bác sĩ trẻ."

Review thêm 2 phút → Confirm AI recommendation accurate → Click "Video Call Patient" → 5 phút giải thích treatment plan cho cô Lan bằng tiếng Việt → Click "Create Draft Order: Amoxicillin 500mg q8h x7d" → **Total time: 10 phút** (vs 20-30 phút traditional consult).

**Climax - Productivity Breakthrough:**

Sau 3 giờ (8pm-11pm Vietnam), Dr. Minh đã complete **18 cases**:
- 15 cases: Approve AI recommendations as-is (AI accurate, just need human verification)
- 2 cases: Minor adjustments (dosing tweaks based on patient weight)
- 1 case: Escalate to US MD (complex case, need specialist input)

**Average time per case: 10 phút** (vs 25-30 phút traditional telemedicine).

Productivity: **18 cases in 3 hours** = 6 cases/hour (vs 2-3 cases/hour traditional).

Dr. Minh nghĩ: "AI này giống như có resident giỏi làm sẵn tất cả history taking, preliminary assessment, drug interaction checking. Mình chỉ cần verify và approve. Không cảm thấy rushed, vẫn đủ thời gian care for each patient, nhưng handle gấp 3x số lượng."

**Resolution - The New Life:**

Cuối tháng đầu:
- **Hours worked**: 60 hours (15 hours/week x 4 weeks) - evening shifts Vietnam time
- **Cases handled**: ~270 cases total
- **Income earned**: $2,100 USD (60 hrs x $35/hr average)
- **Total monthly income**: $800 (Vietnam hospital) + $2,100 (Compass) = **$2,900 USD**

**Life transformation:**
- 3.6x income increase với part-time work
- Still work full-time at hospital (career development, local patients)
- Evening Compass shifts (8pm-11pm Vietnam) → no conflict
- Weekends free for family
- After 6 months, saved enough for down payment on apartment in Hanoi

Dr. Minh tells colleagues: "Compass platform là future of medicine. AI handles grunt work, doctors focus on clinical judgment. Win-win: Patients get fast accurate care, doctors earn better với less burnout. Tôi đã refer 3 bác sĩ bạn join platform rồi."

**Key Journey Touchpoints:**
1. **Recruitment** (Opportunity discovery) → Income motivation
2. **Training** (Platform + Guidelines) → Confidence building
3. **First Case** (AI-prepared) → "Wow" moment (AI did 80% work)
4. **Productivity** (18 cases in 3 hours) → Validation
5. **Income** ($2,100/month part-time) → Life-changing
6. **Advocacy** (Refer 3 doctors) → Network growth

---

### Journey 3: US MD (Compliance Officer) - "Trust Through Transparency"

**Persona: Dr. Sarah Chen**
- **Age**: 42 tuổi, Board-certified Family Medicine physician
- **Location**: San Jose, CA
- **Background**: Vietnamese-American (2nd generation), fluent English (native), conversational Vietnamese
- **Current Role**: Full-time PCP at medical group + Part-time Compass reviewer (20hrs/week supplement income)
- **Concerns**: AI safety, regulatory liability, clinical accuracy

**Opening Scene - Skepticism:**

Dr. Chen được recruit bởi Compass: "We need US-licensed MDs for final approval - regulatory requirement. $150/hour, flexible hours, remote work." Attractive financially, nhưng skeptical: "AI making medical recommendations cho Vietnamese patients? Nguy hiểm. What if AI hallucinates và prescribes wrong drug? I'm liable!"

Compass CEO explains: "You're the safety net. AI + VN MD screen and draft - you verify and approve. Full transparency: See complete AI reasoning, VN MD notes, all patient data. You're in control."

Dr. Chen agrees to trial: "OK, let me see if this AI is actually good hay just hype."

**Rising Action - First Shift Experience:**

Saturday morning 9am, Dr. Chen login **US MD Unified Review Dashboard**.

Queue shows **12 cases pending US MD approval** (all đã qua VN MD review). Click case #1 (Cô Lan pharyngitis):

Dashboard presents **complete clinical picture**:

**Section 1: AI Screening (Full Transparency)**
- AI conversation transcript với patient (Vietnamese + English translation)
- Symptom timeline visualization
- AI differential diagnosis reasoning: "Pharyngitis (bacterial) 85% probability based on: fever duration, sore throat severity, no URI symptoms. Viral pharyngitis 10%. Strep throat 5%."

**Section 2: VN MD Review Notes**
- Dr. Minh's assessment: "Confirmed bacterial pharyngitis. Patient educated về completing full antibiotic course. No red flags."
- Draft Order created: Amoxicillin 500mg PO q8h x7d

**Section 3: Clinical Decision Support**
- Drug interaction check: ✅ None
- Allergy check: ✅ No known allergies
- Contraindication check: ✅ None
- Clinical guidelines adherence: ✅ Matches IDSA pharyngitis treatment guidelines
- AI Confidence Score: 92% (High confidence)

Dr. Chen spends 5 phút reviewing. Thinks: "Hmm, AI screening comprehensive hơn nhiều traditional intake forms. VN MD assessment sound. Clinical guidelines followed correctly. Drug choice appropriate, dosing correct."

Click **"Approve"** → Case complete → Prescription sent to pharmacy.

**Climax - The Realization:**

After reviewing 20 cases in 2 giờ (6 cases/hour vs 3-4 cases/hour traditional chart review):

**Accuracy Analysis:**
- 18/20 cases (90%): AI + VN MD recommendations **perfect** - Dr. Chen approved as-is
- 2/20 cases (10%): Minor adjustments (one dosing change, one drug substitution for patient preference)
- 0/20 cases: Major errors or safety issues
- **Zero cases** where she felt AI was dangerous or reckless

**Quality Observations:**
- AI screening **more thorough** than many human doctors (systematic, never forgets to ask critical questions)
- VN MD reviews **clinically sound** - Vietnamese doctors well-trained, careful
- **Complete context** always available - not guessing based on incomplete notes
- **Explainable AI** - Can see exactly why AI recommended each drug (reasoning chain transparent)

Dr. Chen thinks: "This is AI in medicine done RIGHT. Not replacing doctors - **empowering us**. AI + VN MD handle 95% of work accurately, I provide final quality check + regulatory compliance. Patients get fast care, I earn well với less burnout, clinical quality maintained."

**Resolution - Becoming an Advocate:**

After 3 tháng working với Compass:
- **Hours**: 20 hrs/week (weekend mornings, perfect schedule)
- **Cases reviewed**: ~480 cases total (~40/week)
- **Income**: $12,000 (20 hrs x 4 weeks x 3 months x $150/hr)
- **Error rate**: 0 medication errors caught before approval, 2 cases escalated to specialist
- **Satisfaction**: 9/10 - "Best part-time gig I've had. Meaningful work, good pay, flexible hours."

Dr. Chen presents case study tại California Medical Association conference: "AI-Assisted Telemedicine for Underserved Populations: A Vietnamese-American Case Study"

Key points:
- **Clinical safety**: Zero adverse events in 480 cases reviewed
- **Cultural competence**: Vietnamese language + cultural understanding = better patient engagement
- **Regulatory compliance**: US MD final approval meets legal requirements
- **Scalability**: AI enables 1 US MD to oversee 40-50 cases/week (vs 15-20 without AI)

Conclusion: "AI doesn't replace doctors - it **augments our capabilities**. Compass model shows how to do it responsibly: transparency, human oversight, cultural sensitivity. This is telemedicine 3.0."

**Key Journey Touchpoints:**
1. **Skepticism** (AI safety concerns) → Common doctor reaction
2. **Transparency** (Full AI reasoning shown) → Trust building
3. **First Review** (AI accuracy validated) → "Aha!" moment
4. **Productivity** (6 cases/hour) → Efficiency gain
5. **Zero Errors** (Safety proven) → Confidence
6. **Advocacy** (Conference presentation) → Industry influence

---

## Healthcare Domain Requirements

### Compliance & Regulatory

**FDA Software as Medical Device (SaMD):**
- **Classification Strategy**: Position as "Clinical Decision Support Tool" - may reduce regulatory burden vs "diagnostic device"
- **Regulatory Pathway**: 510(k) premarket notification (97% AI medical devices approved via this route in 2026)
- **FDA Pre-Submission Meeting**: Schedule by Month 6 (before MVP launch) - Cost $10K-15K for regulatory consultant
- **PCCP (Predetermined Change Control Plan)**: Pre-approve algorithm update boundaries to enable iterative AI improvements without resubmission
- **QMSR Compliance**: Quality Management System Regulation - mandatory Feb 2, 2026 alignment
- **GMLP Framework**: Good Machine Learning Practice (FDA/Health Canada/UK MHRA) - validation methodology standard

**HIPAA Compliance (Patient Privacy & Security):**
- **Privacy Rule**: PHI protection, informed consent, minimum necessary disclosure, patient rights (access, amend, accounting)
- **Security Rule**: 5-layer architecture (Data Ingestion, AI Processing, Integration Orchestration, Security & Compliance, API Management)
- **Breach Notification Rule**: <72 hour notification to HHS if PHI breach >500 individuals
- **Business Associate Agreements (BAA)**: Required với all vendors touching PHI (AWS/GCP, OpenAI/Anthropic, FHIR services, SureScripts)
- **2026 HIPAA Updates**: Continuous risk analysis (not periodic), real-time threat monitoring, zero-trust architecture mandatory
- **Audit Requirements**: 100% PHI access logged (who, what, when, where, why), immutable audit trails, monthly compliance reports

**FHIR Interoperability Mandates:**
- **21st Century Cures Act**: Certified health IT must provide standardized API access to patient data (no information blocking)
- **July 2026 Deadline**: Real-time FHIR access to medications, labs, conditions required (compliance critical for EMR integrations)
- **FHIR Resources**: Patient, Observation, MedicationRequest, DiagnosticReport, CarePlan, Encounter (core data models)

**Multi-State Medical Licensing:**
- **US MD Licensing Requirement**: Must hold active license in **patient's state of residence** (cannot practice telemedicine across state lines without license)
- **MVP State Strategy**:
  - **Priority States**: CA, TX, FL (60% of Vietnamese-American population - ~1.3M of 2.2M total)
  - **Justification**: Focus resources on high-concentration states first, expand after validation
- **Interstate Medical Licensure Compact (IMLC)**: Consider for faster multi-state expansion (29 states participating, single application process)
- **US MD Hiring**: Recruit physicians với IMLC participation or multi-state licenses (CA + TX + FL minimum for MVP)

**VN MD Legal Framework:**
- **Role Definition**: VN MD = **Medical Consultant** (NOT US prescriber) - reviews cases, creates draft recommendations for US MD approval
- **No US Prescription Authority**: VN MD lacks US license → Cannot write prescriptions or make final medical decisions for US patients
- **US MD Final Authority**: US-licensed MD reviews VN MD draft + AI analysis → Makes final medical decision → Signs prescription (bears legal liability)
- **Terms of Service Clarity**: "Vietnamese MD provides medical consultation. Final prescription authority rests with US-licensed physician."
- **Regulatory Compliance**: Model complies with US telemedicine laws (US MD final decision-maker)

### Clinical Requirements & Safety

**Clinical Validation Methodology:**
- **POC Phase (Months 1-3)**: 50-100 simulated patient cases, gold standard comparison vs board-certified MD decisions
- **Target Accuracy**: >85% AI alignment with MD decisions (POC gate criteria)
- **MVP Phase (Months 4-9)**: 100-500 real patients, prospective clinical validation, zero medication errors required
- **IRB Approval**: Determine necessity based on FDA Pre-Submission guidance (research vs clinical practice distinction)
- **Publication Plan**: Consider peer-reviewed journal publication of validation results (builds credibility, supports FDA submission)

**Patient Safety Protocols:**
- **Emergency Detection Algorithm**: AI trained on emergency symptom keywords (chest pain, difficulty breathing, stroke signs F.A.S.T., severe bleeding, loss of consciousness)
- **Emergency Escalation Process**:
  1. AI detects emergency indicators → **Immediate workflow halt**
  2. Display prominent red warning: "⚠️ TRIỆU CHỨNG KHẨN CẤP - GỌI 911 NGAY hoặc đến Emergency Room gần nhất"
  3. Show nearest ER addresses (geolocation-based) + direct 911 dial button
  4. Optional: Platform-assisted 911 call with patient consent
  5. Case flagged + on-call MD notified for documentation
  6. Follow-up: Check patient outcome, ensure ER visit completed
- **Adverse Event Reporting**:
  - Patient reports medication reaction → Immediate MD alert (push notification)
  - Serious adverse events (SAE) → FDA MedWatch reporting within 15 days (regulatory requirement)
  - All adverse events logged in database for pattern analysis (detect AI systematic errors)

**Drug Safety Features (Zero-Error Tolerance):**
- **Drug Interaction Checking**: Integrate First Databank or Micromedex database (100% coverage required)
- **Allergy Screening**: Mandatory allergy check before prescription generation (AI + human verification)
- **Contraindication Detection**: Cross-reference patient conditions vs drug contraindications (pregnancy, renal/hepatic impairment, etc.)
- **Dosing Validation**: Weight-based pediatric dosing, renal/hepatic dose adjustments, elderly dosing considerations

### Technical Constraints

**Data Residency & Cross-Border Compliance:**
- **PHI Storage**: **US-only** (AWS US regions: us-east-1, us-west-2, or GCP US regions) - HIPAA safe harbor
- **No Vietnam Servers**: Zero patient data stored on Vietnam infrastructure (compliance requirement)
- **VN MD Access Architecture**:
  - VN MD accesses **same US-based system** via secure HTTPS connection
  - **In-place data viewing**: No downloads, no data transfer to Vietnam
  - **Secure tunnel**: VPN + mTLS for VN MD connections (encryption end-to-end)
  - **Access logging**: Every VN MD query logged (HIPAA audit trail proves data stayed in US)
- **Business Associate Agreement**: VN MD contractors sign BAA (HIPAA Business Associate status, legal liability for privacy violations)

**HIPAA Security Architecture (Zero-Trust Implementation):**
- **Encryption Standards**: AES-256 at rest (database, backups), TLS 1.3 in transit (minimum version, older deprecated)
- **Access Control (RBAC)**:
  - VN MD: View assigned cases only (no access to unrelated patient data)
  - US MD: View review queue assigned by state license
  - Patients: View own data only (strict isolation)
- **Session Security**: 15-60 minute auto-timeout, MFA required for MD logins, device fingerprinting
- **PHI Minimization for AI**: LLM API calls scrubbed of identifiers (de-identify before GPT-4/Claude calls, re-identify after)
- **Audit Logging**: Every database query, API call, user action logged với timestamp + user ID + IP address + action type

**Zero-Trust Principles (2026 Mandatory):**
- **"Never Trust, Always Verify"**: Verify every access request regardless of source (internal or external)
- **Micro-Segmentation**: Isolate AI agents, MD portals, patient apps in separate network zones
- **Service Mesh (Istio)**: Enforce mTLS between all microservices (no plaintext service-to-service communication)
- **Identity-Centric**: Continuous identity risk scoring for all users, machine identities for AI agents
- **Confidential Computing**: Encrypt data during processing (not just storage/transit) - Google Confidential VMs or AWS Nitro Enclaves

### Integration Requirements

**E-Prescribing (SureScripts Network):**
- **NCPDP SCRIPT Standard**: Electronic prescription transmission to 95%+ US pharmacies
- **MVP Scope**: Basic e-prescribing for non-controlled substances (antibiotics, chronic disease meds)
- **EPCS Certification**: **Defer to Phase 2** - Electronic Prescribing of Controlled Substances (Schedule II-V: opioids, benzos, stimulants)
- **Ryan Haight Act**: Online prescribing of controlled substances requires in-person exam (telemedicine exemption complex) → Start with non-controlled only

**Lab Integration (Manual MVP → Automated Phase 3):**
- **LabCorp + Quest Diagnostics**: Cover ~70% US lab market
- **MVP Approach**: Generate lab order PDFs → Patient takes to lab → Manual result upload
- **Phase 3 Automation**: HL7 FHIR DiagnosticReport integration (automated order submission + result retrieval)
- **Critical Value Alerts**: Abnormal results (glucose >400, K+ >6.0) → Immediate MD notification

**Pharmacy Integration:**
- **MVP**: SureScripts e-prescription (prescription sent electronically, patient picks up at pharmacy)
- **Phase 2**: Pharmacy delivery partnerships (mail-order pharmacy, Amazon Pharmacy integration)
- **Insurance**: Support Medicare Part D, major commercial insurances (BCBS, UnitedHealth, Aetna)

### Risk Mitigations (Domain-Specific)

**Medical Licensing Compliance Risk:**
- **Mitigation**: State verification at patient signup - geofence to states where US MD licensed
- **Technical Control**: IP geolocation + patient-entered zip code verification
- **Scalability Strategy**: Hire US MDs with IMLC → covers 29 states với single license application
- **Monitoring**: Track patient state distribution, proactively recruit MDs for high-demand unlicensed states

**VN MD Regulatory Exposure:**
- **Legal Clarity**: Terms of Service explicitly state: "Vietnamese MD provides medical consultation only. US-licensed physician makes final prescription decisions and bears medical liability."
- **Healthcare Attorney Review**: Legal opinion on VN MD consultant model before MVP launch (cost $5K-10K)
- **Insurance Coverage**: Professional liability insurance for VN MD contractors ($1M-3M coverage) + US MD ($1M-3M malpractice)
- **Platform Liability**: Separate E&O insurance for platform ($5M-10M) covering technology errors, data breaches

**AI Hallucination & Patient Safety:**
- **Triple Safety Net**: AI Critic Agent (catches errors) → VN MD human review (clinical judgment) → US MD final check (regulatory compliance)
- **Confidence Thresholds**: Low AI confidence (<70%) → Automatic escalation to MD (no auto-recommendations)
- **Explainable AI**: Show reasoning chain allows MD to verify logic (symptoms → differential → treatment rationale)
- **Continuous Learning**: MD corrections fed back to AI training (improve accuracy over time)

**Cross-Border Data Privacy (US-Vietnam):**
- **US-Only Storage**: All PHI stays in US cloud (HIPAA compliance, no cross-border data transfer laws)
- **VN MD Secure Access**: VPN + mTLS tunnel to US servers (encrypted viewing, no downloads)
- **Access Auditing**: Prove to regulators that data never left US jurisdiction (audit logs show US server access only)
- **BAA Enforcement**: VN MD contractors sign HIPAA BAA (legal liability if mishandle PHI)

---

## Innovation Focus

### Industry-First Innovations

**1. Cultural-Aware Medical AI (Industry First)**

**What Makes It Novel:**
- First medical AI system trained to understand Vietnamese cultural health expressions and map them to Western medical terminology
- AI recognizes phrases like "bị nóng trong" (internal heat/inflammation), "gió độc" (harmful wind/cold exposure), "bị lạnh" (cold entering body) and translates to clinically actionable symptoms
- Goes beyond simple language translation - understands cultural context and traditional Vietnamese health beliefs

**Technical Implementation:**
- Fine-tuned LLM with Vietnamese medical conversation corpus (5,000+ culturally-specific symptom descriptions)
- Cultural expression mapping database (Vietnamese folk terms → Western diagnostic criteria)
- Hybrid NLP pipeline: Vietnamese language model + Medical terminology model + Cultural context layer

**Competitive Moat:**
- Teladoc, MDLive, Amwell: Zero Vietnamese language support, zero cultural understanding
- General translation AI (Google Translate): Literal translation misses clinical nuances ("bị nóng trong" → "hot inside" loses diagnostic meaning)
- This innovation = 3-5 year competitive lead (requires Vietnamese medical expertise + AI ML capability + cultural anthropology understanding)

---

**2. Tri-Party AI-Human Collaboration Model (Unprecedented Architecture)**

**What Makes It Novel:**
- World's first medical system with **three-layer collaboration**: AI Agents (80% work) + Vietnam-based MDs (cultural bridge) + US-licensed MDs (regulatory compliance)
- Not "AI vs Human" or "AI assists Human" - it's "AI + Offshore Human + Local Human" in synchronized workflow
- Enables 24/7 Vietnamese-language telemedicine at US compliance standards với fraction of traditional cost

**Technical Implementation:**
- Multi-agent workflow orchestration (CrewAI/LangGraph) with role-based task delegation
- 3-Stage Order Lifecycle (AI Recommendations → VN MD Draft Orders → US MD Actual Orders)
- Real-time collaboration: AI screening (2 min) → VN MD review (10 min) → US MD approval (5 min) = <20 min total
- Geographically distributed but data-centralized (US-only PHI storage, secure remote access)

**Competitive Moat:**
- No existing telemedicine platform uses offshore physicians legally (regulatory complexity)
- No AI platform has solved "Cultural Understanding + US Compliance" paradox simultaneously
- Model requires: AI expertise + Healthcare regulatory knowledge + International workforce management + Vietnamese cultural fluency
- Regulatory clarity took 6+ months legal research - now defensible IP via process patents

---

**3. Multi-Language Medical NLP (Seamless Code-Switching)**

**What Makes It Novel:**
- AI handles Vietnamese-English code-switching mid-conversation naturally (common behavior of Vietnamese-Americans: "Con bị fever 3 ngày rồi, đau họng nuốt very difficult")
- Not separate Vietnamese AI + English AI - single unified model understands both simultaneously
- Maintains medical accuracy across language boundaries (symptom described in Vietnamese → diagnosis in English → treatment explanation in Vietnamese)

**Technical Implementation:**
- Multilingual medical fine-tuning (GPT-4 + Vietnamese medical corpus)
- Context-aware language detection (sentence-level, not document-level)
- Bidirectional medical terminology mapping (Vietnamese ↔ English with cultural context preservation)

**Competitive Moat:**
- Babel Health, LanguageLine: Translation services (not AI-native, slower, human interpreters)
- Google Health: English-only medical AI
- This requires: Multilingual NLP expertise + Medical domain knowledge + Vietnamese linguistic understanding
- Dataset advantage: 2.2M Vietnamese-Americans generate unique training data over time (network effects)

---

**4. AI-First Telemedicine 3.0 (80% Automation Paradigm)**

**What Makes It Novel:**
- Industry standard telemedicine: 100% human doctor work, AI = zero involvement (Teladoc model)
- Emerging AI telemedicine: AI symptom checker → human doctor final diagnosis (25% automation)
- **Compass model: AI handles 80% clinical work** (screening, differential diagnosis, drug interaction checking, order recommendations) → Human doctor 20% (verify, approve, edge cases)
- First platform to flip the labor ratio: Humans verify AI, not AI assists humans

**Technical Implementation:**
- Multi-agent system with specialized medical AI agents:
  - **Intake Agent**: Symptom gathering, medical history (replaces RN triage)
  - **Screening Agent**: Clinical assessment, differential diagnosis (replaces MD preliminary eval)
  - **Proposer Agent**: Treatment recommendations, drug selection (replaces MD order entry)
  - **Critic Agent**: Safety checks, error detection (replaces pharmacist + peer review)
- Human doctors focus on: Complex cases, edge case judgment, regulatory signing, quality oversight
- Productivity multiplier: 1 MD handles 40-60 cases/day (vs 10-15 traditional telemedicine)

**Competitive Moat:**
- Requires clinical validation proving >90% AI accuracy (regulatory barrier)
- Needs explainable AI for legal liability defense (technical barrier)
- Demands FDA regulatory pathway clarity (compliance barrier)
- 18-month head start: POC validation → MVP launch → Clinical outcomes publication = defensible position

---

**5. Cost Structure Disruption ($39-249/month Unlimited Model)**

**What Makes It Novel:**
- Industry pricing: $50-100 per visit (Teladoc) or insurance-required (no self-pay friendly)
- Compass pricing: **$39-249/month subscription, unlimited visits** across all 4 care flows (Emergency, Prescription, Lab, Monitoring)
- Economics powered by: AI automation (80% labor reduction) + Vietnam offshore MD labor arbitrage (1/10 US cost) + Multi-patient efficiency (1 MD serves 5-10x more patients)

**Unit Economics:**
- **Care Connect ($39/month)**: <4hr response, ~3 visits/month avg → $13/visit cost (AI $3 + VN MD $5 + US MD $3 + infrastructure $2)
- **Care Plus ($99/month)**: <2hr response, ~5 visits/month avg → $20/visit cost (priority routing + faster MD review)
- **Care Premium ($249/month)**: <1hr response, ~8 visits/month avg → $31/visit cost (dedicated MD pool + real-time)
- **Gross Margin**: 60-70% (vs industry 20-30%) due to AI efficiency + offshore labor

**Competitive Moat:**
- Requires all three innovations working together: AI automation + Cultural AI + Offshore MD model
- Traditional telemedicine cannot replicate (stuck with 100% US MD labor cost ~$150/hr)
- AI-only companies cannot compete (lack human cultural understanding + regulatory compliance)
- Price elasticity moat: Once established at $39-249, competitors cannot undercut without similar cost structure

---

### Innovation Validation Strategy

**POC Phase (Months 1-3): Technical Feasibility**
- Prove AI automation works: >85% accuracy in 50-100 test cases
- Validate Vietnamese NLP: Cultural expressions correctly understood
- Demonstrate tri-party workflow: AI → VN MD → US MD pipeline functional

**MVP Phase (Months 4-9): Clinical Validation**
- Real-world accuracy: >90% AI recommendations align with MD decisions
- Zero medication errors: Safety proven with 100-500 pilot patients
- Patient satisfaction: NPS >50 (innovation = value, not just novelty)

**Production Phase (Months 10-18): Market Validation**
- Economics proven: <$5 per patient LLM cost, 60-70% gross margins maintained at scale
- Regulatory clarity: FDA pathway confirmed (510(k) approval or exemption)
- Competitive defensibility: Published clinical outcomes, patent applications filed

---

## SaaS B2B Healthcare Platform Specific Requirements

### Platform Architecture

**Multi-Tenant SaaS Model:**
- **Tenancy Level**: Patient-level isolation (each patient = separate tenant with isolated PHI)
- **Database Strategy**: Shared PostgreSQL with Row-Level Security (RLS) policies enforcing tenant_id partitioning
- **Data Isolation**: Zero-Trust architecture - every microservice verifies tenant identity before data access
- **Scaling Strategy**: Horizontal pod autoscaling (Kubernetes) - target 500 patients MVP → 10,000 patients Production

**Technical Stack:**
- **Backend**: Python 3.11+ FastAPI microservices (async/await for high concurrency)
- **Database**: PostgreSQL 15+ with FHIR extensions (patient data) + Redis (session/cache)
- **Message Queue**: Apache Kafka (event-driven architecture for care flow state transitions)
- **Service Mesh**: Istio (mTLS encryption between all services, zero-trust enforcement)
- **Container Orchestration**: Kubernetes (AWS EKS or GCP GKE)
- **Cloud Provider**: AWS or GCP (HIPAA-compliant regions: us-east-1, us-west-2)

---

### Role-Based Access Control (RBAC)

**User Roles:**

1. **Patient** - 2.2M potential users (Vietnamese-Americans in US)
2. **VN MD** - Vietnam-based medical consultants (~10-20 doctors by Month 18)
3. **US MD** - US-licensed prescribers (~5-10 doctors by Month 18, multi-state licenses)
4. **AI Agent** - System identity (automated screening, proposal generation)
5. **Platform Admin** - Operations team (audit access, emergency support)

**Permission Matrix:**

| Resource/Action | Patient | VN MD | US MD | AI Agent | Admin |
|---|---|---|---|---|---|
| View own medical records | ✅ Full access | ❌ | ❌ | ❌ | 🔒 Audit only |
| View assigned patient cases | ❌ | ✅ Assigned only | ✅ Assigned only | ✅ Assigned only | ✅ All (emergency) |
| Create draft orders | ❌ | ✅ | ❌ | ✅ Recommendations | ❌ |
| Approve/sign prescriptions | ❌ | ❌ | ✅ Final authority | ❌ | ❌ |
| Modify AI recommendations | ❌ | ✅ Clinical override | ✅ Clinical override | ❌ | ❌ |
| Access unassigned patient data | ❌ | ❌ | ❌ | ❌ | ❌ (HIPAA minimum necessary) |
| View audit logs | ❌ | ❌ | ❌ | ❌ | ✅ Compliance team |
| Escalate to 911/ER | ❌ Patient consent | ✅ Clinical judgment | ✅ Clinical judgment | ✅ Emergency protocol | ❌ |

**Permission Enforcement:**
- **API Gateway**: JWT token-based authentication (Auth0 or AWS Cognito)
- **Service-Level**: Every microservice verifies user role + tenant_id before data access
- **Database**: PostgreSQL RLS policies enforce row-level permissions (patient_id = current_user_tenant)
- **Audit Trail**: 100% of permission checks logged (who accessed what data, when, why)

---

### Subscription Tiers & Feature Gating

**Care Connect - $39/month (Target: 60% of users)**
- ✅ All 4 care flows (Emergency, Prescription, Lab/Imaging, Monitoring)
- ✅ Unlimited visits (no per-visit charge)
- ✅ <4 hour response SLA (Connect tier queue priority)
- ✅ Text chat with AI + VN MD (no video)
- ✅ Basic monitoring (72hr check-ins)
- ❌ No priority routing (FIFO queue within tier)

**Care Plus - $99/month (Target: 30% of users)**
- ✅ All Connect features
- ✅ <2 hour response SLA (Plus tier priority queue)
- ✅ Video call option with VN MD (5-10 min consultation)
- ✅ Enhanced monitoring (48hr check-ins + proactive alerts)
- ✅ Prescription delivery coordination (pharmacy integration)

**Care Premium - $249/month (Target: 10% of users - chronic conditions, elderly)**
- ✅ All Plus features
- ✅ <1 hour response SLA (Premium tier dedicated MD pool)
- ✅ Direct US MD consultation option (complex cases, second opinion)
- ✅ Intensive monitoring (24hr check-ins + real-time vitals if wearable connected)
- ✅ Concierge support (direct MD phone access during business hours)
- ✅ Care coordination (specialist referrals, family communication)

**Technical Implementation:**
- **Feature Flags**: LaunchDarkly or custom feature flag service (subscription_tier → enabled_features mapping)
- **Priority Queue**: Kafka consumer groups with priority ordering (Premium → Plus → Connect)
- **SLA Enforcement**: Queue routing + MD pool allocation based on tier (Premium gets dedicated MDs)
- **Billing**: Stripe Billing API (monthly recurring, pro-rated upgrades, annual prepay discount option)

---

### Integration Architecture

**Critical Integrations (MVP - Month 9):**

**1. SureScripts E-Prescribing Network**
- **Purpose**: Electronic prescription transmission to 95%+ US pharmacies
- **Standard**: NCPDP SCRIPT 2017071 (industry standard)
- **Scope**: Non-controlled substances only (antibiotics, chronic disease meds, acute treatments)
- **Integration Type**: RESTful API with NCPDP XML payload
- **Authentication**: mTLS certificates + API keys
- **Certification**: SureScripts certification required (~$10K-15K + 3-6 months process)
- **BAA Required**: Yes (SureScripts is Business Associate)

**2. Payment Processing (Stripe)**
- **Purpose**: Subscription billing, payment method storage, revenue recognition
- **Scope**: Monthly recurring subscriptions, tier changes, proration, refunds
- **Integration Type**: Stripe Billing API + Stripe Customer Portal (self-service)
- **Compliance**: PCI DSS Level 1 (Stripe certified, we don't touch card data)
- **Features**: Automatic retry for failed payments, dunning management, invoice generation

**3. Identity & Access Management (Auth0 or AWS Cognito)**
- **Purpose**: User authentication, MFA enforcement, session management
- **Scope**: Patient logins, MD logins (MFA required for HIPAA), OAuth tokens for API access
- **Integration Type**: OAuth 2.0 + OpenID Connect (OIDC)
- **Security**: HIPAA-compliant identity provider, audit logging, MFA (SMS + authenticator app)
- **BAA Required**: Yes (Auth0 signs BAA for healthcare customers)

**4. SMS/Communication (Twilio)**
- **Purpose**: MFA codes, appointment reminders, prescription ready notifications
- **Scope**: Transactional SMS only (not marketing - HIPAA compliant use)
- **Integration Type**: Twilio Programmable SMS API
- **Compliance**: HIPAA-compliant Twilio accounts available (BAA required)
- **Opt-out**: Required by TCPA (patient can disable SMS notifications)

---

**Phase 2 Integrations (Months 10-18):**

**5. Epic/Cerner FHIR APIs (EMR Integration)**
- **Purpose**: Import patient medical history from existing providers
- **Standard**: FHIR R4 (21st Century Cures Act mandate - July 2026)
- **Scope**: Retrieve MedicationRequest, Condition, AllergyIntolerance, DiagnosticReport from patient's PCP
- **Integration Type**: FHIR RESTful API with OAuth 2.0 (patient authorizes data sharing)
- **Value**: Pre-populate patient medical history → reduce intake time, improve AI accuracy

**6. LabCorp + Quest Diagnostics (Lab Integration)**
- **Purpose**: Automated lab order submission + result retrieval
- **Standard**: HL7 FHIR DiagnosticReport, Observation resources
- **Scope**: Order common labs (CBC, CMP, lipid panel, HbA1c, urinalysis), retrieve results electronically
- **Integration Type**: FHIR API (if available) or HL7 v2 messages (fallback)
- **MVP Workaround**: Generate lab order PDF → Patient takes to lab → Manual result upload

**7. Pharmacy Delivery Services (Amazon Pharmacy, PillPack)**
- **Purpose**: Prescription home delivery coordination
- **Integration Type**: API-based (prescription transfer + delivery tracking)
- **Value**: Convenience for elderly patients, medication adherence tracking

---

### Healthcare Compliance (SaaS Operations)

**HIPAA Compliance Certification:**
- **HITRUST CSF Certification**: Industry gold standard for HIPAA compliance (~12-18 months process, $50K-150K first time)
- **MVP Alternative**: Self-attestation + third-party risk assessment (cheaper, faster, acceptable for pilot)
- **Annual Audits**: Required for HITRUST maintenance ($30K-50K annually)
- **Continuous Monitoring**: Automated compliance checks (AWS Security Hub, Wiz, or Vanta)

**SOC 2 Type II (Security, Availability, Confidentiality):**
- **Why Needed**: Enterprise healthcare customers (hospitals, clinic groups) require SOC 2 for vendor approval
- **Scope**: Security controls, system availability, data confidentiality
- **Timeline**: 6-12 months observation period + audit (plan to start Month 6 for Month 18 completion)
- **Cost**: $15K-30K first audit, $10K-20K annual

**State Medical Board Compliance:**
- **Multi-State Licensing Verification**: Automated check ensuring US MD has license in patient's state before prescription generation
- **Integration**: National Practitioner Data Bank (NPDB) or state medical board APIs
- **Technical Control**: Patient zip code → state lookup → verify US MD has license in that state → route case accordingly
- **Monitoring**: Monthly license status checks for all US MD contractors (detect expired/suspended licenses)

**Business Associate Agreements (BAA):**
- **Required Vendors**:
  - Cloud provider (AWS or GCP)
  - LLM providers (OpenAI, Anthropic)
  - SureScripts (e-prescribing)
  - Auth0 or AWS Cognito (identity)
  - Twilio (SMS communications)
  - Database hosting (if separate)
- **Legal Review**: Healthcare attorney drafts/reviews BAAs ($5K-10K legal budget)
- **Execution**: Electronic signature via DocuSign or Ironclad

---

### SaaS Operations & Customer Lifecycle

**Patient Onboarding Flow:**
1. **Signup** (Web or mobile-responsive PWA)
   - Email + phone number verification (OTP via SMS)
   - Select subscription tier (Connect/Plus/Premium)
   - Enter payment method (Stripe checkout)

2. **Medical Intake** (FHIR-compliant questionnaire)
   - Allergies (drug, food, environmental)
   - Current medications (drug interaction screening)
   - Medical conditions (chronic diseases, past surgeries)
   - Family history (relevant for AI risk assessment)
   - Insurance information (optional - most patients self-pay, but capture for future claims)

3. **Legal Consents** (HIPAA + Telemedicine)
   - HIPAA Authorization for Use and Disclosure
   - Telemedicine Informed Consent (state-specific language)
   - Terms of Service + Privacy Policy
   - E-signature capture (legally binding)

4. **Account Activation**
   - Profile created → Access granted to AI chat interface
   - Welcome message: "Chào mừng! You can now chat với bác sĩ Việt 24/7. Hãy cho chúng tôi biết nếu bạn cần giúp đỡ!"

**Subscription Management (Self-Service):**
- **Upgrade/Downgrade**: Instant tier changes (pro-rated billing calculated by Stripe)
- **Cancellation Policy**: End of current billing cycle (data retained 7 years per HIPAA)
- **Pause/Resume**: Not offered (subscription model assumes continuous access)
- **Payment Failure**: 3 retry attempts over 10 days → account suspended (no PHI deletion) → reactivate when payment succeeds

**Customer Support:**
- **In-App Messaging**: Non-medical questions (billing, account settings, technical issues)
- **Phone Support**: Business hours (9am-5pm PT) for complex billing/tech escalations
- **Medical Questions**: Always routed through AI chatbot → MD (not separate support team - ensure clinical appropriateness)
- **Emergency Support**: 24/7 on-call MD for platform escalations (e.g., prescription not received, urgent clarification)

---

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach: Complete Care Journey MVP**

**Strategic Rationale:**
- Healthcare is not modular - patients present with complex needs requiring integrated services across multiple care flows
- **Real-world scenario**: Patient with sore throat → Prescription (antibiotic) + Monitoring (48hr check-in for effectiveness) + Potential Lab (if symptoms don't improve, throat culture needed)
- Launching with single flow (e.g., Prescription-only) = incomplete value proposition = patient frustration ("I need lab work too, now I have to use another service")
- **Trade-off Accepted**: Longer MVP timeline (9 months vs 3-6 months single-flow) for complete user value that drives retention

**What Makes Users Say "This Is Useful":**
1. **Completeness**: One platform handles all healthcare needs (no service fragmentation)
2. **Speed**: <1-4 hour response times (vs 4-8 hours industry standard) across all tiers
3. **Language**: Vietnamese AI chatbot understands cultural expressions ("bị nóng trong") - no English barrier
4. **Cost**: $39-249/month unlimited visits (vs $50-100/visit competitors or insurance-required models)

**What Makes Investors Say "This Has Potential":**
1. **Validated Tri-Party Model**: AI (80% automation) + VN MD (cultural bridge) + US MD (compliance) collaboration proven functional
2. **Clinical Safety**: Zero medication errors achieved with 500 pilot patients (rigorous safety validation)
3. **Unit Economics**: 60-70% gross margins (AI efficiency + offshore labor arbitrage vs industry 20-30%)
4. **Market Traction**: 500 patients Month 6 → 10,000 patients Month 18 = 20x growth trajectory

**Fastest Path to Validated Learning:**
- **POC (Month 3)**: Prove AI accuracy >85% + Vietnamese NLP works + Tri-party workflow functional → Go/No-Go
- **MVP (Month 9)**: Validate real patients trust system + clinical safety (zero errors) + retention >70% → Product-market fit signal
- **Production (Month 18)**: Prove economics at scale (<$5 LLM cost/patient) + NPS >50 + organic growth (referrals >30%) → Scale readiness

**Resource Requirements:**
- **POC Team (Months 1-3)**: 4-6 people
  - 2 Full-stack engineers (Python/FastAPI + React)
  - 1 AI/ML engineer (LangGraph, prompt engineering, Vietnamese NLP)
  - 1 Product manager (healthcare domain knowledge)
  - 2 Medical advisors (1 VN MD, 1 US MD - part-time consultants)
- **MVP Team (Months 4-9)**: 6-8 people
  - Add: 1 DevOps engineer (Kubernetes, HIPAA infrastructure)
  - Add: 1 QA engineer (clinical safety testing, compliance validation)
  - Scale medical team: 5-8 VN MDs + 2-3 US MDs (part-time contractors)
- **Production Team (Months 10-18)**: 15-20 people
  - Engineering: 8-10 (backend, frontend, AI/ML, DevOps, QA, security)
  - Product: 2-3 (PM, UX designer, data analyst)
  - Medical: 10-20 VN MDs + 5-10 US MDs (scale with patient volume)
  - Operations: 2-3 (compliance, customer support, MD recruitment)

---

### MVP Feature Set (Phase 1: Months 1-9)

**Core User Journeys Supported:**

**1. Vietnamese-American Patient Journey** (Primary persona: Cô Lan Nguyễn)
- **Flow**: Discovery → Chat với AI (tiếng Việt) → VN MD consultation → US MD approval → Prescription ready <3 hours
- **All 4 Care Flows Accessible**: Emergency (15min response), Prescription (<2.5hr), Lab/Imaging (<4hr), Monitoring (24-72hr check-ins)
- **Emotional Success Markers**: "Nhẹ nhõm" (relieved - fast response), "Được hiểu" (understood - cultural fluency), "Tự tin" (empowered - clear treatment plan)

**2. VN MD Journey** (Persona: Dr. Minh Trần from Hanoi)
- **Flow**: Dashboard review → AI-prepared cases → 10 min review → Draft order creation → 18 cases/3hrs productivity
- **Value Delivered**: Vietnam-based remote work → $2,100/month part-time income (3.6x local salary increase)
- **Experience**: AI does 80% grunt work (history taking, preliminary assessment) → MD focuses on clinical judgment

**3. US MD Journey** (Persona: Dr. Sarah Chen, Vietnamese-American)
- **Flow**: Unified review dashboard → AI + VN MD transparency → 5 min approval → 6 cases/hour efficiency
- **Value Delivered**: $150/hr part-time work, flexible hours, meaningful clinical oversight
- **Confidence**: Complete context visible (AI reasoning, VN MD notes, clinical guidelines) → Zero liability concerns

---

**Must-Have Capabilities (MVP Non-Negotiables):**

**Patient-Facing Features:**
- ✅ **Vietnamese-English Bilingual AI Chatbot** (text-based with cultural expression mapping: "bị nóng trong" → inflammation symptoms)
- ✅ **Web Application** (desktop + mobile-responsive PWA for Month 9)
- ✅ **Self-Service Signup** + subscription management (Stripe integration for Connect/Plus/Premium tiers)
- ✅ **All 4 Care Flows End-to-End**:
  - **Luồng A (Emergency)**: 6 stations, <15 min emergency detection + 911 escalation
  - **Luồng B (Prescription)**: 9 stations, <2.5 hr complete cycle (AI → VN MD → US MD → Pharmacy)
  - **Luồng C (Lab/Imaging)**: 9 stations, <4 hr cycle (lab order generation, result tracking)
  - **Luồng D (Monitoring)**: 14 stations, 24-72hr check-ins (medication effectiveness, side effects)
- ✅ **24/7 AI Availability** + <1-4hr MD response SLA (Premium <1hr, Plus <2hr, Connect <4hr)

**Clinical & Safety Features:**
- ✅ **3-Stage Order Lifecycle**: AI Recommendations → VN MD Draft Orders → US MD Actual Orders (regulatory compliance)
- ✅ **Emergency Detection + Escalation**: AI trained on emergency keywords (chest pain, stroke F.A.S.T., severe bleeding) → Immediate 911 guidance
- ✅ **Drug Interaction Checking**: 100% accuracy (First Databank or Micromedex database integration)
- ✅ **Allergy Screening**: Mandatory before prescription generation (patient safety paramount)
- ✅ **Multi-State Licensing Verification**: US MD license matches patient's state (automated geofencing + verification)

**Compliance & Security Features:**
- ✅ **HIPAA 5-Layer Architecture**: Encryption (AES-256 rest, TLS 1.3 transit), Access control (RBAC), Audit logging (100% PHI access tracked)
- ✅ **Zero-Trust Implementation**: Istio service mesh (mTLS between all microservices), continuous identity verification
- ✅ **FHIR-First Data Model**: Patient, MedicationRequest, DiagnosticReport, CarePlan (21st Century Cures Act compliance)
- ✅ **US-Only PHI Storage**: AWS/GCP HIPAA-compliant regions (us-east-1, us-west-2) - no cross-border data transfer
- ✅ **FDA Regulatory Strategy Clear**: 510(k) pathway or exemption confirmed by Month 9 (Pre-Submission meeting Month 6)

**Critical Integrations (MVP):**
- ✅ **SureScripts**: E-prescribing to 95%+ US pharmacies (NCPDP SCRIPT standard, non-controlled substances)
- ✅ **Stripe**: Subscription billing (monthly recurring, pro-rated tier changes, dunning management)
- ✅ **Auth0 or AWS Cognito**: Identity + MFA (HIPAA-compliant, OAuth 2.0 + OIDC)
- ✅ **Twilio**: SMS notifications (MFA codes, prescription ready alerts, HIPAA BAA required)

---

**MVP Exclusions (Explicitly Deferred to Phase 2/3):**

**Deferred to Phase 2 (Months 10-15):**
- ❌ **Native Mobile Apps** (React Native iOS/Android) - PWA validates demand first, native apps add polish post-validation
- ❌ **Voice AI Chatbot** (Vietnamese speech-to-text/text-to-speech) - Text proves concept, voice enhances elderly accessibility later
- ❌ **Multi-Modal AI** (photo analysis for skin conditions, throat images) - Nice-to-have, not essential for core flows
- ❌ **Epic/Cerner EMR Bi-Directional Sync** - Manual medical history intake acceptable for MVP (automation adds efficiency later)
- ❌ **LabCorp/Quest Automated Integration** - PDF lab orders acceptable for MVP (patient takes to lab, manual result upload)
- ❌ **Controlled Substance Prescribing** (EPCS certification for Schedule II-V) - Ryan Haight Act complexity, focus non-controlled first

**Deferred to Phase 3 (Months 16-24+):**
- ❌ **Pioneer Model** (30-40% cases fully automated, MD audit post-facto) - Requires extensive clinical validation, regulatory clarity
- ❌ **Predictive Healthcare** (AI predicts deterioration using wearables + EMR data) - Advanced AI capability, not MVP-critical
- ❌ **Pharmacogenomics Integration** (genetic testing for personalized drug selection) - Cutting-edge, research-level innovation
- ❌ **Market Expansion** (Vietnam domestic, global Vietnamese diaspora, other Asian-American communities) - Focus US Vietnamese-Americans first

---

### Post-MVP Features

**Phase 2 (Months 10-15): Enhanced Experience & Scale**

**User Experience Enhancements:**
- 🔄 **Voice AI Chatbot** (Vietnamese speech recognition + synthesis) - Elderly patients with limited typing ability
- 🔄 **Native Mobile Apps** (React Native iOS + Android) - Push notifications, better offline UX, app store presence
- 🔄 **Multi-Modal AI** (symptom photo analysis) - Upload throat photo, skin rash → AI visual analysis assists diagnosis
- 🔄 **Offline Mode** (progressive web app caching) - Rural areas with intermittent connectivity

**Advanced Integrations:**
- 🔄 **Epic/Cerner FHIR Real-Time Sync** - Import patient medical history from existing PCP (allergies, meds, conditions) → reduce intake time
- 🔄 **LabCorp/Quest Automated Integration** - Electronic lab order submission + automated result retrieval (no PDF, no manual upload)
- 🔄 **Amazon Pharmacy/PillPack Delivery** - Home prescription delivery coordination (convenience for elderly, medication adherence tracking)
- 🔄 **Wearable Device Integration** (Apple Health, Fitbit) - Real-time vitals for Monitoring Flow (blood pressure, glucose, heart rate)

**Clinical Capabilities:**
- 🔄 **Controlled Substance Prescribing** (EPCS certification) - Schedule II-V medications (opioids, benzos, stimulants) - requires Ryan Haight Act compliance
- 🔄 **Specialist Referral Coordination** - Automated referral generation to specialists (dermatology, cardiology) + appointment tracking
- 🔄 **Family Care Coordination** - Multi-patient household management (elderly parent + adult child accounts linked)

**Scale & Optimization:**
- 🔄 **Multi-Region Deployment** (US East + West for redundancy) - <100ms latency nationwide, disaster recovery
- 🔄 **Advanced Analytics Dashboard** - MD performance metrics, patient outcomes tracking, cost per case analysis
- 🔄 **Vietnamese NLP Fine-Tuning** - Custom medical terminology model trained on 10K+ real patient conversations (network effect moat)
- 🔄 **A/B Testing Framework** - Optimize AI prompts, UI flows, care pathways based on data

---

**Phase 3 (Months 16-24+): Autonomous AI & Market Expansion**

**Autonomous AI Evolution:**
- 🚀 **Pioneer Model** (30-40% routine cases fully automated) - AI generates prescription directly, US MD audits post-facto (regulatory innovation)
- 🚀 **Predictive Healthcare** - AI predicts patient deterioration before symptoms appear (wearables + EMR pattern analysis) → proactive interventions
- 🚀 **Personalized Medicine** - Pharmacogenomics integration (genetic testing → drug selection based on patient's genetic profile)
- 🚀 **Chronic Disease Management** - Automated protocols for diabetes, hypertension, COPD (AI-driven medication titration, lifestyle coaching)

**Market Expansion:**
- 🚀 **Vietnam Domestic Market** - Leverage VN MD network already in Vietnam, reverse direction (serve Vietnamese citizens in Vietnam)
- 🚀 **Global Vietnamese Diaspora** - Canada (220K Vietnamese), Australia (300K), Europe (200K) - 4M+ Vietnamese worldwide
- 🚀 **Other Asian-American Communities** - Replicate cultural-AI model for Chinese (5.4M), Korean (1.9M), Filipino (4.2M) Americans
- 🚀 **Enterprise B2B** - Sell to employers with large Vietnamese workforce (nail salons, restaurants) - employer-sponsored healthcare benefit

**Innovation Leadership:**
- 🚀 **Vietnamese Medical AI Research** - Publish peer-reviewed papers (JAMA, NEJM) on cultural-aware AI outcomes → thought leadership
- 🚀 **Open-Source Vietnamese Medical NLP** - Release models to community (talent recruitment, goodwill, ecosystem building)
- 🚀 **Industry Standard Setter** - FDA precedent for cultural-aware AI, HIMSS conference presentations, healthcare AI policy influence

---

### Risk Mitigation Strategy

**Technical Risks:**

**Risk 1: AI Hallucination → Medication Error (CRITICAL PATIENT SAFETY RISK)**
- **Probability**: Medium (2-5% hallucination rate in medical LLMs per research)
- **Impact**: Catastrophic (patient harm, lawsuit, FDA enforcement, platform shutdown)
- **Mitigation**:
  - **Triple Safety Net**: AI Critic Agent (error detection) → VN MD review (clinical judgment) → US MD final approval (regulatory signing)
  - **Explainable AI**: Reasoning chain visible to MDs (symptoms → differential → treatment rationale) - enables verification
  - **Confidence Thresholds**: AI confidence <70% → automatic escalation to MD (no auto-recommendations on uncertain cases)
  - **Drug Database Integration**: 100% drug interaction coverage (First Databank or Micromedex - industry gold standard)
  - **POC Validation Gate**: 50-100 test cases, ZERO medication errors required to proceed to MVP
  - **Continuous Monitoring**: MD override rate tracked weekly, patterns analyzed for systematic AI errors
- **Contingency**: If >1% medication error rate detected, immediately halt AI recommendations, switch to full human workflow until fixed

**Risk 2: FDA Regulatory Uncertainty (COULD DELAY LAUNCH OR REQUIRE COSTLY COMPLIANCE)**
- **Probability**: Medium (AI medical device regulation evolving, 2026 new guidance expected)
- **Impact**: High (6-12 month launch delay, $100K-500K additional compliance costs)
- **Mitigation**:
  - **FDA Pre-Submission Meeting**: Schedule Month 6 ($10K-15K regulatory consultant) - get official guidance before MVP launch
  - **Clinical Decision Support Positioning**: Frame as CDS tool (may reduce regulatory burden vs "diagnostic device" classification)
  - **510(k) Pathway**: 97% approval rate for AI medical devices 2026 (well-understood pathway, lower risk than de novo)
  - **PCCP (Predetermined Change Control Plan)**: Pre-approve algorithm update boundaries → iterate AI without resubmission
  - **Healthcare Attorney on Retainer**: $5K-10K for regulatory guidance throughout process
- **Contingency**: If FDA requires extensive pre-market validation, extend MVP timeline 3-6 months, raise additional $200K-300K for clinical studies

**Risk 3: Vietnamese NLP Accuracy Below Threshold (CULTURAL EXPRESSIONS NOT UNDERSTOOD)**
- **Probability**: Low-Medium (Vietnamese medical corpus limited, cultural nuances complex)
- **Impact**: High (product differentiation fails, patient dissatisfaction, competitive advantage lost)
- **Mitigation**:
  - **POC Validation**: Test 50+ cultural expressions ("bị nóng trong", "gió độc", "bị lạnh") → >90% accuracy required
  - **Fine-Tuning Dataset**: 5,000+ Vietnamese medical conversations (crowdsourced from Vietnamese MDs + medical interpreters)
  - **Hybrid NLP Pipeline**: GPT-4 multilingual base + Vietnamese medical fine-tuning + cultural expression mapping database
  - **Continuous Learning**: Patient corrections captured ("AI hiểu sai, ý tôi là...") → fed back to training data
  - **3-Month POC Buffer**: Dedicated NLP validation phase before MVP commitment
- **Contingency**: If <85% NLP accuracy, add human Vietnamese medical interpreter to workflow temporarily (manual fallback), iterate AI in parallel

---

**Market Risks:**

**Risk 4: Vietnamese-Americans Don't Trust AI for Healthcare (CULTURAL RESISTANCE)**
- **Probability**: Medium (elderly Vietnamese-Americans prefer traditional in-person care, skeptical of technology)
- **Impact**: High (low adoption rate, <500 patients by Month 6, product-market fit not achieved)
- **Mitigation**:
  - **Human-Centric Messaging**: Emphasize VN MD + US MD involvement (AI assists, doctors decide) - not "AI replaces doctors"
  - **Community Trust-Building**: Partner with Vietnamese churches, cultural centers, community organizations (trusted institutions)
  - **Physician Endorsement Strategy**: Vietnamese-American doctors publicly endorse platform (credibility by association)
  - **Free Trial Program**: First 100 users get 1-month free trial (reduce barrier to adoption, prove value before payment)
  - **Vietnamese-Language Education**: Explainer videos showing AI + MD collaboration, patient testimonials (Cô Lan story)
  - **Success Metric**: NPS >50 by Month 9 (strong word-of-mouth indicator)
- **Contingency**: If NPS <30, pivot messaging (reduce AI emphasis, increase human doctor visibility), add video consultations to MVP

**Risk 5: Insufficient Patient Volume (CAN'T REACH 500 PATIENTS BY MONTH 6)**
- **Probability**: Medium (cold-start problem, Vietnamese-Americans geographically dispersed across US)
- **Impact**: High (unit economics fail, can't validate product-market fit, investor confidence lost)
- **Mitigation**:
  - **Geographic Focus**: Launch CA, TX, FL only (60% of Vietnamese-American population = 1.3M concentrated)
  - **Facebook Group Marketing**: Vietnamese community groups very active (Orange County Vietnamese, Houston Vietnamese) - organic reach
  - **Referral Incentives**: $20 account credit for each successful referral (viral loop mechanism)
  - **Partnership Strategy**: Vietnamese medical clinics in Little Saigon (Orange County) refer overflow patients (trusted referral source)
  - **Content Marketing**: Vietnamese health education blog (diabetes, hypertension in Vietnamese) - SEO + trust building
  - **Pricing Flexibility**: If adoption slow, add $19/month "Care Essentials" tier (lower entry barrier)
- **Contingency**: If <250 patients Month 6, extend pilot phase 3 months, increase marketing spend $10K-20K, test different channels (Vietnamese radio, newspapers)

---

**Resource Risks:**

**Risk 6: Insufficient Capital (RUN OUT OF FUNDING BEFORE PRODUCT-MARKET FIT)**
- **Probability**: Medium (healthcare AI startups capital-intensive, 18-month runway at risk)
- **Impact**: Catastrophic (shutdown before validation, investor loss, team dissolution)
- **Mitigation**:
  - **Lean MVP Budget**: $150K-300K total for POC + MVP (bootstrap-friendly if needed)
  - **Phased Funding Strategy**: Raise $500K seed (18-month runway) → Series A after product-market fit proven (Month 12-15)
  - **Early Revenue Generation**: Launch subscriptions Month 9 → Self-sustaining by Month 15 if 2,000 patients @ $70 avg/month = $140K MRR
  - **Cost Optimization**: Open-source tools (LangGraph, PostgreSQL, Istio), VN MD labor arbitrage ($25-35/hr vs $150/hr US), hybrid LLM strategy (GPT-4 + Claude cost-optimized)
  - **Burn Rate Control**: <$25K/month MVP phase → <$50K/month production (tight expense management)
  - **Milestone-Based Spending**: Only proceed POC → MVP if success gates passed (avoid sunk costs on failed validation)
- **Contingency**: If funding constrained, reduce MVP scope to Prescription-only flow (defer Emergency, Lab, Monitoring), cut timeline to 6 months, launch with $100K budget

**Risk 7: Can't Hire Sufficient VN MDs or US MDs (WORKFORCE SHORTAGE)**
- **Probability**: Low-Medium (VN MDs abundant in Vietnam, US MDs competitive market)
- **Impact**: Medium (capacity constraints, can't scale to 10K patients, growth bottleneck)
- **Mitigation**:
  - **VN MD Recruitment**: Partner with Vietnam medical universities (Hanoi Medical, HCMC Medical) - abundant MD supply, 1/10 US salary attractive
  - **US MD Recruitment**: Target Vietnamese-American physicians (cultural fit + often have multi-state licenses) - competitive compensation $150/hr part-time
  - **IMLC Strategy**: Hire US MDs participating in Interstate Medical Licensure Compact (29 states accessible with single application)
  - **Scalability Math**: 1 VN MD handles 6 cases/hr, 1 US MD reviews 6 cases/hr → 10 VN MDs + 5 US MDs = 10K patients/month capacity (achievable)
  - **Flexible Contractor Model**: Part-time remote work (attractive for MDs seeking supplemental income, flexible schedules)
- **Contingency**: If US MD shortage acute, use telemedicine locum tenens agencies (higher cost $200-250/hr, acceptable for growth phase), expand IMLC recruitment

---

## Functional Requirements

### Patient Care Interaction

**FR1**: Patients can initiate a medical consultation via text-based chat in Vietnamese or English

**FR2**: Patients can describe symptoms using Vietnamese cultural health expressions that are understood by the system

**FR3**: Patients can switch between Vietnamese and English mid-conversation without restarting the session

**FR4**: Patients can upload medical history information (allergies, current medications, chronic conditions)

**FR5**: Patients can view their complete care plan (diagnosis, prescriptions, lab orders, monitoring protocols)

**FR6**: Patients can receive emergency guidance with 911 escalation when critical symptoms are detected

**FR7**: Patients can access their medical records and consultation history

**FR8**: Patients can receive notifications about prescription status, lab results, and monitoring check-ins

---

### AI-Assisted Clinical Workflow

**FR9**: AI Agent can conduct symptom intake by asking contextual follow-up questions

**FR10**: AI Agent can perform clinical screening and generate differential diagnoses

**FR11**: AI Agent can recommend treatment plans including medications, lab tests, and monitoring protocols

**FR12**: AI Agent can check for drug interactions using a comprehensive medication database

**FR13**: AI Agent can screen for patient allergies before recommending medications

**FR14**: AI Agent can detect emergency symptoms and trigger immediate escalation protocols

**FR15**: AI Agent can provide clinical reasoning and confidence scores for its recommendations

**FR16**: AI Critic Agent can validate and challenge primary AI recommendations for safety

---

### Vietnamese MD (VN MD) Workflow

**FR17**: VN MDs can access a priority queue of patient cases assigned to them

**FR18**: VN MDs can view complete AI screening results, symptom transcripts, and clinical assessments

**FR19**: VN MDs can review and modify AI treatment recommendations

**FR20**: VN MDs can create draft orders (prescriptions, lab requests, monitoring protocols)

**FR21**: VN MDs can conduct video consultations with patients (for Plus and Premium tiers)

**FR22**: VN MDs can document clinical notes in Vietnamese or English

**FR23**: VN MDs can escalate complex cases to US MD specialists

**FR24**: VN MDs can view patient medical history and previous consultations

---

### US MD (US MD) Workflow

**FR25**: US MDs can access a unified review queue filtered by their licensed states

**FR26**: US MDs can view complete case context (AI recommendations, VN MD draft orders, patient data)

**FR27**: US MDs can approve, modify, or reject VN MD draft orders

**FR28**: US MDs can electronically sign prescriptions for transmission to pharmacies

**FR29**: US MDs can verify their medical license matches the patient's state of residence

**FR30**: US MDs can document final clinical decisions and regulatory compliance notes

**FR31**: US MDs can view audit trails of all clinical decisions and data access

---

### Care Flow Management

**FR32**: System can orchestrate Emergency Flow (6 stations) with <15 minute response time

**FR33**: System can orchestrate Prescription Flow (9 stations) from intake to pharmacy transmission

**FR34**: System can orchestrate Lab/Imaging Flow (9 stations) from order creation to result tracking

**FR35**: System can orchestrate Monitoring Flow (14 stations) with automated check-ins (24hr, 48hr, 72hr)

**FR36**: System can implement 3-Stage Order Lifecycle (AI Recommendations → VN MD Draft → US MD Actual)

**FR37**: System can route cases based on subscription tier priority (Premium → Plus → Connect)

**FR38**: System can enforce SLA response times by tier (<1hr Premium, <2hr Plus, <4hr Connect)

---

### Prescription Management

**FR39**: System can generate electronic prescriptions in NCPDP SCRIPT standard format

**FR40**: System can transmit prescriptions to pharmacies via SureScripts network

**FR41**: System can verify prescription validity (dosing, duration, contraindications)

**FR42**: System can track prescription status (pending, transmitted, ready for pickup)

**FR43**: System can notify patients when prescriptions are ready at their pharmacy

**FR44**: System can handle prescription refill requests

**FR45**: System can restrict controlled substances (Schedule II-V) prescribing to approved flows

---

### Lab & Diagnostic Management

**FR46**: System can generate lab orders based on AI and MD recommendations

**FR47**: System can produce printable lab order PDFs for patients to take to LabCorp/Quest

**FR48**: System can allow manual upload of lab results by patients or staff

**FR49**: System can parse and display lab results in structured format

**FR50**: System can flag abnormal lab values for MD review

**FR51**: System can trigger follow-up workflows based on lab results

---

### Monitoring & Follow-Up

**FR52**: System can create automated monitoring protocols (24hr, 48hr, 72hr check-ins)

**FR53**: System can send AI-driven check-in messages to patients via chat

**FR54**: System can collect patient-reported outcomes during monitoring (symptom improvement, side effects)

**FR55**: System can escalate monitoring cases to MD review when patient reports deterioration

**FR56**: System can track medication adherence and effectiveness

**FR57**: System can close monitoring cases when patient outcomes are satisfactory

---

### Patient Account & Subscription Management

**FR58**: Patients can create accounts with email and phone verification

**FR59**: Patients can select subscription tiers (Connect $39, Plus $99, Premium $249)

**FR60**: Patients can enter and manage payment methods securely

**FR61**: Patients can upgrade or downgrade subscription tiers with pro-rated billing

**FR62**: Patients can cancel subscriptions with data retained per HIPAA requirements

**FR63**: Patients can view billing history and receipts

**FR64**: Patients can manage account settings (contact info, password, preferences)

---

### Authentication & Access Control

**FR65**: Users can authenticate via email/password with multi-factor authentication (MFA) for MDs

**FR66**: System can enforce role-based permissions (Patient, VN MD, US MD, AI Agent, Admin)

**FR67**: System can verify user identity before granting access to PHI

**FR68**: System can automatically log out inactive sessions after timeout period

**FR69**: System can prevent unauthorized access to patient data not assigned to a user

**FR70**: System can enable MFA via SMS codes or authenticator apps

---

### Compliance & Audit

**FR71**: System can log 100% of PHI access with timestamp, user ID, action type, and IP address

**FR72**: System can generate audit reports for HIPAA compliance reviews

**FR73**: System can verify US MD licensure in patient's state before prescribing

**FR74**: System can encrypt PHI at rest (AES-256) and in transit (TLS 1.3)

**FR75**: System can de-identify PHI before sending to external LLM APIs

**FR76**: System can track consent status for HIPAA authorization and telemedicine consent

**FR77**: System can enforce data retention policies (7 years minimum per HIPAA)

**FR78**: System can restrict PHI storage to US-only cloud regions

---

### Integration & Interoperability

**FR79**: System can integrate with SureScripts for e-prescribing to 95%+ US pharmacies

**FR80**: System can integrate with Stripe for subscription billing and payment processing

**FR81**: System can integrate with Auth0 or AWS Cognito for identity management

**FR82**: System can integrate with Twilio for SMS notifications and MFA codes

**FR83**: System can store patient data in FHIR R4 format (Patient, MedicationRequest, DiagnosticReport, CarePlan)

**FR84**: System can export patient data in FHIR format upon patient request

---

### Platform Administration

**FR85**: Admins can view platform-wide metrics (patient volume, case completion rates, MD productivity)

**FR86**: Admins can manage user accounts (activate, suspend, reset passwords)

**FR87**: Admins can configure subscription tiers and pricing

**FR88**: Admins can manage MD contractor roster (VN MD and US MD licenses, availability)

**FR89**: Admins can access audit logs for compliance investigations

**FR90**: Admins can generate compliance reports (HIPAA, SOC 2, FDA)

---

### Emergency & Safety

**FR91**: System can detect emergency keywords (chest pain, difficulty breathing, stroke signs)

**FR92**: System can immediately halt normal workflow when emergency detected

**FR93**: System can display 911 guidance and nearest ER locations to patients

**FR94**: System can notify on-call MD when emergency case occurs

**FR95**: System can track patient outcome after emergency escalation

**FR96**: System can maintain zero-error tolerance for drug interactions and allergies

---

### Vietnamese Language & Cultural Understanding

**FR97**: System can recognize and translate Vietnamese cultural health expressions to medical terminology

**FR98**: System can maintain conversation context when patients code-switch between Vietnamese and English

**FR99**: System can provide AI responses in natural Vietnamese (not literal translations)

**FR100**: System can explain medical diagnoses and treatment plans in culturally-appropriate Vietnamese

---

**CAPABILITY CONTRACT NOTICE:**

This FR list (FR1-FR100) defines the complete capability inventory for the MVP (Months 1-9). Any feature not explicitly listed here will NOT exist in the final product unless we formally add it to this requirements list. This is the binding contract between product vision and implementation.

**Downstream Usage:**
- **UX Designers**: Will design interactions ONLY for capabilities listed in FR1-FR100
- **Architects**: Will design systems to support ONLY capabilities listed in FR1-FR100
- **Epic Breakdown**: Will implement ONLY capabilities listed in FR1-FR100

---

## Non-Functional Requirements

### Performance

**NFR-P1: Chat Response Time**
- AI chatbot initial response: <2 seconds (P95 percentile)
- AI follow-up questions: <1 second (P95 percentile)
- Justification: Real-time conversational flow critical for patient engagement and trust

**NFR-P2: Care Flow SLA Enforcement**
- Premium tier: <1 hour end-to-end (AI screening → VN MD → US MD approval)
- Plus tier: <2 hours end-to-end
- Connect tier: <4 hours end-to-end
- Justification: SLA compliance is subscription value proposition and competitive differentiator

**NFR-P3: API Latency**
- FHIR API calls: <500ms (P95 percentile)
- SureScripts e-prescribing: <3 seconds for prescription transmission
- Drug interaction database queries: <200ms (critical path for safety)
- Justification: Clinical workflow efficiency and patient safety depend on real-time data access

**NFR-P4: Page Load Time**
- Patient web portal initial load: <3 seconds on 4G connection
- MD dashboard initial load: <2 seconds (high-bandwidth assumption)
- Mobile-responsive PWA load: <4 seconds on 3G connection
- Justification: User experience quality, especially for elderly patients with limited patience for slow loading

**NFR-P5: Concurrent User Support**
- System supports 500+ concurrent chat sessions without performance degradation
- MD dashboards support 50+ simultaneous VN MD + US MD logins
- Justification: Scale target (500 MVP → 10K production) requires concurrent capacity planning

---

### Security

**NFR-S1: Data Encryption**
- PHI encrypted at rest: AES-256 encryption for all database storage
- PHI encrypted in transit: TLS 1.3 minimum (TLS 1.2 and below deprecated)
- LLM API calls: PHI de-identified before external transmission (re-identify after response)
- Justification: HIPAA Security Rule mandates, patient trust, regulatory compliance

**NFR-S2: Access Control**
- Role-Based Access Control (RBAC) enforced at API gateway, service layer, and database layer
- Multi-Factor Authentication (MFA) mandatory for all MD logins (VN MD + US MD)
- Session timeout: 15 minutes for patient sessions, 60 minutes for MD sessions
- Justification: HIPAA minimum necessary principle, prevent unauthorized PHI access

**NFR-S3: Audit Logging**
- 100% of PHI access logged with: timestamp, user ID, IP address, action type, resource accessed
- Audit logs immutable (write-once, append-only)
- Audit log retention: 7 years minimum (HIPAA requirement)
- Justification: HIPAA audit requirements, forensic investigation capability, compliance validation

**NFR-S4: Authentication Security**
- Password complexity: Minimum 12 characters, require uppercase, lowercase, number, special character
- MFA codes: 6-digit OTP, 5-minute expiration, SMS + authenticator app support
- Failed login lockout: 5 attempts → account locked for 30 minutes
- Justification: HIPAA Security Rule, prevent brute force attacks, protect against credential stuffing

**NFR-S5: Network Security**
- Zero-Trust Architecture: Every service-to-service call verified (no implicit trust)
- Service mesh mTLS: Mutual TLS between all microservices (Istio enforcement)
- VN MD remote access: VPN + mTLS tunnel required for Vietnam-based access
- Justification: HIPAA 2026 updates mandate zero-trust, cross-border access security

---

### Scalability

**NFR-SC1: User Growth Support**
- System scales from 500 users (MVP Month 9) to 10,000 users (Production Month 18) with <10% performance degradation
- Horizontal pod autoscaling: Kubernetes pods scale automatically based on CPU/memory thresholds
- Database connection pooling: Support 1,000+ concurrent database connections
- Justification: 20x growth trajectory, avoid costly re-architecture, maintain SLA compliance at scale

**NFR-SC2: AI Agent Scalability**
- AI agent orchestration supports 500+ concurrent AI workflows (LangGraph parallel execution)
- LLM API rate limits: Support 1,000 requests/minute (OpenAI Tier 4 or equivalent)
- Cost optimization: Maintain <$5 per patient interaction LLM cost (hybrid GPT-4 + Claude strategy)
- Justification: AI automation is cost advantage - must scale economically

**NFR-SC3: Geographic Expansion**
- Architecture supports multi-region deployment (US East + US West) for Phase 2
- Data replication: Cross-region backup with <1 hour RPO (Recovery Point Objective)
- Latency optimization: <100ms API latency for 95% of US users (CDN + regional endpoints)
- Justification: National expansion plans (CA, TX, FL → 50 states), disaster recovery

**NFR-SC4: Medical Team Scalability**
- Platform supports 100+ VN MD contractors + 50+ US MD contractors (production scale)
- Case routing system handles 10,000+ cases/day throughput
- Queue management: Priority queues scale to 1,000+ pending cases without degradation
- Justification: MD workforce scales with patient volume, maintain SLA at scale

---

### Reliability

**NFR-R1: System Uptime**
- 99.9% uptime SLA (maximum 8.76 hours downtime per year)
- Planned maintenance windows: <2 hours/month, scheduled during low-traffic periods (2-4am PT)
- Justification: 24/7 healthcare service - downtime directly impacts patient care and emergency access

**NFR-R2: Data Durability**
- Database backup: Daily automated backups with 30-day retention
- Point-in-time recovery: Restore to any point within last 7 days
- Backup testing: Monthly restore validation tests (ensure backups are not corrupted)
- Justification: PHI loss catastrophic (HIPAA breach), patient safety, legal liability

**NFR-R3: Fault Tolerance**
- Database: Multi-AZ deployment (AWS RDS or GCP Cloud SQL high availability)
- Message queue: Kafka multi-broker replication (replication factor 3)
- Service redundancy: Minimum 2 pods per microservice (eliminate single point of failure)
- Justification: Healthcare cannot tolerate single points of failure, emergency flow requires resilience

**NFR-R4: Error Recovery**
- AI hallucination detection: <2% false positive rate for AI Critic Agent (don't block valid recommendations)
- Failed prescription transmission retry: 3 automatic retries with exponential backoff
- Payment processing retry: Stripe automatic retry on failed payments (3 attempts over 10 days)
- Justification: Graceful degradation, user experience quality, revenue protection

---

### Compliance & Regulatory

**NFR-C1: HIPAA Compliance**
- HITRUST CSF alignment: Self-attestation for MVP, full certification by Month 18
- Privacy Rule compliance: Patient rights (access, amendment, accounting of disclosures) implemented
- Breach notification: <72 hour notification to HHS if breach affects >500 individuals
- Justification: Legal requirement, patient trust, enterprise customer prerequisite

**NFR-C2: FDA Regulatory Alignment**
- Clinical Decision Support positioning: Frame platform as CDS tool (not diagnostic device)
- 510(k) pathway readiness: Documentation prepared for Pre-Submission meeting Month 6
- QMSR compliance: Quality Management System Regulation aligned (Feb 2026 mandate)
- GMLP framework: Good Machine Learning Practice followed for AI model validation
- Justification: FDA enforcement risk, market access, investor confidence

**NFR-C3: State Medical Licensing Compliance**
- Automated verification: US MD license verified in patient's state before prescription generation
- Monthly license checks: All MD contractors verified against National Practitioner Data Bank
- Geofencing: Patients outside US MD licensed states blocked from prescription flow
- Justification: Medical practice laws, liability protection, regulatory compliance

**NFR-C4: Data Residency**
- US-only PHI storage: All patient data stored in US cloud regions (AWS us-east-1, us-west-2 or GCP us-central1, us-east4)
- No cross-border data transfer: VN MD accesses US servers directly (no data replication to Vietnam)
- Audit trail proof: Logs prove PHI never left US jurisdiction (regulatory defense)
- Justification: HIPAA safe harbor, cross-border privacy law compliance, regulatory clarity

**NFR-C5: Business Associate Agreements**
- All vendors handling PHI have signed BAAs: Cloud provider, LLM providers, SureScripts, Auth0/Cognito, Twilio
- BAA compliance monitoring: Annual vendor compliance reviews
- Subcontractor BAAs: VN MD contractors sign HIPAA BAAs (legal liability enforcement)
- Justification: HIPAA Business Associate Rule, legal liability chain, vendor accountability

---

### Accessibility

**NFR-A1: Language Accessibility**
- Vietnamese language support: All patient-facing interfaces available in Vietnamese
- Code-switching support: AI handles Vietnamese-English mixed conversations naturally
- Cultural expression understanding: AI trained on 50+ Vietnamese cultural health terms
- Justification: Core product differentiator, target user base (Vietnamese-Americans), market fit

**NFR-A2: Mobile Accessibility**
- Mobile-responsive design: All features accessible on smartphones (iOS Safari, Android Chrome)
- Touch target size: Minimum 44x44px tap targets (elderly-friendly)
- Font size flexibility: Support system font size settings (accessibility zoom)
- Justification: Elderly Vietnamese users (50+ age group), mobile-first user behavior

**NFR-A3: WCAG Compliance (Deferred)**
- WCAG 2.1 Level AA compliance: Deferred to Phase 2 (not MVP-critical, focus on Vietnamese language accessibility first)
- Screen reader support: Deferred to Phase 2
- Keyboard navigation: Deferred to Phase 2
- Justification: Prioritize core differentiator (Vietnamese language) over general accessibility, add WCAG after product-market fit

---
