# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Lâm Tùng  
**Vai trò trong nhóm:** MCP handoff / Tool integration support  
**Ngày nộp:** 14/04/2026  

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong phần Day 09, tôi phụ trách hoàn thiện `mcp_server.py` để module MCP có thể bàn giao cho sprint tiếp theo mà không phụ thuộc quá nhiều vào môi trường local. Công việc chính của tôi là làm cho MCP server đủ ổn định để `workers/policy_tool.py` gọi qua `dispatch_tool()` và ghi trace vào `mcp_tools_used`. Tôi tập trung vào `search_kb`, `get_ticket_info`, `check_access_permission`, `create_ticket`, đặc biệt là `search_kb(query, top_k)` vì đây là tool policy worker dùng để lấy evidence.

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`
- Functions tôi implement/củng cố: `tool_search_kb()`, `_lexical_search_docs()`, `_coerce_top_k()`, `_format_kb_result()`, `dispatch_tool()`

**Cách công việc của tôi kết nối với phần của thành viên khác:**  
`policy_tool.py` gọi MCP qua `_call_mcp_tool()`, nên nếu `mcp_server.py` trả lỗi hoặc output sai shape thì Sprint 3 và Sprint 4 sẽ thiếu trace `mcp_tools_used`.

**Bằng chứng:** commit `3fbed50 Complete mock MCP server handoff`, chỉ sửa `day09/lab/mcp_server.py`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chọn thêm lexical fallback trên `data/docs` cho `search_kb` thay vì chỉ phụ thuộc vào ChromaDB.

Lúc kiểm tra MCP server, tôi thấy `search_kb` đang ưu tiên reuse `workers.retrieval.retrieve_dense()`. Cách này đúng về mặt kiến trúc, nhưng trong môi trường lab có thể thiếu `chromadb`, thiếu index, hoặc embedding chưa setup. Nếu giữ nguyên, MCP tool vẫn tồn tại nhưng không chắc trả evidence thật.

Tôi chọn giữ ChromaDB là đường chính, nhưng nếu `chromadb` chưa cài hoặc retrieval không trả chunks thì fallback sang lexical search đọc trực tiếp file `.txt` trong `data/docs`. Phương án thay thế là hard-code mock chunk hoặc yêu cầu team build index trước khi test. Tôi không chọn hard-code vì dễ tạo câu trả lời giả; cũng không chọn bắt buộc ChromaDB vì mục tiêu bàn giao là tool phải chạy được ngay.

**Trade-off đã chấp nhận:**  
Lexical fallback không tốt bằng semantic search, nhưng nó trả evidence thật từ tài liệu nội bộ và có metadata `retrieval: lexical_fallback`, nên trace vẫn trung thực.

**Bằng chứng từ trace/code:**
```python
if find_spec("chromadb") is None:
    chroma_error = "ChromaDB is not installed."

chunks = _lexical_search_docs(query, top_k=top_k)
result["fallback_used"] = "lexical_docs"
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** MCP `search_kb` không ổn định khi môi trường chưa có ChromaDB hoặc index chưa sẵn sàng.

**Symptom:**  
Khi chạy `python mcp_server.py`, tool discovery chạy được nhưng `search_kb` có nguy cơ trả rỗng nếu ChromaDB lỗi. Điều này nguy hiểm cho Sprint 4 vì trace có thể ghi MCP call nhưng `output.chunks` không có evidence hữu ích. Với câu “Flash Sale refund policy”, policy worker cần chunk từ `policy_refund_v4.txt` để detect exception.

**Root cause:**  
`tool_search_kb()` phụ thuộc vào retrieval worker, còn retrieval worker phụ thuộc vào ChromaDB và embedding setup. MCP server vì vậy chưa thật sự độc lập để bàn giao.

**Cách sửa:**  
Tôi thêm `_lexical_search_docs()` để đọc `data/docs`, tính điểm đơn giản theo query term và keyword boost như `p1`, `sla`, `refund`, `hoàn tiền`, `flash sale`, `access`, `level`. Tôi cũng thêm `_coerce_top_k()`, `_format_kb_result()`, và validation trong `dispatch_tool()` cho required fields.

**Bằng chứng trước/sau:**  
Trước sửa: nếu thiếu ChromaDB, `search_kb` không đảm bảo evidence thật.  
Sau sửa: `python mcp_server.py` trả chunks từ `sla_p1_2026.txt` và `access_control_sop.txt`; test policy worker trả `mcp_tools_used=["search_kb"]`, `chunks=3`, `policy_applies=false`, detect `flash_sale_exception`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**  
Tôi làm tốt phần biến MCP server từ “có tool” thành module có thể bàn giao và test độc lập. Tôi cũng kiểm tra đường gọi thật từ `policy_tool.py` sang `mcp_server.py` để đảm bảo trace Sprint 3 có `mcp_tools_used`.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**  
Tôi chưa làm real MCP server bằng HTTP hoặc thư viện `mcp`, nên phần này chưa lấy được bonus +2. Fallback lexical cũng chỉ là giải pháp thực dụng, chưa thay thế được vector search thật.

**Nhóm phụ thuộc vào tôi ở đâu?**  
Nếu `mcp_server.py` không ổn định thì policy worker có thể route đúng nhưng không có evidence.

**Phần tôi phụ thuộc vào thành viên khác:**  
Tôi phụ thuộc vào Supervisor/Graph Owner để set `needs_tool=True` và phụ thuộc vào Trace Owner để đưa `mcp_tools_used` vào log cuối.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm test script nhỏ cho MCP contract, ví dụ gọi `dispatch_tool("search_kb", ...)`, `dispatch_tool("get_ticket_info", ...)`, và case thiếu required input. Lý do là trace hiện tại chứng minh MCP call chạy được, nhưng chưa có test tự động để ngăn lỗi schema/output khi người khác chỉnh tiếp.
