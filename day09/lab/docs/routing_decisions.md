# Routing Decisions Log — Lab Day 09

**Nhóm:** X100 Day09 Team  
**Ngày:** 14/04/2026

Tài liệu này tổng hợp quyết định routing thực tế từ trace đã chạy ở bộ grading questions.

---

## Routing Decision #1

**Task đầu vào:**
> Ticket P1 được tạo lúc 22:47. Đúng theo SLA, ai nhận thông báo đầu tiên và qua kênh nào? Deadline escalation là mấy giờ?

**Worker được chọn:** retrieval_worker  
**Route reason (từ trace):** retrieval keywords matched: ['p1', 'sla', 'ticket', 'escalation']  
**MCP tools được gọi:** Không có  
**Workers called sequence:** retrieval_worker → synthesis_worker

**Kết quả thực tế:**
- final_answer (ngắn): Không đủ thông tin trong tài liệu nội bộ.
- confidence: 0.10
- Correct routing? Yes

**Nhận xét:**

Route đúng theo intent câu hỏi SLA/ticket, nhưng output bị abstain do evidence chưa đủ chi tiết ở bước retrieval cho truy vấn có nhiều ràng buộc thời gian.

---

## Routing Decision #2

**Task đầu vào:**
> Engineer cần Level 3 access để khắc phục P1 đang active. Bao nhiêu người phải phê duyệt? Ai là người phê duyệt cuối cùng?

**Worker được chọn:** policy_tool_worker  
**Route reason (từ trace):** policy keywords matched: ['access', 'level 3']  
**MCP tools được gọi:** search_kb, get_ticket_info  
**Workers called sequence:** policy_tool_worker → synthesis_worker

**Kết quả thực tế:**
- final_answer (ngắn): Trả về 3 approvers (Line Manager, IT Admin, IT Security), người cuối là IT Security.
- confidence: 0.95
- Correct routing? Yes

**Nhận xét:**

Đây là route có chất lượng tốt nhất trong bộ grading: đúng domain access-control, có gọi MCP, và câu trả lời có cấu trúc rõ ràng.

---

## Routing Decision #3

**Task đầu vào:**
> Sự cố P1 xảy ra lúc 2am. Đồng thời cần cấp Level 2 access tạm thời cho contractor để emergency fix. Hãy nêu đầy đủ quy trình SLA và điều kiện cấp quyền.

**Worker được chọn:** policy_tool_worker  
**Route reason (từ trace):** policy keywords matched: ['access'] | risk_high flagged (['emergency', '2am'])  
**MCP tools được gọi:** search_kb, get_ticket_info  
**Workers called sequence:** policy_tool_worker → synthesis_worker

**Kết quả thực tế:**
- final_answer (ngắn): Có nêu được phần điều kiện cấp quyền, nhưng phần SLA P1 chưa đủ sát theo tài liệu.
- confidence: 0.95
- Correct routing? No (partial)

**Nhận xét:**

Câu này là multi-hop nên cần vừa SLA vừa access policy. Route hiện tại nghiêng quá nhiều về policy branch, thiếu bằng chứng retrieval chuyên cho SLA.

---

## Routing Decision #4 (tuỳ chọn — bonus)

**Task đầu vào:**
> Khách hàng mua trong Flash Sale, phát hiện lỗi nhà sản xuất và yêu cầu hoàn tiền trong 5 ngày.

**Worker được chọn:** policy_tool_worker  
**Route reason:** policy keywords matched: ['hoàn tiền', 'flash sale']

**Nhận xét:**

Đây là trường hợp route tốt vì exception rule nằm trong policy. Hệ thống đã gọi search_kb và trả kết luận nhất quán với rule Flash Sale không hoàn tiền.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 8 | 53% |
| policy_tool_worker | 7 | 47% |
| human_review | 0 | 0% |

### Routing Accuracy

- Câu route đúng: 9 / 10 (theo bộ grading)
- Câu route sai hoặc partial: 1 / 10 (gq09, thiếu retrieval evidence cho nhánh SLA)
- Câu trigger HITL: 1 / 15 (theo tổng trace gần nhất trong eval_report)

### Lesson Learned về Routing

1. Rule-based routing theo keyword cho tốc độ và độ ổn định tốt ở sprint đầu, dễ debug hơn LLM classifier.
2. Với truy vấn multi-hop, cần route theo chuỗi hoặc route song song thay vì chọn 1 worker duy nhất từ đầu.

### Route Reason Quality

Chất lượng route_reason đủ để debug nhanh vì đã ghi keyword cụ thể khớp truy vấn (ví dụ: policy/retrieval/risk signals). Tuy nhiên nhóm sẽ cải tiến thêm format chuẩn gồm 4 phần: matched_keywords, rejected_routes, risk_flags, next_node để phân tích sai lệch rõ hơn.
