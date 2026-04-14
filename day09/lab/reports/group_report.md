# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** X100 Day09 Team  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Nguyễn Minh Hiếu | Supervisor Owner | nguyenhieu16072004@gmail.com |
| Tống Tiến Mạnh | Worker Owner | tienmanhttm2018@gmail.com |
| Hà Huy Hoàng | Worker Owner | masterjtrhoang171110x@gmail.com |
| Nguyễn Lâm Tùng | MCP Owner | nguyenlamtung2005@gmail.com |
| Trần Gia Khánh | MCP Owner | giakhanh28031995@gmail.com |
| Nguyễn Việt Long | Trace & Docs Owner | nguyenvietlong9k@gmail.com |
| Nguyễn Quang Đăng | Trace & Docs Owner | dangnguyen12a@gmail.com |

**Ngày nộp:** 14/04/2026  
**Repo:** d:/assignments_vinuni/X100-Day08-Day09-Day10/day09/lab  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:**

Nhóm triển khai kiến trúc Supervisor-Worker với 5 node chính: supervisor, retrieval_worker, policy_tool_worker, human_review và synthesis_worker. Dòng chảy xử lý bắt đầu từ supervisor để phân loại intent và mức rủi ro, sau đó route sang worker phù hợp trước khi tổng hợp output cuối ở synthesis. So với pipeline single-agent của Day08, hệ thống mới tách rõ trách nhiệm từng thành phần, giúp quan sát và kiểm thử theo module.

Về mặt quan sát, mỗi run đều lưu trace gồm supervisor_route, route_reason, workers_called, mcp_tools_used, confidence và latency_ms. Trong 40 trace gần nhất, phân bố route là 20/40 cho retrieval_worker và 20/40 cho policy_tool_worker, cho thấy supervisor phân nhánh cân bằng giữa hai nhóm câu hỏi chính.

**Routing logic cốt lõi:**
> Mô tả logic supervisor dùng để quyết định route (keyword matching, LLM classifier, rule-based, v.v.)

Nhóm dùng rule-based keyword routing để đảm bảo tốc độ và tính giải thích. Cụ thể, các từ khóa như hoàn tiền, flash sale, access, level 3 sẽ vào policy_tool_worker; các từ khóa như p1, sla, ticket, escalation sẽ vào retrieval_worker; các tín hiệu risk như emergency, 2am, err- sẽ gắn cờ risk_high, và một số trường hợp lỗi mơ hồ có thể đẩy qua human_review. Cách làm này giúp route_reason có thể debug trực tiếp mà không cần suy đoán thêm.

**MCP tools đã tích hợp:**
> Liệt kê tools đã implement và 1 ví dụ trace có gọi MCP tool.

- `search_kb`: Tìm evidence từ KB nội bộ, đã được gọi ở các câu policy như gq03, gq10.
- `get_ticket_info`: Lấy trạng thái/timeline ticket mock, đã được gọi ở gq03 và gq09.
- `check_access_permission`: Đã implement trong MCP server để kiểm tra approver và emergency override theo level access.

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

> Chọn **1 quyết định thiết kế** mà nhóm thảo luận và đánh đổi nhiều nhất.
> Phải có: (a) vấn đề gặp phải, (b) các phương án cân nhắc, (c) lý do chọn phương án đã chọn.

**Quyết định:** Dùng supervisor rule-based routing có route_reason rõ ràng thay vì route bằng LLM classifier ngay từ Sprint 1.

**Bối cảnh vấn đề:**

Trong giai đoạn đầu, nhóm gặp hai áp lực cùng lúc: cần chạy ổn định trong thời gian ngắn và cần trace đủ rõ để phục vụ chấm điểm Day09. Nếu dùng LLM classifier để route ngay từ đầu, chất lượng route có thể khá tốt nhưng khó kiểm soát tính nhất quán, đồng thời khó giải thích vì sao chọn worker A thay vì B ở từng câu cụ thể.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Rule-based keyword routing | Nhanh, dễ debug, route_reason giải thích trực tiếp | Có thể kém linh hoạt với câu multi-intent |
| LLM classifier routing | Linh hoạt ngữ nghĩa tốt hơn | Khó kiểm soát, khó tái lập kết quả, tăng latency |

**Phương án đã chọn và lý do:**

Nhóm chọn rule-based routing để ưu tiên tính ổn định và khả năng quan sát theo yêu cầu bài lab. Quyết định này giúp nhóm xác định lỗi nhanh khi pipeline sai: nếu route_reason cho thấy vào đúng nhánh nhưng answer vẫn sai thì lỗi nằm ở worker; nếu route_reason chưa đúng thì chỉnh logic supervisor. Trong dữ liệu cập nhật, route distribution 20/40 retrieval và 20/40 policy cho thấy logic route đang cân bằng thay vì lệch về một phía.

**Bằng chứng từ trace/code:**
> Dẫn chứng cụ thể (VD: route_reason trong trace, đoạn code, v.v.)

```
gq03:
  supervisor_route = policy_tool_worker
  route_reason = "policy keywords matched: ['access', 'level 3']"
  workers_called = ["policy_tool_worker", "synthesis_worker"]
  mcp_tools_used = ["search_kb", "get_ticket_info"]

gq01:
  supervisor_route = retrieval_worker
  route_reason = "retrieval keywords matched: ['p1', 'sla', 'ticket', 'escalation']"

Nguồn: artifacts/grading_run.jsonl
```

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** 54 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: gq03 — Lý do tốt: Route đúng domain access, có dùng MCP search_kb + get_ticket_info, trả lời đúng số approver và cấp phê duyệt cao nhất.

**Câu pipeline fail hoặc partial:**
- ID: gq01 — Fail ở đâu: Câu hỏi SLA chi tiết nhưng output abstain.  
  Root cause: Retrieval chưa lấy đúng đoạn chứa thông tin notification channel và escalation deadline.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?

Pipeline trả lời abstain rõ ràng: "Không đủ thông tin trong tài liệu nội bộ." Đây là hướng xử lý an toàn để tránh hallucination đối với câu hỏi truy vấn mức phạt tài chính SLA mà tài liệu nhóm không có bằng chứng chắc chắn.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?

Có. Trace ghi 2 workers: policy_tool_worker và synthesis_worker. Hệ thống trả lời được phần điều kiện cấp quyền khá ổn, nhưng phần SLA P1 chưa đủ chính xác theo tiêu chí multi-hop đầy đủ, nên nhóm đánh giá mức partial.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

> Dựa vào `docs/single_vs_multi_comparison.md` — trích kết quả thực tế.

**Metric thay đổi rõ nhất (có số liệu):**

Hai thay đổi rõ nhất là latency và confidence. Avg latency tăng từ 2500ms (Day08) lên 4668ms (Day09), tương đương +86.7%. Avg confidence giảm từ 0.820 xuống 0.461. Về abstain rate, bản chạy cập nhật cho thấy Day09 ở mức 28% so với 10% của Day08 (+18 điểm phần trăm), thấp hơn đáng kể so với các lần chạy thử trước đó.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**

Điều bất ngờ là dù chất lượng answer chưa tăng ngay, thời gian debug lại giảm đáng kể. Nhờ route_reason và workers_called, nhóm có thể khoanh vùng lỗi nhanh trong khoảng 10 phút thay vì phải đọc toàn pipeline như Day08.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**

Với câu đơn giản một nguồn, multi-agent vẫn làm tăng overhead orchestration và chi phí gọi model/tool. Trong các trường hợp truy vấn dễ, single-agent vẫn có lợi thế tốc độ phản hồi.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Nguyễn Minh Hiếu | Thiết kế supervisor, routing logic, kết nối graph | Sprint 1 |
| Tống Tiến Mạnh, Hà Huy Hoàng | Retrieval worker và synthesis worker | Sprint 2 |
| Nguyễn Tùng Lâm, Trần Gia Khánh | MCP server và tích hợp tool calls | Sprint 3 |
| Nguyễn Việt Long, Nguyễn Quang Đăng | Trace analysis, docs, tổng hợp báo cáo | Sprint 4 |

**Điều nhóm làm tốt:**

Nhóm chia vai theo module rõ ràng, bám sát contracts và trace. Các quyết định kỹ thuật đều để lại bằng chứng trong code và log, giúp phần tài liệu không bị mô tả chung chung.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

Tuning chất lượng giữa retrieval và synthesis chưa được đồng bộ sớm, dẫn đến nhiều câu abstain dù route hợp lý. Một số quyết định tối ưu hiệu năng được thực hiện muộn ở cuối phiên.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

Nhóm sẽ thêm checkpoint tích hợp sau mỗi sprint (không chờ đến cuối), có bộ test hồi quy theo category câu hỏi để phát hiện sớm lỗi multi-hop và lỗi nguồn.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nếu có thêm 1 ngày, nhóm sẽ triển khai hai cải tiến. Thứ nhất, bổ sung route orchestration cho truy vấn multi-intent để cho phép đi qua cả retrieval và policy một cách có chủ đích, đặc biệt cho mẫu câu kiểu gq09. Thứ hai, tinh chỉnh retrieval (query rewrite + rerank theo domain) nhằm giảm abstain rate từ mức 28% hiện tại xuống dưới 20% mà vẫn giữ tính an toàn chống hallucination. Hai hướng này bám trực tiếp vào điểm yếu đã thấy trong trace và metrics cập nhật.

---

*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
