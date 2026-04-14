# System Architecture — Lab Day 09

**Nhóm:** X100 Day09 Team  
**Ngày:** 14/04/2026  
**Version:** 1.0

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker  
**Lý do chọn pattern này (thay vì single agent):**

Nhóm tách hệ thống thành supervisor và các worker chuyên trách để giảm coupling, tăng khả năng debug và mở rộng. Supervisor chỉ làm nhiệm vụ phân luồng dựa trên tín hiệu trong câu hỏi (policy, retrieval, risk), còn worker chỉ xử lý domain riêng. Cách làm này giúp mỗi thành phần có contract rõ ràng, có thể test độc lập và đo được chất lượng theo trace.

Kiến trúc thực tế gồm 5 node chính: supervisor, retrieval_worker, policy_tool_worker, human_review và synthesis_worker. Ngoài ra có lớp MCP server để expose tool gọi ngoài như tìm kiếm KB và tra cứu ticket.

---

## 2. Sơ đồ Pipeline

**Sơ đồ thực tế của nhóm:**

```
User Question
  |
  v
Supervisor (rule-based routing)
  |
  +--> retrieval_worker -------------------+
  |                                        |
  +--> policy_tool_worker (MCP calls) -----+--> synthesis_worker --> Output
  |                                        |
  +--> human_review --> retrieval_worker ---+

Trace fields: supervisor_route, route_reason, workers_called, mcp_tools_used, latency_ms
```

Luồng thực thi trong graph hiện tại:
1. Supervisor quyết định worker đầu tiên.
2. Nếu route sang policy, worker có thể gọi MCP tools để lấy thêm context.
3. Retrieval cung cấp evidence chunks.
4. Synthesis tổng hợp câu trả lời dựa trên context và policy result.

---

## 3. Vai trò từng thành phần

### Supervisor (graph.py)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích task, chọn route và gắn cờ risk/needs_tool |
| **Input** | task (str) |
| **Output** | supervisor_route, route_reason, risk_high, needs_tool |
| **Routing logic** | Rule-based keyword matching: policy keywords, retrieval keywords, risk keywords; có nhánh human_review cho lỗi mơ hồ ERR-* |
| **HITL condition** | unknown error + risk cao hoặc thiếu context |

### Retrieval Worker (workers/retrieval.py)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Semantic retrieval từ ChromaDB và trả chunks + sources |
| **Embedding model** | text-embedding-3-small (qua OpenAI-compatible endpoint) |
| **Top-k** | Mặc định 3 (có thể override qua state) |
| **Stateless?** | Yes |

### Policy Tool Worker (workers/policy_tool.py)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích policy theo rule + LLM, quản lý exception, gọi MCP khi cần |
| **MCP tools gọi** | search_kb, get_ticket_info |
| **Exception cases xử lý** | flash_sale_exception, digital_product_exception, activated_exception |

### Synthesis Worker (workers/synthesis.py)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | gpt-4o-mini (fallback Gemini nếu lỗi) |
| **Temperature** | 0.1 |
| **Grounding strategy** | Dựng context từ retrieved_chunks + policy_result, ưu tiên trả lời có nguồn |
| **Abstain condition** | Khi thiếu context thì trả về "Không đủ thông tin trong tài liệu nội bộ" |

### MCP Server (mcp_server.py)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources, total_found |
| get_ticket_info | ticket_id | ticket details (priority, status, deadline, notifications) |
| check_access_permission | access_level, requester_role, is_emergency | can_grant, required_approvers, emergency_override |
| create_ticket | priority, title, description | ticket_id, url, created_at |

---

## 4. Shared State Schema

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| task | str | Câu hỏi đầu vào | supervisor đọc |
| route_reason | str | Lý do route | supervisor ghi |
| risk_high | bool | Cờ rủi ro cao | supervisor ghi, human_review đọc |
| needs_tool | bool | Có cần gọi tool không | supervisor ghi, policy_tool đọc |
| hitl_triggered | bool | Có trigger human review không | human_review ghi |
| retrieved_chunks | list | Evidence retrieval | retrieval/policy_tool ghi, synthesis đọc |
| retrieved_sources | list | Danh sách nguồn | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả policy | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Lịch sử tool calls | policy_tool ghi, trace đọc |
| final_answer | str | Câu trả lời cuối | synthesis ghi |
| sources | list | Sources cho câu trả lời | synthesis ghi |
| confidence | float | Mức tin cậy | synthesis ghi |
| history | list | Log từng bước | mọi node ghi |
| workers_called | list | Chuỗi worker đã gọi | mọi worker ghi |
| supervisor_route | str | Route được chọn | supervisor ghi |
| latency_ms | int/null | Thời gian xử lý | wrapper graph ghi |
| run_id | str | Định danh run | init state ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó, vì logic dồn trong pipeline lớn | Dễ hơn, vì trace chỉ ra node lỗi cụ thể |
| Thêm capability mới | Phải sửa prompt/pipeline chung | Thêm worker hoặc MCP tool độc lập |
| Routing visibility | Không có | Có supervisor_route + route_reason |
| Khả năng đo lường | Chủ yếu nhìn output cuối | Đo được route, tool call, latency theo node |

**Quan sát thực tế của nhóm:**

Trong 15 trace gần nhất, hệ thống có phân bố route rõ ràng giữa retrieval (53%) và policy (47%), có ghi đầy đủ route_reason cho 100% run. Điều này giúp nhóm truy ngược nguyên nhân nhanh hơn khi câu trả lời bị abstain hoặc lệch nguồn.

---

## 6. Giới hạn và điểm cần cải tiến

1. Chất lượng retrieval chưa ổn định, nhiều câu vẫn abstain dù tài liệu có thông tin.
2. Policy worker đôi lúc lấy nguồn chưa sát domain câu hỏi (nhiễu từ tài liệu HR/FAQ).
3. Latency tăng đáng kể so với Day 08 vì nhiều bước và có thêm MCP/LLM call.
