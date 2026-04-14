# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Nguyễn Việt Long  
**Vai trò trong nhóm:** Trace & Evaluation Owner (Sprint 4)  
**Ngày nộp:** 14/04/2026  
**Độ dài:** ~680 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Trong Day 09, phần tôi làm tập trung vào khâu đánh giá và chuẩn hóa đầu ra trace cho sprint cuối. Dựa trên lịch sử commit của tôi trên nhánh `long`, tôi có 3 commit chính liên quan trực tiếp tới `day09/lab`: `bc21551` (evaluation), `61aaee0` (add grading run), và `0a716f3` (fix grading results). Trong đó commit `bc21551` là phần code cốt lõi vì tôi sửa `eval_trace.py` để pipeline đánh giá chạy ổn định hơn và sinh metric rõ ràng hơn cho việc phân tích.

**Module/file tôi chịu trách nhiệm:**
- File chính: `day09/lab/eval_trace.py`
- Files kết quả: `day09/lab/artifacts/eval_report.json`, `day09/lab/artifacts/grading_run.jsonl`, `day09/lab/artifacts/grading_run.json`, `day09/lab/artifacts/traces/*.json`

Công việc của tôi nối với phần của các bạn khác ở chỗ: nếu worker/supervisor chạy được nhưng trace không chuẩn hoặc grading log không đúng format, nhóm vẫn mất điểm phần Sprint 4 và SCORING phần grading artifacts.

**Bằng chứng:**
- `bc21551` sửa code `eval_trace.py` + cập nhật `eval_report.json`, traces.
- `61aaee0` thêm `artifacts/grading_run.jsonl`.
- `0a716f3` thêm `artifacts/grading_run.json` và chỉnh `grading_run.jsonl`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Tôi chuyển `eval_trace.py` sang hướng “robust evaluation script” thay vì script chỉ chạy happy-path, bằng cách thêm normalize dữ liệu và fallback khi thiếu runtime dependency.

Ở commit `bc21551`, tôi thêm hàm `_get_graph_api()` để lazy import `run_graph, save_trace`, giúp mode analyze/compare chạy được ngay cả khi môi trường thiếu dependency chạy graph. Tôi cũng chuẩn hóa dữ liệu trace bằng `_to_float()`, `_fmt_rate()`, `_percentile()`, `_is_abstain()` và logic parse baseline Day 08 (`_load_day08_baseline()`). Đồng thời, trong `run_grading_questions()`, tôi xử lý mềm các trường dễ thiếu: `sources`, `supervisor_route`, `route_reason`, danh sách `mcp_tools_used` (kể cả trường hợp tool item không phải dict).

Lựa chọn thay thế là giữ script đơn giản như ban đầu: đọc trace, tính vài số trung bình, và giả định schema luôn đúng. Tôi không chọn cách đó vì trace thực tế thường có dữ liệu thiếu/khác kiểu khi chạy nhiều phiên.

**Trade-off đã chấp nhận:** code `eval_trace.py` dài và phức tạp hơn, nhưng đổi lại việc phân tích có độ bền cao hơn, ít vỡ khi đầu vào không đồng nhất.

**Bằng chứng từ code (commit `bc21551`):**
```python
def _get_graph_api():
    sys.path.insert(0, os.path.dirname(__file__))
    from graph import run_graph, save_trace
    return run_graph, save_trace

"supervisor_route": result.get("supervisor_route") or "unknown",
"route_reason": result.get("route_reason") or "missing_route_reason",
"confidence": round(_to_float(result.get("confidence", 0.0), 0.0), 3),
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** Kết quả grading ban đầu trong `artifacts/grading_run.jsonl` chưa phản ánh tốt chất lượng trả lời và thiếu file tổng hợp JSON dạng mảng để đối chiếu nhanh.

**Symptom:** Trước khi fix (`61aaee0`), log grading có nhiều câu trả lời “Không đủ thông tin...” và source chưa sát tài liệu mục tiêu ở một số câu. Ngoài ra chỉ có file `.jsonl`, chưa có bản tổng hợp `.json` dễ đọc toàn bộ run.

**Root cause:** Đầu ra grading trước đó chưa được rà soát/chỉnh lại ở bước hậu xử lý artifacts sau khi chạy; format đủ để chấm tự động nhưng chưa tối ưu cho kiểm tra thủ công và đối chiếu nhanh theo từng câu.

**Cách sửa:** Ở commit `0a716f3`, tôi thêm `artifacts/grading_run.json` và đồng bộ lại `artifacts/grading_run.jsonl` với nội dung trả lời/sources chi tiết hơn theo từng câu `gq01..gq10`, đồng thời giữ đủ các field chấm điểm như `supervisor_route`, `route_reason`, `workers_called`, `mcp_tools_used`, `confidence`, `timestamp`.

**Bằng chứng trước/sau:**
- Trước (`61aaee0`): có `grading_run.jsonl` nhưng nhiều answer dạng abstain, một số source chưa bám đúng doc đích.
- Sau (`0a716f3`): thêm `grading_run.json` và `grading_run.jsonl` được cập nhật với answer cụ thể hơn, ví dụ `gq01` có escalation 22:57 + source `sla_p1_2026.txt`, `gq04` trả 110% store credit + source `policy_refund_v4.txt`.

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**  
Tôi làm tốt ở phần cuối pipeline: biến output chạy thử thành artifacts có thể đọc, so sánh và dùng cho chấm điểm. Commit `bc21551` giúp phần evaluate có nhiều metric hơn và ổn định hơn khi dữ liệu trace không hoàn hảo.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**  
Phần đóng góp của tôi nghiêng về evaluation/artifacts, chưa đóng góp trực tiếp vào logic supervisor hay worker core. Vì vậy phạm vi kỹ thuật của tôi hẹp hơn các bạn làm kiến trúc.

**Nhóm phụ thuộc vào tôi ở đâu?**  
Nhóm phụ thuộc ở khâu Sprint 4: nếu không có grading artifacts đúng format và báo cáo trace rõ, nhóm dễ mất điểm SCORING phần grading và comparison.

**Phần tôi phụ thuộc vào thành viên khác:**  
Tôi phụ thuộc vào chất lượng output từ `graph.py` và các worker; nếu upstream route/answer sai thì dù tôi chuẩn hóa trace tốt vẫn không cứu được quality của final answers.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm bước kiểm tra tự động consistency cho grading artifacts (schema + đối chiếu nguồn theo từng câu), vì diff giữa `61aaee0` và `0a716f3` cho thấy việc rà soát thủ công cuối giờ rất dễ bỏ sót. Cụ thể, tôi muốn có script validate rằng mỗi record đều có `supervisor_route`, `route_reason`, `sources` không rỗng khi câu hỏi có thể retrieve được, và tách cảnh báo cho các câu abstain để nhóm kiểm tra lại trước deadline.