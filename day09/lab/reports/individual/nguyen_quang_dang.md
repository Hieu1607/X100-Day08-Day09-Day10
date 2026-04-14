# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Quang Đăng  
**Vai trò trong nhóm:** Trace & Docs Owner  
**Ngày nộp:** 14/04/2026  
**Độ dài:** khoảng 650 từ

---

## 1. Tôi phụ trách phần nào?

Trong bài lab Day 09, tôi phụ trách phần trace, tổng hợp metrics và viết tài liệu kỹ thuật cho nhóm. Cụ thể, tôi làm việc trực tiếp trên file eval_trace.py để chạy bộ câu hỏi, đọc trace và trích số liệu so sánh giữa Day 08 và Day 09. Đồng thời, tôi chịu trách nhiệm điền và đồng bộ nội dung trong các tài liệu docs/system_architecture.md, docs/routing_decisions.md, docs/single_vs_multi_comparison.md và reports/group_report.md.

Phần của tôi kết nối với phần code của các thành viên khác theo hướng sau: supervisor và workers tạo ra trace đầu ra, còn tôi chuẩn hóa cách đọc trace và chuyển kết quả này thành bằng chứng định lượng trong báo cáo. Nếu không có phần tôi làm, nhóm vẫn có thể chạy pipeline, nhưng sẽ khó chứng minh hiệu quả kỹ thuật, khó giải thích vì sao route đúng/sai và dễ mất điểm ở rubric documentation + comparison.

Bằng chứng trực tiếp của phần tôi phụ trách là các chỉ số trong artifacts/eval_report.json như routing_distribution, avg_latency_ms, abstain_rate, mcp_usage_rate và việc các số này được phản ánh nhất quán trong các file docs và group report.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

Quyết định kỹ thuật tôi chủ động đề xuất là dùng hai lớp số liệu khi viết tài liệu: một lớp cho grading run (10 câu) và một lớp cho tổng trace tích lũy (40 trace), thay vì trộn chung một nguồn dữ liệu.

Lúc đầu nhóm có tình trạng số liệu bị lệch giữa các file vì có file dùng 15 trace cũ, file khác dùng kết quả grading mới. Nếu tôi lấy một con số duy nhất cho tất cả, báo cáo sẽ mâu thuẫn nội bộ. Tôi cân nhắc hai lựa chọn:

1. Chỉ dùng grading run cho toàn bộ báo cáo.
2. Tách rõ: routing accuracy theo grading run, còn vận hành hệ thống theo tổng trace tích lũy.

Tôi chọn phương án 2 vì phù hợp bản chất dữ liệu hơn. Grading run phản ánh kết quả chấm chính thức trong khung thời gian cụ thể, còn tổng trace phản ánh hành vi hệ thống ổn định hơn về phân bố route, latency và mức dùng MCP. Cách tách này giúp phần phân tích vừa sát chấm điểm vừa có giá trị kỹ thuật.

Trade-off tôi chấp nhận là tài liệu dài hơn, phải ghi chú ngữ cảnh số liệu ở nhiều chỗ để tránh người đọc hiểu nhầm. Tuy nhiên đổi lại, báo cáo nhất quán hơn và có khả năng defend khi giảng viên đối chiếu giữa artifacts và markdown.

Bằng chứng thể hiện quyết định có hiệu quả là: các file docs đã thống nhất số liệu 40 trace cho metrics vận hành (ví dụ 20/40 retrieval, 20/40 policy; latency trung bình 4668ms; abstain 28%), trong khi phần routing accuracy theo grading vẫn ghi rõ 9/10 và 1 câu partial ở gq09.

---

## 3. Tôi đã sửa một lỗi gì?

Lỗi tôi xử lý là lỗi không nhất quán số liệu giữa các tài liệu sau khi nhóm cập nhật lại grading run. Symptom ban đầu là trong một số file vẫn còn số liệu cũ như 15 traces, abstain 67%, latency 4432ms, trong khi eval_report mới đã chuyển sang 40 traces, abstain 28%, latency 4668ms. Nếu giữ nguyên, báo cáo nhóm sẽ tự mâu thuẫn và có nguy cơ bị trừ điểm ở tiêu chí evidence consistency.

Root cause nằm ở quy trình cập nhật thủ công: mỗi file được chỉnh ở thời điểm khác nhau, nhưng không có bước đồng bộ cuối cùng sau khi artifacts thay đổi. Ngoài ra, routing_decisions.md dùng mẫu 3-4 quyết định từ grading run nhưng phần summary lại đang lấy nền 15 trace cũ, làm số tổng kết bị lệch.

Cách tôi sửa là đọc lại toàn bộ artifacts/grading_run.jsonl và artifacts/eval_report.json, sau đó cập nhật đồng bộ các file docs và group report theo đúng ngữ cảnh số liệu. Tôi giữ nguyên các nhận định định tính có giá trị, nhưng thay toàn bộ số định lượng cũ bằng bản mới, đồng thời ghi rõ đâu là số theo grading run, đâu là số theo tổng trace.

Bằng chứng trước/sau:

- Trước sửa: có các mốc 15 trace, 67%, 4432ms xuất hiện trong docs và report.
- Sau sửa: toàn bộ docs/report dùng thống nhất 40 trace, 20/40 route mỗi nhánh, avg latency 4668ms, avg confidence 0.461, abstain 28%, mcp usage 50%.

Kết quả là bộ tài liệu hiện tại không còn xung đột nội bộ và khớp trực tiếp với artifacts mới nhất.

---

## 4. Tôi tự đánh giá đóng góp của mình

Điểm tôi làm tốt nhất là khả năng biến trace kỹ thuật thành lập luận báo cáo có thể kiểm chứng. Tôi không chỉ mô tả hệ thống hoạt động ra sao mà còn bám số liệu thật, cập nhật theo phiên bản mới và đảm bảo các file thống nhất với nhau.

Điểm tôi chưa tốt là chưa thiết lập sẵn một checklist tự động để cảnh báo khi metrics thay đổi, nên vẫn phải rà bằng tay nhiều lần. Điều này tốn thời gian và dễ sai sót nếu deadline gấp.

Nhóm phụ thuộc vào tôi ở phần hoàn thiện bằng chứng và narrative cho phần nộp: nếu phần docs/report không chốt, nhóm khó thể hiện đầy đủ giá trị kỹ thuật dù code đã chạy được.

Ngược lại, tôi phụ thuộc vào các bạn phụ trách supervisor/worker/MCP ở chất lượng trace đầu vào. Nếu route_reason hoặc mcp_tools_used ghi không đầy đủ thì phần phân tích của tôi sẽ thiếu độ tin cậy.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Nếu có thêm 2 giờ, tôi sẽ thêm một bước validation tự động trong eval_trace.py để đối chiếu số liệu trong artifacts với các mốc chính cần điền vào tài liệu. Lý do là trace gq09 và các lần re-run cho thấy metrics thay đổi khá nhanh theo phiên bản pipeline; có validator tự động sẽ giảm rủi ro lệch số liệu khi cập nhật báo cáo ở phút cuối.

---