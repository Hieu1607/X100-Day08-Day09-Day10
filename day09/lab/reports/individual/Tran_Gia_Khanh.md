# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Gia Khánh  
**Vai trò trong nhóm:** MCP Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong Day 09, tôi phụ trách vai trò MCP Owner nên tập trung vào việc nối external capability cho pipeline multi-agent. Phần tôi trực tiếp làm nằm ở `mcp_server.py` và phần tích hợp trong `workers/policy_tool.py`. Cụ thể, tôi triển khai các tool theo chuẩn mock MCP gồm `search_kb(query, top_k)` để tìm context và `get_ticket_info(ticket_id)` để tra ticket, đồng thời bổ sung thêm 2 tool mở rộng là `check_access_permission` và `create_ticket` để team có thể dùng khi mở rộng scenario.  

Tôi cũng chuẩn hóa output của call MCP thành object có `tool`, `input`, `output`, `error`, `timestamp` để trace dễ đọc và debug theo từng bước. Công việc của tôi kết nối trực tiếp với phần Supervisor/Graph của bạn khác trong nhóm: nếu route vào policy worker mà không bật `needs_tool` hoặc graph vẫn dùng placeholder thì MCP sẽ không được gọi thật.  

**Module/file tôi chịu trách nhiệm:**
- File chính: `mcp_server.py`, `workers/policy_tool.py`
- Functions tôi implement: `list_tools()`, `dispatch_tool()`, `_call_mcp_tool()`, `run()` (policy path có MCP)

**Bằng chứng:**
- Trace run policy có field `mcp_tools_used` với tool `search_kb`
- Log worker có dòng `[policy_tool_worker] called MCP search_kb`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Dùng mock MCP in-process qua `dispatch_tool()` thay vì dựng MCP server HTTP thật ngay từ đầu.

Lúc làm Sprint 3 tôi cân nhắc hai hướng: (1) làm server thật bằng HTTP hoặc `mcp` library để client gọi qua network, hoặc (2) mock chuẩn interface MCP nhưng chạy cùng process. Tôi chọn hướng (2) vì mục tiêu lab là chứng minh được orchestration + trace tool call trước, không bị chậm bởi vấn đề hạ tầng (port, auth, retry, timeout).  

Điểm quan trọng là tôi không gọi tool “tự do” mà vẫn giữ contract rõ ràng: tool registry, schema và dispatch layer tách riêng. Nhờ vậy, khi cần nâng cấp sang server thật thì phần worker gần như giữ nguyên, chỉ thay implementation của client call. Với nhóm làm lab theo sprint ngắn, đây là cách giảm rủi ro và đạt Definition of Done nhanh hơn.

**Trade-off đã chấp nhận:**  
Mock in-process không phản ánh latency/network failure thực tế như một MCP server thật. Ngoài ra, vì chạy local nên độ “external” của capability chưa đầy đủ theo nghĩa production.

**Bằng chứng từ trace/code:**
```python
from mcp_server import dispatch_tool
result = dispatch_tool(tool_name, tool_input)
state["mcp_tools_used"].append({
    "tool": tool_name,
    "input": tool_input,
    "output": result,
    "timestamp": datetime.now().isoformat(),
})
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Pipeline route đúng vào policy worker nhưng trace không ghi nhận MCP call (`mcp_tools_used` rỗng).

**Symptom:**  
Khi chạy câu policy kiểu “flash sale refund”, output hiển thị `route=policy_tool_worker` nhưng `mcp_tools_used=[]`. Điều này làm Sprint 3 fail ở tiêu chí “Trace ghi được mcp tool call”.

**Root cause:**  
Lỗi không nằm trong `mcp_server.py` hay `workers/policy_tool.py`. Gốc lỗi nằm ở `graph.py`: các worker node vẫn là placeholder, đặc biệt `policy_tool_worker_node` không gọi `workers/policy_tool.py::run()` thật mà chỉ set state giả. Vì vậy MCP integration đã viết nhưng không được thực thi end-to-end.

**Cách sửa:**  
Tôi thay wrapper placeholder trong `graph.py` để gọi worker thật:
- `retrieval_worker_node -> retrieval_run(state)`
- `policy_tool_worker_node -> policy_tool_run(state)`
- `synthesis_worker_node -> synthesis_run(state)`

**Bằng chứng trước/sau:**  
- Trước sửa: test policy trả `mcp_tools_used_len=0`  
- Sau sửa: cùng query trả `mcp_calls=1`, trace có object tool `search_kb` và history có dòng `[policy_tool_worker] called MCP search_kb`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**  
Tôi làm tốt phần nối MCP theo hướng có thể test được ngay: tool có schema rõ, call format rõ, trace rõ. Nhờ đó nhóm debug nhanh, biết chính xác worker có gọi MCP hay chưa.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**  
Tôi chưa nâng cấp lên MCP server thật (HTTP hoặc library `mcp`) để lấy bonus. Tôi ưu tiên hoàn thành luồng core trước nên chấp nhận giải pháp mock.

**Nhóm phụ thuộc vào tôi ở đâu?**  
Nếu chưa có MCP layer thì policy worker không thể hiện external capability, và Sprint 3 sẽ không đạt criteria trace.

**Phần tôi phụ thuộc vào thành viên khác:**  
Tôi phụ thuộc vào phần `graph.py` của Supervisor Owner để đảm bảo graph thực sự gọi worker thật, không dùng placeholder, thì MCP mới chạy end-to-end.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ nâng mock MCP thành server thật (FastAPI hoặc `mcp` library) và thêm timeout + retry cho client call, vì trace hiện tại cho thấy có trường hợp fallback mock do thiếu API key khi tìm KB. Cải tiến này giúp tách hẳn orchestration khỏi implementation chi tiết của tool và kiểm thử được failure mode thực tế (network timeout, tool unavailable), từ đó báo cáo Sprint 4 có số liệu latency/mcp error rate thuyết phục hơn.
