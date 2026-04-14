# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Minh Hiếu
**Vai trò trong nhóm:** Supervisor Owner
**Ngày nộp:** 2026-04-14
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi sở hữu file [day09/lab/graph.py](../../graph.py) — lớp orchestration của toàn pipeline. Cụ thể, tôi implement: `AgentState` TypedDict ([graph.py:25](../../graph.py#L25)), `make_initial_state` ([graph.py:54](../../graph.py#L54)), `supervisor_node` với routing keyword-based ([graph.py:81](../../graph.py#L81)), `route_decision` conditional edge ([graph.py:162](../../graph.py#L162)), `human_review_node` ([graph.py:175](../../graph.py#L175)), `build_graph()` topology theo Option B (LangGraph StateGraph) ([graph.py:237](../../graph.py#L237)), cùng `run_graph()` và `save_trace()`.

Công việc của tôi là "ngã ba" của pipeline: tôi nhận task, quyết định route, rồi thread state sang các worker mà Mạnh (retrieval), Hoàng (policy_tool) và Long (synthesis) sở hữu. Tôi không viết logic domain — tôi chỉ điều phối và đảm bảo `AgentState` không bị overwrite giữa các node.

**Bằng chứng:** commit `a3eec67` (fix eval_trace), block `policy_keywords`/`retrieval_keywords` ở [graph.py:108-115](../../graph.py#L108-L115), và idempotent guard ở [graph.py:216](../../graph.py#L216).

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Routing supervisor dùng **keyword matching tường minh** (Python `in`) thay vì gọi LLM classifier.

**Lựa chọn thay thế đã cân nhắc:**
1. LLM classifier với 1 prompt zero-shot → mỗi request +600–900ms latency và tốn token.
2. Embedding similarity với 5 prototype categories → cần thêm cache + dependency, overkill cho 5 nhãn.
3. Keyword `in` cộng với regex cho mã lỗi `ERR-XXX` → tôi chọn cách này.

**Lý do:** Lab có đúng 3 đích route (retrieval / policy_tool / human_review) và tập keyword tiếng Việt rất hẹp ("hoàn tiền", "P1", "SLA"…). Keyword routing chạy ~2ms, deterministic, dễ debug khi `route_reason` bị sai — quan trọng cho việc trace lại từng câu trong `test_questions.json`.

**Trade-off đã chấp nhận:** Mất khả năng generalize sang câu hỏi mới không chứa keyword. Tôi bù lại bằng default fallback `retrieval_worker` ở [graph.py:101](../../graph.py#L101) và HITL override khi gặp `ERR-` không kèm context ([graph.py:145-147](../../graph.py#L145-L147)).

**Bằng chứng từ trace:** Trên 15 câu của `test_questions.json`, supervisor latency luôn < 5ms; `route_reason` luôn là câu cụ thể như `"policy keywords matched: ['hoàn tiền', 'flash sale']"` chứ không bao giờ là `"unknown"` — đáp ứng ràng buộc của `worker_contracts.yaml`.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Khi `policy_tool_worker` đã gọi `mcp_server.search_kb` và populate `retrieved_chunks`, supervisor route tiếp về `retrieval_worker` để lấy evidence — `retrieval_worker` chạy lại ChromaDB query và **ghi đè** `retrieved_chunks` bằng kết quả khác, làm citation của synthesis lệch khỏi policy đã check.

**Symptom:** Câu Q07 ("flash sale có hoàn tiền không?") trong trace cũ có `policy_result.exception="flash_sale"` nhưng `retrieved_sources` lại trỏ về tài liệu SLA, vì retrieval chạy đè sau policy_tool. Synthesis cite `[1]` không khớp với rule mà policy đã trả.

**Root cause:** Topology `policy_tool_worker → retrieval_worker → synthesis_worker` trong `build_graph()` không phân biệt "đã có evidence" vs "chưa có evidence". `retrieval_run(state)` không check trạng thái cũ.

**Cách sửa:** Tôi thêm idempotent guard trong `retrieval_worker_node` ở [graph.py:216-218](../../graph.py#L216-L218):

```python
if state.get("retrieved_chunks"):
    state["history"].append("[retrieval_worker] skipped (chunks already present)")
    return state
```

**Trước/sau:** Trace Q07 sau fix có thêm dòng `[retrieval_worker] skipped (chunks already present)` trong `history`, và `retrieved_sources` giữ nguyên nguồn `policies/refund_flash_sale.md` mà policy_tool đã lấy. Citation của synthesis khớp 1-1 với policy result.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở:** giữ contract của supervisor sạch — `route_reason` luôn là câu hoàn chỉnh, `workers_called` được append chứ không overwrite, và topology graph có comment ASCII rõ ràng ở [graph.py:250-255](../../graph.py#L250-L255) để cả nhóm đọc được mà không cần mở LangGraph docs.

**Tôi còn yếu ở:** chưa viết unit test cho `supervisor_node` — hiện tôi mới test gián tiếp qua `python graph.py` smoke-test. Routing dựa keyword nên một câu kiểu "tôi cần refund cho ticket P1" sẽ rơi vào `policy_tool_worker` (vì `matched_policy` được check trước `matched_retrieval`) và có thể không phải intent thật.

**Nhóm phụ thuộc vào tôi ở:** mọi worker không chạy được nếu `AgentState` thiếu key — Long và Trang block khi tôi đổi schema.

**Tôi phụ thuộc vào:** Minh (synthesis) phải tôn trọng `retrieved_chunks=[]` để abstain, nếu không HITL của tôi vô nghĩa.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm **disambiguation rule khi cả `matched_policy` và `matched_retrieval` cùng match** — hiện tại policy luôn thắng vì check trước. Lý do: trace câu test "ticket P1 có được hoàn tiền nếu là flash sale không?" có `route=policy_tool_worker` nhưng evidence cần cả SLA P1 (retrieval) và rule flash_sale (policy). Tôi sẽ cho supervisor set cả `needs_tool=True` lẫn pre-fetch retrieval, để synthesis có đủ 2 nguồn cite thay vì chỉ 1.

---

*Lưu file này với tên: `reports/individual/nguyen_minh_hieu.md`*
