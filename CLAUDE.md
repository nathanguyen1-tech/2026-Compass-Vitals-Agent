# CLAUDE.md — Context cho Claude Code

## Project: Compass Vitals Agent

Đây là hệ thống AI intake agent cho chăm sóc sức khỏe từ xa của Compass Vitals Healthcare.

### Stack
- Python 3.12
- FastAPI + LangGraph + LangChain
- Gemini / Claude / OpenAI (via LLM Gateway)
- PostgreSQL (session persistence)

### Cấu trúc quan trọng

```
services/ai-agent-service/
  app/
    agents/
      intake_agent_v2.py          ← Agent chính (V2)
      intake_agent.py             ← Agent cũ (V1, giữ để compare)
      care_flow_graph.py          ← LangGraph state machine
      prompts/
        intake_prompt_v2.py       ← System prompt chính (QUAN TRỌNG NHẤT)
        complaint_protocols.py    ← Protocol theo loại triệu chứng
        soap_prompt.py            ← SOAP note generation
        clinical_summary_v2_prompt.py
      tools/
        emergency_detector.py     ← Phát hiện emergency keywords
        intake_tracker.py         ← Track progress của intake
        safety_classifier.py
    nlp/
      code_switcher.py            ← Phát hiện ngôn ngữ (Việt/Anh)
      cultural_mapper.py          ← Map từ ngữ dân gian → y khoa
```

### Nguyên tắc V2 (KHÔNG phá vỡ)
1. Trust the LLM — không override quá nhiều
2. Chỉ instant emergency check trước LLM (không dùng safety classifier rộng)
3. Single static prompt (không compose_intake_prompt())
4. Extract markers từ LLM output thay vì enforce cứng

### Khi sửa intake_prompt_v2.py
- Prompt được viết bằng tiếng Việt — giữ nguyên ngôn ngữ
- Cấu trúc BƯỚC A/B/C/D phải giữ nguyên
- Các HARD STOP không được xóa
- Sau khi sửa prompt, test với: `python -m pytest tests/unit/test_intake_agent_v2.py -v`

### Khi sửa emergency_detector.py
- Đây là instant keyword detector (trước LLM)
- Chỉ thêm keywords Tier 1 (life-threatening ngay lập tức)
- Tier 2 xử lý trong prompt (BƯỚC A)

### Chạy tests
```bash
cd services/ai-agent-service
source .venv/bin/activate
python -m pytest tests/unit/ -v
python -m pytest tests/unit/test_intake_agent_v2.py -v  # chỉ test intake
```

### Quy trình bắt buộc khi sửa code

**TRƯỚC KHI sửa bất kỳ file nào:**
```bash
cd /home/nathan-ubutu/2026/CVH-Agents/2026-Compass-Vitals-Agent
git add -A
git commit -m "chore: snapshot trước khi apply changes"
git push
```

**SAU KHI sửa xong và tests pass:**
```bash
git add -A
git commit -m "fix: <mô tả thay đổi>"
git push
```

Không bao giờ để code chưa commit khi bắt đầu làm việc.

### Commit convention
```
fix: <mô tả tiếng Việt>
feat: <mô tả tiếng Việt>
refactor: <mô tả tiếng Việt>
chore: <mô tả tiếng Việt>
```

Ví dụ: `fix: cải thiện phát hiện red flag đau ngực + khó thở trong intake_prompt_v2`
