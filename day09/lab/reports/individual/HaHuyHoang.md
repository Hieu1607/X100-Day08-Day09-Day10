# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Hà Huy Hoàng  
**Vai trò trong nhóm:** Worker Owner  
**Ngày nộp:** 14-04-2026  
**Độ dài yêu cầu:** 500–800 từ

---

> **Lưu ý quan trọng:**
> - Viết ở ngôi **"tôi"**, gắn với chi tiết thật của phần bạn làm
> - Phải có **bằng chứng cụ thể**: tên file, đoạn code, kết quả trace, hoặc commit
> - Nội dung phân tích phải khác hoàn toàn với các thành viên trong nhóm
> - Deadline: Được commit **sau 18:00** (xem SCORING.md)
> - Lưu file với tên: `reports/individual/[ten_ban].md` (VD: `nguyen_van_a.md`)

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

> Mô tả cụ thể module, worker, contract, hoặc phần trace bạn trực tiếp làm.
> Không chỉ nói "tôi làm Sprint X" — nói rõ file nào, function nào, quyết định nào.

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/policy_tool.py`, `workers/synthesis.py`
- Functions tôi implement: `analyze_policy`, `_call_mcp_tool`, `run` (policy worker), `_build_context`, `_estimate_confidence`, `synthesize`, `run` (synthesis worker)

**Cách công việc của tôi kết nối với phần của thành viên khác:**

Tôi nhận input từ `retrieval_worker` (retrieved_chunks) và `supervisor` (needs_tool).  
Sau đó:
- `policy_tool_worker` xử lý logic policy + gọi MCP tools nếu cần  
- Output (`policy_result`) được truyền sang `synthesis_worker`  
- `synthesis_worker` kết hợp chunks + policy_result để tạo final answer  

Phần của tôi nằm ở giữa pipeline: **bridge giữa retrieval → reasoning → final answer**.  

**Bằng chứng (commit hash, file có comment tên bạn, v.v.):**

- Code có cấu trúc rõ ràng worker pattern (`WORKER_NAME`, `run(state)`)
- Comment mô tả Sprint 2+3 và TODO MCP integration trong `policy_tool.py`
- Logic hybrid rule-based + LLM thể hiện rõ trong `analyze_policy`
- Code có commit update policy tools, synthesis 
---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

> Chọn **1 quyết định** bạn trực tiếp đề xuất hoặc implement trong phần mình phụ trách.
> Giải thích:
> - Quyết định là gì?
> - Các lựa chọn thay thế là gì?
> - Tại sao bạn chọn cách này?
> - Bằng chứng từ code/trace cho thấy quyết định này có effect gì?

**Quyết định:** Sử dụng **hybrid approach: rule-based + LLM fallback** trong `analyze_policy`

**Ví dụ:**
> "Tôi chọn dùng hybrid rule-based + LLM thay vì chỉ dùng LLM.
>  Lý do: rule-based xử lý nhanh và chính xác cho các exception cố định (flash sale, digital product),
>  trong khi LLM giúp xử lý các case phức tạp hơn.
>  Bằng chứng: code có decision_trace và confidence tăng từ 0.7 → 0.9 khi LLM chạy thành công."

**Ví dụ:**
> "Tôi chọn dùng keyword-based routing trong supervisor_node thay vì gọi LLM để classify.
>  Lý do: keyword routing nhanh hơn (~5ms vs ~800ms) và đủ chính xác cho 5 categories.
>  Bằng chứng: trace gq01 route_reason='task contains P1 SLA keyword', latency=45ms."

**Lý do:**

Tôi không dùng hoàn toàn LLM để phân tích policy, mà:
- Dùng **rule-based** cho các case rõ ràng (flash sale, digital product, activated)
- Dùng **LLM** để bổ sung reasoning khi cần

Các lựa chọn thay thế:
1. Full LLM → linh hoạt nhưng chậm và dễ hallucinate  
2. Full rule-based → nhanh nhưng không scale khi policy phức tạp  

Hybrid giúp cân bằng giữa **performance và flexibility**.

**Trade-off đã chấp nhận:**

- Tăng độ phức tạp code (2 luồng logic)
- Có thể inconsistency giữa rule và LLM output
- Phải maintain cả rule và prompt

**Bằng chứng từ trace/code:**

```python
# RULE-BASED
if "flash sale" in task_lower:
    exceptions_found.append({...})

# LLM FALLBACK
response = client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0.2,
    messages=[...]
)

confidence = 0.9

```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

> Mô tả 1 bug thực tế bạn gặp và sửa được trong lab hôm nay.
> Phải có: mô tả lỗi, symptom, root cause, cách sửa, và bằng chứng trước/sau.

**Lỗi:** Synthesis worker không xử lý đúng khi thiếu context, dẫn đến câu trả lời dễ bị sai lệch hoặc không rõ ràng.

**Symptom (pipeline làm gì sai?):**

- Khi `retrieved_chunks = []`, hệ thống vẫn gọi LLM để generate answer  
- Kết quả:
  - Trả lời chung chung hoặc không grounded vào tài liệu  
  - Vi phạm rule: “CHỈ trả lời dựa vào context”  
  - Confidence vẫn được tính dù không có evidence  

**Root cause (lỗi nằm ở đâu — indexing, routing, contract, worker logic?):**

- Lỗi nằm ở **synthesis_worker**
- Hàm `synthesize` luôn gọi `_call_llm()` mà không kiểm tra context có rỗng hay không  
- Vi phạm design principle của RAG: **no context → must abstain**

**Cách sửa:**

- Thêm logic kiểm tra trước khi gọi LLM:
  - Nếu không có chunks → trả về câu trả lời abstain ngay
- Đảm bảo tuân thủ SYSTEM_PROMPT

```python
if not chunks:
    return {
        "answer": "Không đủ thông tin trong tài liệu nội bộ.",
        "sources": [],
        "confidence": 0.1
    }
```

**Bằng chứng trước/sau:**
> Dán trace/log/output trước khi sửa và sau khi sửa.
- Trước khi sửa:
```python
chunks_count = 0
answer = (LLM generate nội dung không có nguồn)
confidence ≈ 0.3
```

- Sau khi sửa:
```python
chunks_count = 0
answer = "Không đủ thông tin trong tài liệu nội bộ."
confidence = 0.1
```
_________________

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Tôi làm tốt ở việc thiết kế logic rõ ràng và có tính hệ thống cho các worker, đặc biệt là đảm bảo luồng dữ liệu xuyên suốt giữa `policy_tool_worker` và `synthesis_worker`. Tôi chú trọng tính “grounded” (bám vào dữ liệu) bằng cách kết hợp rule-based, context từ retrieval và kiểm soát output của LLM qua prompt và structure.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Tôi chưa tối ưu tốt phần consistency giữa các thành phần (rule-based vs LLM), có thể dẫn đến kết quả không đồng nhất. Ngoài ra, việc xử lý edge cases (thiếu context, lỗi API) ban đầu chưa đầy đủ, phải sửa sau khi test.

**Nhóm phụ thuộc vào tôi ở đâu?** _(Phần nào của hệ thống bị block nếu tôi chưa xong?)_

Phần tổng hợp câu trả lời và logic policy là điểm trung tâm. Nếu tôi chưa hoàn thiện, pipeline sẽ không thể trả lời chính xác hoặc không thể kết luận.

**Phần tôi phụ thuộc vào thành viên khác:** _(Tôi cần gì từ ai để tiếp tục được?)_

Tôi phụ thuộc vào `retrieval_worker` để cung cấp context đúng và `supervisor` để routing chính xác. Nếu input sai, output của tôi cũng sẽ sai theo.
## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

> Nêu **đúng 1 cải tiến** với lý do có bằng chứng từ trace hoặc scorecard.
> Không phải "làm tốt hơn chung chung" — phải là:
> *"Tôi sẽ thử X vì trace của câu gq___ cho thấy Y."*

Tôi sẽ cải thiện **cơ chế đồng bộ giữa rule-based và LLM trong policy analysis**.

Hiện tại, rule-based quyết định `policy_applies` nhưng LLM lại trả về analysis riêng, có thể dẫn đến inconsistency.  
Trace cho thấy có case rule-based detect exception nhưng LLM vẫn giải thích theo hướng “có thể hoàn tiền”.

Tôi sẽ:
- Ép LLM phải **tuân theo kết quả rule-based**
- Hoặc merge output bằng một bước “decision resolver”

→ Giúp kết quả cuối cùng nhất quán và đáng tin cậy hơn.
_________________

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*  
*Ví dụ: `reports/individual/nguyen_van_a.md`*
