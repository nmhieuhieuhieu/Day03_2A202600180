# Group Report: Lab 3 - TravelWise ReAct Agent

- **Team Name**: C401 - C5
- **Team Members**: Đỗ Minh Phúc, Nguyễn Minh Hiếu, Hồ Sỹ Minh Hà, Nguyễn Khánh Nam, Lê Tú Nam, Lê Hữu Hưng
- **Deployment Date**: 2026-04-06

---

## 1. Executive Summary

TravelWise là một travel assistant agent được xây dựng theo kiến trúc ReAct (Reason + Act), sử dụng các công cụ thực tế (Brave Search, DuckDuckGo, Wikipedia, Calculator, System Time) để lên kế hoạch du lịch cho người dùng.

Trong quá trình phát triển Agent v1, nhóm phát hiện và phân tích **4 lỗi** nghiêm trọng thông qua telemetry logs, sau đó xây dựng Agent v2 với các bản vá tương ứng. Nhóm đã thực hiện **live demo thành công** với giảng viên vào ngày 06/04/2026.

- **Tổng sessions thử nghiệm**: 21
- **Sessions hoàn thành đúng (có bước thực)**: 13/18 (72%)
- **Sessions bị hallucinate loop**: 5 sessions (steps = 0)
- **Timeout (vượt max_steps=7)**: 1 session
- **Kết quả chính**: Agent v2 loại bỏ hoàn toàn hallucinated loop, tìm kiếm đúng năm thực tế (2026), và trả về kết quả tìm kiếm có nội dung thay vì "No results found."

---

## 2. System Architecture & Tooling

### 2.0 Chatbot Baseline

Trước khi xây dựng ReAct Agent, nhóm implement một **Chatbot Baseline** đơn giản làm điểm so sánh:

- **Kiến trúc**: Single-turn LLM call — user input → system prompt cố định → LLM response, không có tool, không có vòng lặp.
- **Giới hạn**: Toàn bộ câu trả lời dựa trên parametric knowledge (dữ liệu trong model). Không thể truy cập real-time data (thời tiết, giá vé, khách sạn), dễ hallucinate số liệu cụ thể.
- **Ưu điểm**: Latency thấp (~1,200ms), token ít (~350 tokens/query), chi phí thấp (~$0.0035/query).

### 2.1 ReAct Loop Implementation

Agent hoạt động theo vòng lặp **Thought → Action → Observation** lặp lại cho đến khi có Final Answer:

```
User Input
    │
    ▼
┌─────────────────────────────────────┐
│  [Thought] LLM phân tích ngữ cảnh  │
│  [Action]  tool_name[argument]      │  ◄─── stop=["\nObservation:"] cắt tại đây
│  [Observation] Kết quả tool thực   │       để LLM không tự bịa Observation
└─────────────────────────────────────┘
    │
    ▼ (lặp tối đa 7 lần)
Final Answer (Markdown, tiếng Việt)
```

**Cơ chế chống hallucination:** LLM được gọi với `stop=["\nObservation:"]` — buộc LLM dừng trước khi tự viết nội dung Observation, đảm bảo agent phải gọi tool thật.

### 2.2 Tool Definitions & Evolution

#### Tool Inventory (Agent v2)

| Tool Name          | Input Format                                         | Use Case                                                                                    |
| :----------------- | :--------------------------------------------------- | :------------------------------------------------------------------------------------------ |
| `web_search`       | `string` — plain text query (không có quotes)        | Tìm thời tiết, giá vé, khách sạn, địa điểm ăn uống theo thời gian thực (Brave → DuckDuckGo) |
| `calculator`       | `string` — biểu thức toán học (`150000 * 2 + 50000`) | Tính tổng chi phí, ước tính ngân sách                                                       |
| `get_system_time`  | không có input                                       | Lấy ngày/giờ hiện tại khi người dùng hỏi rõ về thời gian                                    |
| `wikipedia_search` | `string` — tên địa điểm, sự kiện, khái niệm          | Tra cứu thông tin nền về địa danh, lịch sử, văn hóa                                         |

#### Tool Design Evolution (v1 → v2)

| Tool               | Agent v1                                      | Agent v2                                                     | Lý do thay đổi                                         |
| :----------------- | :-------------------------------------------- | :----------------------------------------------------------- | :----------------------------------------------------- |
| `web_search`       | Chỉ dùng Brave Search, không sanitize query   | Brave + DuckDuckGo fallback; strip quotes trước khi gửi API  | Bug #3: quoted query → "No results found."             |
| `calculator`       | Có nhưng agent tự tính thay vì gọi tool       | Giữ nguyên + thêm rule bắt buộc dùng calculator trong prompt | Bug #4: agent bypass calculator                        |
| `get_system_time`  | Được gọi để lấy ngày, nhưng agent vẫn sai năm | Giữ nguyên + inject `datetime.now()` vào system prompt       | Bug #2: agent dùng năm 2023 thay vì 2026               |
| `wikipedia_search` | Không có                                      | Thêm mới — tra cứu thông tin tĩnh về địa danh                | Mở rộng khả năng cung cấp thông tin nền cho người dùng |

### 2.3 LLM Providers Used

- **Primary**: GPT-4o (OpenAI)
- **Secondary (Backup)**: Gemini (GeminiProvider — đã implement)

---

## 3. Telemetry & Performance Dashboard

_Dữ liệu được thu thập tự động từ `logs/2026-04-06.log` qua module `src/telemetry/`._

| Metric                                         | Giá trị       |
| :--------------------------------------------- | :------------ |
| **Avg Latency per LLM call**                   | 2,849 ms      |
| **Max Latency**                                | 13,596 ms     |
| **Min Latency**                                | 773 ms        |
| **Avg Tokens per LLM call**                    | 623 tokens    |
| **Total Tokens (toàn bộ session)**             | 42,427 tokens |
| **Total Cost Estimate**                        | $0.42         |
| **Avg Steps per session (sau khi fix Bug #1)** | 2.5 steps     |
| **Max Steps observed**                         | 7 (timeout)   |

**Tool usage breakdown:**

| Tool              | Số lần gọi |
| :---------------- | :--------- |
| `web_search`      | 17         |
| `get_system_time` | 6          |
| `calculator`      | 1          |

---

## 4. Root Cause Analysis (RCA) — Traces

### Successful Trace Example

**Input**: `"Thời tiết Đà Nẵng cuối tuần này thế nào? Tôi cần biết để chuẩn bị đồ đi biển."`

```
STEP 1 (1,243ms)
  Thought: Tôi cần biết ngày hiện tại để xác định "cuối tuần này", sau đó tìm dự báo thời tiết.
  >> Calling tool: get_system_time
  << Tool result: Sunday, April 06, 2026

STEP 2 (3,102ms)
  Thought: Hôm nay là Chủ nhật 06/04/2026. Cuối tuần tới là 11-12/04/2026. Tìm dự báo thời tiết.
  >> Calling tool: web_search
     Args: thời tiết Đà Nẵng ngày 11 12 tháng 4 2026
  << Tool result:
     - Dự báo thời tiết Đà Nẵng tuần tới: Nhiệt độ 28-32°C, ít mây, không mưa
     - Biển Đà Nẵng tháng 4: sóng nhỏ, thích hợp tắm biển và các hoạt động ngoài trời

  >> Final Answer found

AGENT_END | steps: 2 | has_answer: true
```

**Kết quả**: Agent trả lời đúng với dữ liệu thực tế, dùng đúng 2 tools theo thứ tự logic, không timeout.

### Failure Traces

### Bug #1 — Hallucinated Loop (steps = 0)

- **Input**: `"Thời tiết Đà Nẵng cuối tuần này thế nào?"`
- **Triệu chứng**: `AGENT_END steps: 0` — agent hoàn thành mà không gọi bất kỳ tool nào.
- **Root Cause**: LLM được huấn luyện trên nhiều ReAct traces, nên khi thấy format `Action: ... \nObservation:`, nó tự động hoàn thành cả phần `Observation` từ parametric memory (dữ liệu trong model) mà không gọi tool thật. Toàn bộ vòng lặp Thought→Action→Observation→Final Answer diễn ra trong một lần generate duy nhất.
- **Fix**: Truyền `stop=["\nObservation:"]` vào `llm.generate()` — LLM bị cắt ngay trước khi viết Observation, buộc agent gọi tool thật.

```
[TRƯỚC FIX] AGENT_END | steps: 0  ← không gọi tool nào
[SAU FIX]   AGENT_END | steps: 2  ← gọi get_system_time + web_search
```

### Bug #2 — Sai Năm (LLM dùng năm 2023)

- **Input**: `"Tôi muốn đi Lạng Sơn"`
- **Triệu chứng**: `TOOL_CALL web_search["Lạng Sơn weather October 2023"]` — sai năm gần 3 năm.
- **Root Cause**: LLM không biết ngày hiện tại, tự đoán dựa trên dữ liệu training (cutoff ~2023). Kết quả search không tìm được vì sai thời điểm.
- **Fix**: Inject `datetime.now()` vào `get_system_prompt()` — agent biết ngày thực tế ngay từ đầu mà không cần gọi tool.

```python
current_date = datetime.now().strftime("%A, %d/%m/%Y")
# → "Sunday, 06/04/2026" được inject vào system prompt
```

### Bug #3 — Quoted Query → "No results found"

- **Input**: `"Sài Gòn đi Đà Lạt, budget 3 triệu cho 2 người"`
- **Triệu chứng**: `TOOL_RESULT: "No results found."` — xuất hiện 6 lần trong log.
- **Root Cause**: LLM sinh query dạng `web_search["giá vé xe Sài Gòn Đà Lạt"]` với dấu ngoặc kép. Brave Search API interpret `"..."` là **phrase search** (tìm cụm từ chính xác) → không khớp → trả về rỗng.
- **Fix**: (1) Thêm rule vào system prompt cấm dùng quotes; (2) sanitize query trong code `.replace('"', '')` trước khi gửi API; (3) thêm DuckDuckGo fallback khi Brave trả về rỗng.

### Bug #4 — Tự Tính Thay Vì Dùng Calculator

- **Triệu chứng**: Agent tự tính tổng chi phí trong Final Answer thay vì gọi `calculator[...]`.
- **Root Cause**: System prompt không có rule rõ ràng bắt buộc dùng calculator tool.
- **Fix**: Thêm rule: _"Whenever you are presented with a calculation, never do it yourself. Use the calculator tool."_

---

## 5. Ablation Studies & Experiments

### Experiment 1: Agent v1 (không có stop sequence) vs Agent v2 (có stop sequence)

| Metric                               | Agent v1                       | Agent v2                     |
| :----------------------------------- | :----------------------------- | :--------------------------- |
| Sessions với steps = 0 (hallucinate) | 5/18 (28%)                     | 0%                           |
| Tool calls thực tế                   | ~0 trong các session lỗi       | Luôn gọi tool                |
| Kết quả trả về                       | Thông tin bịa từ training data | Dữ liệu thực từ Brave Search |

### Experiment 2: Chatbot Baseline vs ReAct Agent v2

#### 2a. So sánh chất lượng câu trả lời

| Loại câu hỏi                       | Chatbot Baseline                         | ReAct Agent v2                | Winner                     |
| :--------------------------------- | :--------------------------------------- | :---------------------------- | :------------------------- |
| Thời tiết hiện tại                 | ❌ Hallucinate (không có real-time data) | ✅ Search thực tế             | **Agent**                  |
| Tính tổng chi phí                  | ⚠️ Tự tính, có thể sai                   | ✅ Dùng calculator chính xác  | **Agent**                  |
| Câu hỏi đơn giản (lịch sử, địa lý) | ✅ Nhanh, chính xác                      | ✅ Chính xác nhưng chậm hơn   | **Chatbot** (hiệu quả hơn) |
| Lên lịch trình đa bước             | ❌ Không có context thực tế              | ✅ Kết hợp search + tính toán | **Agent**                  |

#### 2b. So sánh hiệu năng & chi phí

| Metric                        | Chatbot Baseline   | ReAct Agent v2  | Ghi chú                                        |
| :---------------------------- | :----------------- | :-------------- | :--------------------------------------------- | --- |
| **Latency (avg)**             | ~1,200 ms          | ~7,100 ms       | Agent = 2.5 steps × 2,849 ms/call              |
| **Tokens per query (avg)**    | ~350 tokens        | ~1,558 tokens   | Agent = 2.5 steps × 623 tokens/call            |
| **Cost per query (estimate)** | ~$0.0035           | ~$0.020         | Agent tốn ~5.7× hơn do multi-step              |     |
| **Accuracy (real-time data)** | Thấp (hallucinate) | Cao (dùng tool) | Agent vượt trội với câu hỏi cần real-time data |
| **Max steps**                 | 1 (single call)    | 2–7 steps       | Agent timeout nếu vượt max_steps=7             |

**Kết luận:** ReAct Agent vượt trội với câu hỏi cần real-time data hoặc multi-step reasoning, nhưng tốn gấp ~5.7× chi phí và ~6× thời gian so với chatbot baseline. Với câu hỏi đơn giản, chatbot baseline hiệu quả hơn — kiến trúc hybrid (chatbot cho simple query, agent cho complex query) sẽ tối ưu hơn trong production.

---

## 6. Code Quality

### Cấu trúc Module

```text
src/
├── core/
│   ├── llm_provider.py      # Abstract base class LLMProvider
│   ├── openai_provider.py   # OpenAI implementation
│   └── gemini_provider.py   # Gemini implementation (backup)
├── agent/
│   └── agent.py             # ReActAgent — tách biệt khỏi tool logic
├── tools/
│   └── tools.py             # Tool definitions + execute_tool dispatcher
└── telemetry/
    ├── logger.py            # Structured JSON logger
    └── metrics.py           # PerformanceTracker (latency, tokens, cost)
```

### Các quyết định thiết kế

- **Abstract class `LLMProvider`**: Định nghĩa interface `generate(prompt, system_prompt, stop)` — swap giữa OpenAI và Gemini không cần sửa agent code, chỉ thay provider khi khởi tạo.
- **Tách `execute_tool` khỏi agent**: `ReActAgent` nhận `tool_executor` qua dependency injection (`agent.tool_executor = execute_tool`) — agent có thể test độc lập mà không cần tools thật.
- **Telemetry tách biệt**: `logger` và `tracker` là global singletons trong `src/telemetry/` — agent gọi `logger.log_event()` mà không cần biết log đi đâu (file/console).
- **Tool registry dạng list**: `TOOLS` trong `tools.py` là list of dicts — thêm tool mới chỉ cần append vào list, không cần sửa agent.

---

## 7. Production Readiness Review

| Tiêu chí                | Trạng thái | Ghi chú                                                                  |
| :---------------------- | :--------- | :----------------------------------------------------------------------- |
| **Guardrails**          | ✅         | `max_steps=7` ngăn vòng lặp vô hạn                                       |
| **Input Sanitization**  | ✅         | Strip quotes khỏi tool args trước khi gửi API                            |
| **Error Handling**      | ✅         | Parse error → nudge LLM tiếp tục; timeout → trả lời mặc định             |
| **Structured Logging**  | ✅         | JSON logs với timestamp, event type, data                                |
| **Performance Metrics** | ✅         | Latency, token count, cost estimate per request                          |
| **Search Fallback**     | ✅         | Brave Search thất bại → tự động fallback sang DuckDuckGo                 |
| **Secret Management**   | ⚠️         | API keys trong `.env` — cần revoke key bị expose lên git                 |
| **Scalability**         | ⚠️         | Single-thread, chưa có async — cần refactor với LangGraph cho multi-user |
| **Retry Logic**         | ⚠️         | Khi search fail, agent tự thử query khác — chưa có exponential backoff   |

---

## 7. Group Learning Points

- **Cần xử lý haluciation ở LLM**: Không có `stop=["\nObservation:"]`, LLM tự hoàn thành toàn bộ trace từ parametric memory — agent hoạt động nhưng không gọi tool thật. Đây là lỗi tinh vi nhất vì output trông hợp lệ nhưng dữ liệu hoàn toàn bịa.
- **Prompt engineering có trade-off**: Mỗi rule thêm vào system prompt làm token tăng, latency tăng. Cần cân bằng giữa độ chính xác và chi phí vận hành.
- **Agent không phải lúc nào cũng tốt hơn chatbot**: Với câu hỏi đơn giản, agent tốn gấp 5.7× chi phí mà không cải thiện đáng kể chất lượng — kiến trúc hybrid sẽ tối ưu hơn trong production.
