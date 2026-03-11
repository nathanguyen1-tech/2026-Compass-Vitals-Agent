# Compass Vitals Agent — Emergency Detection Reference

**Version:** 1.0
**Date:** March 11, 2026
**System:** Compass Vitals Agent — AI-powered Clinical Intake
**Language Support:** Vietnamese (Tiếng Việt) + English

---

## Overview

Hệ thống Emergency Detection của Compass Vitals Agent sử dụng **4 tầng phát hiện** (4-tier detection) hoàn toàn dựa trên keyword matching (không phụ thuộc LLM) để đảm bảo tốc độ phản hồi < 1ms và độ tin cậy 100%.

Mọi text input từ bệnh nhân đều được quét qua cả 4 tầng trước khi AI phản hồi.

---

## Tier 1 — Instant Emergency (Gọi 911 ngay lập tức)

**Đặc điểm:** Không cần xác nhận LLM. Phát hiện = Cảnh báo ngay.
**Lý do:** Trì hoãn 1 phút = nguy cơ tử vong.

### Vietnamese Keywords

| Nhóm | Keyword (Unicode) | Keyword (ASCII-folded) |
|-------|-------------------|----------------------|
| Mất ý thức / Co giật | mất ý thức | mat y thuc |
| | bất tỉnh | bat tinh |
| | hôn mê | hon me |
| | co giật | co giat |
| Tự tử / Tự hại | tự tử | tu tu |
| | muốn chết | muon chet |
| | không muốn sống | khong muon song |
| Xuất huyết tiêu hóa | ói ra máu | oi ra mau |
| | nôn ra máu | non ra mau |
| | đi cầu ra máu | di cau ra mau |
| Quá liều | uống thuốc quá liều | uong thuoc qua lieu |

### English Keywords

| Category | Keywords |
|----------|----------|
| Loss of consciousness / Seizure | unconscious, loss of consciousness, seizure |
| Suicide / Self-harm | want to die, kill myself, suicide |
| GI Hemorrhage | vomiting blood, bloody stool, coughing blood |
| Anaphylaxis | anaphylaxis |
| Overdose | overdose |

### Vital Signs (Nhiệt độ / Temperature)

| Threshold | Value | Action |
|-----------|-------|--------|
| Celsius | ≥ 40.0°C | Emergency — Hyperpyrexia |
| Fahrenheit | ≥ 104.0°F | Emergency — Hyperpyrexia |

**Patterns nhận diện:** `42°C`, `42 do C`, `42 độ`, `sot 42`, `nhiet do 42`, `fever 104`, `104°F`

> **Note:** Vital signs luôn trigger emergency bất kể ngữ cảnh phủ định. "Tôi không sốt 42 độ" vẫn trigger vì giá trị số tự nó đã nguy hiểm.

---

## Tier 2 — Full Emergency Keywords (LLM xác nhận bằng 2 câu hỏi)

**Đặc điểm:** Khi phát hiện keyword, LLM sẽ hỏi 2 câu xác nhận trước khi escalate.
**Lý do:** Các triệu chứng này có thể có nhiều mức độ nghiêm trọng khác nhau.

### Vietnamese Keywords

| Nhóm | Keywords (Unicode) | Keywords (ASCII-folded) |
|-------|-------------------|----------------------|
| Tim mạch / Hô hấp | đau ngực, khó thở, không thở được, tê nửa người, đau ngực trái, đau lan ra cánh tay | dau nguc, kho tho, khong tho duoc, te nua nguoi, dau nguc trai, dau lan ra canh tay |
| Thần kinh | đột ngột yếu nửa người, méo miệng, nói ngọng đột ngột, mất thị lực đột ngột | dot ngot yeu nua nguoi, meo mieng, noi ngong dot ngot, mat thi luc dot ngot |
| Mất ý thức | mất ý thức, bất tỉnh, ngất, ngất xỉu, hôn mê | mat y thuc, bat tinh, ngat, ngat xiu, hon me |
| Chảy máu / Co giật | chảy máu nhiều, co giật | chay mau nhieu, co giat |
| Tự tử / Tự hại | tự tử, muốn chết, không muốn sống | tu tu, muon chet, khong muon song |
| Xuất huyết tiêu hóa | ói ra máu, nôn ra máu, đi cầu ra máu | oi ra mau, non ra mau, di cau ra mau |
| Sốc phản vệ | sưng họng, phù mặt | sung hong, phu mat |
| Quá liều | uống thuốc quá liều | uong thuoc qua lieu |

### English Keywords

| Category | Keywords |
|----------|----------|
| Cardiac / Respiratory | chest pain, difficulty breathing, can't breathe, numbness, heart attack |
| Neurological | sudden weakness, facial drooping, slurred speech, stroke signs |
| Loss of consciousness | unconscious, loss of consciousness, fainting, seizure |
| Bleeding | severe bleeding |
| Suicide / Self-harm | want to die, kill myself, suicide |
| GI Hemorrhage | vomiting blood, bloody stool, coughing blood |
| Anaphylaxis | throat swelling, throat closing, anaphylaxis |
| Overdose | overdose |

---

## Tier 3 — Complaint-Specific Red Flags (11 Protocols)

Khi bệnh nhân đã được phân loại vào 1 trong 11 protocol, hệ thống sẽ kiểm tra thêm các red flags đặc thù cho loại bệnh đó.

### 3.1 Hypertension (Tăng huyết áp)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| hypertensive_emergency | BP >180/120 + headache/vision changes/chest pain | `180`, `vision changes`, `thay doi thi luc`, `mat mo` | ER |

### 3.2 Diabetes (Tiểu đường)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| dka_symptoms | DKA: nausea/vomiting + confusion + rapid breathing | `nausea`, `vomiting`, `confusion`, `rapid breathing`, `buon non`, `oi`, `lon xon`, `tho nhanh` | ER |

### 3.3 URI / Cough (Nhiễm trùng hô hấp / Ho)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| meningitis_signs | High fever + stiff neck | `stiff neck`, `cung co`, `cung gay` | ER |
| respiratory_distress | Difficulty breathing or coughing blood | `difficulty breathing`, `coughing blood`, `hemoptysis`, `kho tho`, `ho ra mau` | ER |

### 3.4 Headache (Đau đầu)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| thunderclap_headache | Worst headache of life / sudden onset | `worst headache`, `thunderclap`, `worst of my life`, `dau nhat`, `dot ngot du doi`, `chua tung dau nhu vay` | **911** |
| headache_neuro_deficit | Headache + neurological deficits or fever + stiff neck | `numbness`, `weakness`, `vision loss`, `slurred speech`, `te`, `yeu`, `mat thi luc`, `noi ngong` | ER |

### 3.5 Back / Joint Pain (Đau lưng / Đau khớp)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| cauda_equina | Loss of bowel/bladder control + saddle anesthesia + progressive weakness | `bladder control`, `bowel control`, `saddle`, `mat kiem soat tieu`, `mat kiem soat dai tien`, `te vung ngoi` | ER |

### 3.6 Abdominal / GI (Đau bụng / Tiêu hóa)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| acute_abdomen | Severe RLQ pain + fever / rigid abdomen | `rigid abdomen`, `severe abdominal`, `bloody stool`, `bung cung`, `dau bung du doi`, `di cau ra mau` | ER |

### 3.7 Mental Health (Sức khỏe tâm thần)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| suicidal_ideation | Active suicidal ideation with plan | `kill myself`, `suicide`, `end my life`, `don't want to live`, `want to die`, `self-harm`, `tu tu`, `khong muon song`, `muon chet`, `tu hai`, `cham dut cuoc song` | **911** + 988 Lifeline |

### 3.8 Skin Rash (Phát ban)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| sjs_concern | Rapidly spreading rash + fever + mucosal involvement (SJS) | `spreading rash`, `mouth sores`, `eye`, `blistering`, `lan nhanh`, `lot mieng`, `bong nuoc` | ER |

### 3.9 Urinary (Tiết niệu)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| pyelonephritis | High fever + flank pain / urinary retention | `high fever`, `flank pain`, `can't urinate`, `retention`, `sot cao`, `dau hong lung`, `bi tieu`, `khong tieu duoc` | ER |

### 3.10 Fatigue (Mệt mỏi)

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| sudden_weakness | Sudden onset weakness (especially one-sided) — stroke | `sudden weakness`, `one-sided`, `one side`, `yeu dot ngot`, `mot ben`, `nua nguoi` | **911** |

### 3.11 Chest Pain (Đau ngực) — Highest Stakes

| Red Flag ID | Pattern | Keywords | Action |
|-------------|---------|----------|--------|
| acs_active | Active chest pain + diaphoresis/dyspnea/syncope | `chest pain now`, `sweating`, `can't breathe`, `dau nguc ngay`, `do mo hoi`, `kho tho` | **911** |
| aortic_dissection | Tearing/ripping chest pain radiating to back | `tearing`, `ripping`, `radiating to back`, `xe`, `rach`, `lan ra lung` | **911** |
| chest_pain_with_leg_swelling | Chest pain + unilateral leg swelling (PE) | `leg swelling`, `swollen leg`, `one leg`, `sung chan`, `phu chan` | **911** |

---

## Tier 4 — Cross-Complaint Combination Patterns

Các pattern này kiểm tra **tổ hợp nhiều nhóm keyword** cùng lúc, không phụ thuộc vào protocol cụ thể nào. Áp dụng trên toàn bộ conversation context (4 messages gần nhất).

### 4.1 Stroke Signs (Dấu hiệu đột quỵ — FAST)

| Keyword Group | Keywords | Min Groups Required |
|---------------|----------|-------------------|
| Face droop | face droop, facial drooping, drooping, meo mieng | **1 of 3** |
| Arm weakness | arm weakness, one side weak, yeu mot ben, yeu nua nguoi | |
| Speech difficulty | slurred speech, speech difficulty, noi ngong, noi kho | |

**Action:** 911
**Message:** "These could be signs of a stroke. Please call 911 immediately."

### 4.2 Anaphylaxis (Sốc phản vệ)

| Keyword Group | Keywords | Min Groups Required |
|---------------|----------|-------------------|
| Allergic reaction | throat swelling, throat closing, throat is closing, sung hong, nghet tho, noi me day, nổi mề đay, hives, swollen face, phu mat, phù mặt | **2 of 2** (Both groups must match) |
| Respiratory distress | can't breathe, difficulty breathing, kho tho, cannot breathe, khó thở | |

**Action:** 911
**Message:** "These symptoms could be anaphylaxis. Please call 911 and use EpiPen if available."

### 4.3 Alcohol Withdrawal (Cai rượu)

| Keyword Group | Keywords | Min Groups Required |
|---------------|----------|-------------------|
| Withdrawal context | withdrawal, cai ruou, bo ruou | **2 of 2** (Both groups must match) |
| Physical symptoms | tremor, shaking, run, run tay | |

**Action:** ER
**Message:** "Alcohol withdrawal can be dangerous. Please go to the nearest ER immediately."

---

## Negation Handling (Xử lý phủ định)

Hệ thống có khả năng nhận diện ngữ cảnh phủ định để tránh false positive.

### Negation Prefixes — English
`no`, `not`, `don't have`, `do not have`, `without`, `deny`, `denies`, `negative for`

### Negation Prefixes — Vietnamese
`khong` / `không`, `khong bi` / `không bị`, `khong co` / `không có`, `chua bi` / `chưa bị`

### Examples

| Input | Emergency? | Reason |
|-------|-----------|--------|
| "tôi đau ngực" | Yes | Keyword match, no negation |
| "toi khong bi dau nguc" | **No** | Negation prefix "khong bi" detected |
| "I don't have chest pain" | **No** | Negation prefix "don't have" detected |
| "toi khong muon chet" | **No** | Negation "khong" before "muon chet" |
| "nhiệt độ 42 độ, nhưng không sốt" | **Yes** | Vital signs (≥40°C) — ALWAYS trigger regardless of negation |

> **Note:** Negation handling chỉ áp dụng cho Tier 1 (Instant) và `detect_emergency_with_negation()`. Tier 2 standard `detect_emergency()` không kiểm tra negation — luôn trigger nếu match keyword.

---

## Mandatory Screening Questions (Câu hỏi sàng lọc bắt buộc)

Khi bệnh nhân được phân loại vào protocol cụ thể, AI **bắt buộc** phải hỏi các câu hỏi sàng lọc an toàn sau:

### Chest Pain (3 câu hỏi an toàn — hỏi TRƯỚC tiên)
1. "Bạn có đang đau ngực NGAY LÚC NÀY không?" / "Is the chest pain happening RIGHT NOW?"
2. "Bạn có bị khó thở, đổ mồ hôi, buồn nôn, hoặc đau ở hàm/tay/lưng không?" / "Are you also having shortness of breath, sweating, nausea, or pain in your jaw/arm/back?"
3. "Bạn có tiền sử bệnh tim, đặt stent, hoặc phẫu thuật bypass không?" / "Do you have a history of heart disease, stents, or bypass surgery?"

### Headache (3 câu hỏi)
1. "Đây có phải là cơn đau đầu dữ dội nhất trong đời bạn không? Nó có đến đột ngột không?"
2. "Bạn có bị sốt kèm cứng cổ không?"
3. "Bạn có bị tê, yếu, thay đổi thị lực, hoặc khó nói không?"

### Abdominal / GI (3 câu hỏi)
1. "Đau có dữ dội và ở phía bên phải bụng dưới không?"
2. "Bạn có bị sốt kèm đau bụng không?"
3. "Bạn có đi cầu ra máu hoặc ói ra máu không?"

### Back / Joint Pain (3 câu hỏi)
1. "Bạn có bị thay đổi về kiểm soát tiểu tiện hoặc đại tiện không?"
2. "Bạn có bị tê ở vùng giữa hai chân (vùng ngồi) không?"
3. "Bạn có bị yếu dần ở chân không?"

### Mental Health (1 câu hỏi bắt buộc)
1. "Bạn có từng nghĩ đến việc tự làm hại mình hoặc không muốn sống không?" / "Have you had thoughts of hurting yourself or not wanting to be alive?"

### Fatigue (1 câu hỏi)
1. "Sự yếu có đến đột ngột không, đặc biệt là ở một bên người?"

---

## Action Legend

| Action | Meaning | Response |
|--------|---------|----------|
| **911** | Life-threatening — call 911 immediately | AI hiển thị cảnh báo đỏ + hướng dẫn gọi 911 |
| **ER** | Urgent — go to nearest Emergency Room | AI khuyên đến phòng cấp cứu ngay |
| **urgent_review** | Needs physician review within hours | AI escalate to physician queue |

---

## Technical Notes

- **Detection method:** 100% keyword-based (pure Python string matching). Không sử dụng LLM cho detection.
- **Vietnamese support:** Hỗ trợ cả Unicode có dấu (`đau ngực`) và ASCII-folded không dấu (`dau nguc`). Sử dụng `_strip_vietnamese_diacritics()` để normalize input.
- **Performance:** < 1ms per check. Chạy trên mọi message trước khi gửi đến LLM.
- **LLM role:** LLM chỉ đóng vai trò phỏng vấn viên (interviewer) và xác nhận (confirmer) — KHÔNG đưa ra quyết định emergency.
- **Source files:**
  - `services/ai-agent-service/app/agents/tools/emergency_detector.py`
  - `services/ai-agent-service/app/agents/prompts/complaint_protocols.py`

---

*Document generated from Compass Vitals Agent source code — March 2026*
