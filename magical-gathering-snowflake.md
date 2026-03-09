# Plan: Nâng cấp Intake Agent — Phỏng vấn thông minh theo Clinical Protocol

## Context

Hiện tại Intake Agent quá đơn giản: chỉ có 1 system prompt cố định, hỏi OLDCARTS chung chung, không biết phân loại bệnh, không có câu hỏi chuyên biệt theo triệu chứng, emergency detection chỉ là keyword matching đơn giản. Cần nâng cấp dựa trên `clinical-intake-protocol.md` — tài liệu lâm sàng 958 dòng với 20 protocol bệnh chi tiết.

**Mục tiêu:** Agent phỏng vấn thông minh như bác sĩ thật — nhận diện loại bệnh → hỏi đúng câu hỏi chuyên biệt → sàng lọc red flag sớm → theo dõi tiến độ → tạo dữ liệu có cấu trúc cho screening agent.

---

## Thay đổi chính

### 1. Complaint Protocol Data Layer (file mới)
**File:** `app/agents/prompts/complaint_protocols.py`

Định nghĩa 11 protocol bệnh (10 Tier-1 + Chest Pain):
- `hypertension` — home BP, nước mắm/muối, compliance
- `diabetes` — A1c, polyuria/polydipsia, rice consumption
- `uri_cough` — fever, productive/dry cough, TB screening (quan trọng cho VN)
- `headache` — thunderclap, worst headache of life, aura
- `back_joint_pain` — radiation, bowel/bladder (cauda equina)
- `abdominal_gi` — location quadrant, HepB screening (critical VN population)
- `mental_health` — PHQ-2, safety screening (mandatory), somatization detection
- `skin_rash` — spreading, fever + rash, new exposures
- `urinary` — dysuria, flank pain, UTI history
- `fatigue` — acute vs chronic, depression overlap
- `chest_pain` — 3 safety questions TRƯỚC, red_flags_first priority

Mỗi protocol gồm:
- `keywords_en/vi` — từ khóa phân loại CC
- `hpi_additions` — câu hỏi HPI chuyên biệt (ngoài OLDCARTS chung)
- `red_flags` — red flag riêng với message song ngữ EN/VI
- `ros_focus` — hệ cơ quan cần hỏi ROS
- `cultural_notes` — lưu ý văn hóa VN

Hàm `classify_chief_complaint(text) -> str` — keyword matching để chọn protocol.

### 2. Intake Tracker (file mới)
**File:** `app/agents/tools/intake_tracker.py`

Class theo dõi tiến độ phỏng vấn:
- **Phase tracking:** `greeting → cc → red_flag_screening → hpi → ros → pmh → medications → allergies → social_family → summary → complete`
- **OLDCARTS coverage:** track 8 fields (onset, location, duration, character, aggravating, alleviating, timing, severity)
- **Section completeness:** CC, HPI (6/8), ROS (2+ systems), PMH, meds, allergies, red flags
- **Progress indicator:** "khoảng nửa chặng đường" / "sắp xong"
- `is_minimum_complete()` — check đủ data cho SOAP generation
- `to_dict()`/`from dict` — serialize vào session store

**Cơ chế trích xuất dữ liệu:** LLM gắn marker ẩn `[INTAKE:field=value]` trong response. `intake_agent.py` parse marker → cập nhật tracker → strip marker trước khi gửi bệnh nhân. Nếu LLM quên marker → tracker không advance → prompt tiếp tục hỏi → graceful degradation.

### 3. Emergency Detector nâng cấp (sửa file có sẵn)
**File:** `app/agents/tools/emergency_detector.py`

- Giữ nguyên `detect_emergency()` + `get_emergency_keywords_found()` (backward compatible)
- Thêm `detect_contextual_red_flags(text, complaint_category)` — red flag theo ngữ cảnh bệnh
- Thêm `get_red_flag_screening_questions(complaint_category)` — câu hỏi sàng lọc red flag
- Multi-keyword combinations: chest pain + dyspnea + diaphoresis → 911
- Emergency message song ngữ riêng cho từng loại red flag

### 4. Dynamic Prompt Composer (rewrite file có sẵn)
**File:** `app/agents/prompts/intake_prompt.py`

Thay prompt cố định bằng `compose_intake_prompt(tracker, protocol, language, msg_count)`:
- Phase-aware: mỗi phase có instruction riêng
- Complaint-aware: include câu hỏi HPI chuyên biệt
- Completeness-aware: list sections còn thiếu
- Marker instruction: hướng dẫn LLM emit `[INTAKE:field=value]`
- Giữ `INTAKE_SYSTEM_PROMPT` constant cho backward compatibility

### 5. Intake Agent nâng cấp (sửa file có sẵn)
**File:** `app/agents/intake_agent.py`

- Load/create IntakeTracker từ state
- Classify CC → chọn complaint protocol
- Dùng `compose_intake_prompt()` thay vì prompt cố định
- Parse `[INTAKE:field=value]` markers từ LLM response
- Contextual emergency detection
- Populate `intake_data` dict (trước đây text mode KHÔNG populate)
- Return `intake_tracker`, `intake_data`, `intake_complete` trong state
- Greeting mới: thêm thời gian ước lượng "10-15 phút"

### 6. State + API updates (sửa nhỏ)
- `app/agents/state.py` — thêm `intake_tracker: dict | None`
- `app/api/v1/routes/chat.py` — persist tracker state, thêm progress
- `app/api/v1/schemas/chat.py` — thêm `intake_progress`, `current_phase`

### 7. Voice service sync (sửa vừa)
**File:** `app/domain/services/gemini_live_service.py`
- Mở rộng field enum (thêm ros_finding, pmh, social_history, family_history)
- Update voice system instruction cho khớp với prompt mới

---

## Thứ tự thực hiện

| Step | File(s) | Mô tả | Tests |
|------|---------|--------|-------|
| 1 | `complaint_protocols.py` | 11 protocols + classify function | `test_complaint_protocols.py` |
| 2 | `intake_tracker.py` | Tracker class | `test_intake_tracker.py` |
| 3 | `emergency_detector.py` | Contextual red flags | `test_contextual_emergency.py` + verify 9 existing tests pass |
| 4 | `intake_prompt.py` | Dynamic prompt composer | `test_intake_prompt_composer.py` |
| 5 | `intake_agent.py` | Core integration | Update `test_intake_agent.py` + verify all 120 tests pass |
| 6 | `state.py`, `chat.py`, schema | State + API | Minor updates |
| 7 | `gemini_live_service.py` | Voice sync | Verify existing tests |

---

## Backward Compatibility

- `intake_node()` signature KHÔNG đổi
- `INTAKE_SYSTEM_PROMPT` constant giữ nguyên (alias cho compose())
- `detect_emergency()` + `get_emergency_keywords_found()` giữ nguyên
- `CareFlowState` thêm optional field (không break existing code)
- Screening agent đọc `intake_data` → giờ có data thay vì None → tốt hơn
- All 120 existing unit tests phải PASS

## Verification

1. Chạy `pytest tests/unit/ -v` — tất cả tests (cũ + mới) phải pass
2. Start server, chat test với các kịch bản:
   - Đau đầu (Vietnamese) → verify headache protocol kicks in
   - Chest pain (English) → verify 3 safety questions FIRST
   - Đau bụng + mention "viêm gan B" → verify HepB screening
   - "Tôi buồn lắm, không muốn sống" → verify PHQ + safety screening + crisis line
   - Normal cold → verify generic OLDCARTS + TB screening question
3. Verify `intake_data` populated → run full care flow → screening agent gets structured data
4. Verify progress indicator in API response
