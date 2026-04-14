# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** X100 Day09 Team  
**Ngày:** 14/04/2026

Nguồn số liệu chính: artifacts/eval_report.json và artifacts/grading_run.jsonl.

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.820 | 0.475 | -0.345 | Day09 thận trọng hơn, abstain nhiều |
| Avg latency (ms) | 2500 | 4432 | +1932 (+77.3%) | Chi phí orchestration + tool calls |
| Abstain rate (%) | 20% | 67% | +47pp | Day09 ưu tiên an toàn, tránh bịa |
| Multi-hop accuracy | Not tracked | Not tracked | N/A | Chưa có script chấm chính thức theo loại câu |
| Routing visibility | Không có | Có route_reason + supervisor_route | N/A | Day09 debug trực tiếp theo route |
| Debug time (estimate) | 25 phút | 10 phút | -15 phút | Dựa trên 1 vòng debug route + retrieval |
| MCP usage rate | N/A | 47% (7/15) | N/A | Day09 gọi MCP theo nhu cầu |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Khá ổn định | Trung bình, dễ abstain nếu retrieval hụt |
| Latency | Thấp hơn | Cao hơn do nhiều bước |
| Observation | Trả lời nhanh nhưng khó biết sai ở đâu | Có trace rõ route nhưng chi phí cao hơn |

**Kết luận:**

Với câu đơn giản, multi-agent chưa cho thấy lợi thế rõ về chất lượng output trong phiên bản hiện tại. Lợi thế chính nằm ở khả năng quan sát và bảo trì, không phải tốc độ.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Không ổn định | Có cải thiện một phần nhờ policy + MCP |
| Routing visible? | Không | Có |
| Observation | Khó truy nguyên lỗi | Dễ thấy lỗi route hoặc thiếu evidence theo từng node |

**Kết luận:**

Day09 phù hợp hơn cho multi-hop vì có thể tách vai retrieval/policy/tool. Tuy nhiên cần bổ sung chiến lược route chuỗi để tránh chỉ đi một nhánh duy nhất cho câu hỏi lai.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | 20% | 67% |
| Hallucination cases | Cao hơn | Thấp hơn |
| Observation | Có xu hướng trả lời đoán | Từ chối trả lời khi evidence yếu |

**Kết luận:**

Day09 an toàn hơn về mặt chống hallucination, nhưng cần cân bằng lại để không abstain quá mức với các câu hỏi có đủ thông tin trong tài liệu.

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai -> phải đọc toàn bộ pipeline RAG để đoán lỗi nằm ở retrieval hay generation.
Không có route trace nên khó khoanh vùng nhanh.
Thời gian ước tính: ~25 phút/lỗi.
```

### Day 09 — Debug workflow
```
Khi answer sai -> mở trace -> xem supervisor_route + route_reason + workers_called.
Nếu route sai: sửa rule ở supervisor.
Nếu route đúng nhưng output sai: test worker độc lập theo contract.
Thời gian ước tính: ~10 phút/lỗi.
```

**Câu cụ thể nhóm đã debug:**

Ở câu gq09 (P1 + Level 2 emergency), trace cho thấy route vào policy_tool_worker và không đi retrieval chuyên sâu cho SLA. Nhóm xác định đây là lỗi chiến lược route cho truy vấn multi-intent, không phải lỗi LLM thuần.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool + route rule |
| Thêm 1 domain mới | Sửa prompt lớn, khó kiểm thử | Thêm worker/domain module riêng |
| Thay đổi retrieval strategy | Ảnh hưởng pipeline chung | Chỉ sửa retrieval_worker |
| A/B test một phần | Khó | Dễ, thay node hoặc route condition |

**Nhận xét:**

Day09 dễ mở rộng rõ rệt. Việc tách contract giữa supervisor và worker giúp thêm tính năng mà không phá luồng cũ.

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 1 LLM call (synthesis) |
| Complex query | 1 LLM call | 2 LLM calls (policy + synthesis) |
| MCP tool call | N/A | Trung bình 0.6 call/query (9 calls/15 traces) |

**Nhận xét về cost-benefit:**

Multi-agent tăng chi phí và latency, đổi lại có cấu trúc rõ ràng và khả năng mở rộng mạnh hơn. Với hệ production, cần cơ chế dynamic short-circuit để giảm bước không cần thiết cho câu đơn giản.

---

## 6. Kết luận

**Multi-agent tốt hơn single agent ở điểm nào?**

1. Dễ debug và giám sát nhờ trace chi tiết theo route, worker, tool.
2. Dễ mở rộng capability bằng cách thêm worker/MCP tool độc lập.

**Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. Latency và tỉ lệ abstain hiện tại cao hơn đáng kể.

**Khi nào không nên dùng multi-agent?**

Khi bài toán đơn giản, domain hẹp, yêu cầu phản hồi nhanh và không cần orchestration phức tạp.

**Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Thêm cơ chế route đa nhánh cho truy vấn multi-intent, tuning retrieval để giảm abstain giả, và thêm evaluator tự động theo từng loại câu hỏi để theo dõi chất lượng theo tuần.
