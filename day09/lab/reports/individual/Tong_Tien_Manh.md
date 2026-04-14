# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Tống Tiến Mạnh
**Vai trò trong nhóm:** Worker Owner — Retrieval Worker
**Ngày nộp:** 14/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/retrieval.py`
- Functions tôi implement:
  - `_get_embedding_fn()` — khởi tạo OpenAI embedding client với fallback random cho test
  - `_get_collection()` — kết nối ChromaDB, kế thừa collection `rag_lab` từ Day 08
  - `retrieve_dense(query, top_k)` — embed query → query ChromaDB → trả về top_k chunks với score
  - `run(state)` — worker entry point, đọc `task`/`top_k` từ AgentState, ghi `retrieved_chunks`, `retrieved_sources`, `worker_io_logs`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

`graph.py` (do thành viên khác viết) import `from workers.retrieval import run as retrieval_run` tại line 204 — retrieval worker là node trung tâm mà mọi path trong graph đều đi qua trước khi vào `synthesis_worker`. `policy_tool.py` nhận `retrieved_chunks` từ output của worker tôi để chạy `analyze_policy()`. `mcp_server.py` cũng tái dùng `retrieve_dense` trực tiếp trong `tool_search_kb()` (line 152) như fallback.

**Bằng chứng:**
- Commit `23ea1d0 feat: retrieval worker` — commit chứa toàn bộ file `workers/retrieval.py` do tôi push.
- Line 204 `graph.py`: `from workers.retrieval import run as retrieval_run`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Dùng absolute path neo theo vị trí file (`__file__`) thay vì relative path để locate ChromaDB.

Khi bắt đầu, tôi định để `CHROMA_DB_PATH = "chroma_db"` — relative path đơn giản. Vấn đề: path này resolve theo CWD của process, không phải vị trí file. Nếu graph được chạy từ project root (`python day09/lab/graph.py`), CWD là root và `chroma_db/` sẽ tìm sai chỗ. Tương tự khi chạy standalone test từ `workers/`.

Tôi chọn tính path tuyệt đối từ `__file__`:

```python
_LAB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(_LAB_ROOT, "chroma_db"))
```

Lựa chọn thay thế tôi đã cân nhắc: (1) yêu cầu người dùng luôn chạy từ `day09/lab/` — không robust; (2) dùng `pathlib.Path(__file__).parent.parent` — tương đương nhưng không nhất quán với phần còn lại của codebase đang dùng `os`.

**Lý do:** Đảm bảo worker chạy được từ bất kỳ CWD nào — khi `graph.py` import và gọi, khi test standalone, hay khi `eval_trace.py` khởi động pipeline.

**Trade-off đã chấp nhận:** Path hardcoded theo cấu trúc thư mục (`workers/ → lab/ → chroma_db/`). Nếu ai rename thư mục thì sẽ fail — giải quyết bằng env override `CHROMA_DB_PATH`.

**Bằng chứng từ code:**

```python
# workers/retrieval.py, line 40-41
_LAB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(_LAB_ROOT, "chroma_db"))
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** ChromaDB trả về 0 chunks dù collection `rag_lab` đã được index.

**Symptom (pipeline làm gì sai?):**

Khi chạy graph lần đầu, toàn bộ câu hỏi route qua `retrieval_worker` trả về kết quả rỗng. Trace `run_20260414_163938.json` ghi:

```
"[retrieval_worker] retrieved 0 chunks from []"
"final_answer": "[SYNTHESIS ERROR] Không thể gọi LLM. Kiểm tra API key trong .env."
"confidence": 0.1
"retrieved_chunks": []
```

**Root cause:**

`CHROMA_DB_PATH` ban đầu dùng relative path. Khi `graph.py` được import và chạy từ thư mục `day09/lab/`, Python resolve `chroma_db` sang đúng chỗ. Nhưng khi `eval_trace.py` chạy từ project root, path trở thành `./chroma_db` ở root — không tồn tại → `_get_collection()` tạo collection mới rỗng thay vì lấy collection đã có.

**Cách sửa:**

Thay relative path bằng absolute path dựa trên `os.path.abspath(__file__)`:

```python
# Trước (bị lỗi):
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_db")

# Sau (đã sửa):
_LAB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(_LAB_ROOT, "chroma_db"))
```

**Bằng chứng trước/sau:**

Trước khi sửa — trace `run_20260414_163938`:
```
"retrieved_chunks": [], "retrieved_sources": [], "confidence": 0.1
```

Sau khi sửa — grading run `gq03` (route qua policy_tool → retrieval):
```
"sources": ["hr_leave_policy.txt", "access_control_sop.txt", "it_helpdesk_faq.txt"]
"confidence": 0.95, "latency_ms": 7703
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế `run()` theo đúng worker contract — nhận/trả `AgentState` dict, không raise exception ra ngoài (catch toàn bộ lỗi vào `worker_io["error"]`), append đủ `worker_io_logs` và `history`. Điều này giúp `graph.py` và `eval_trace.py` hoạt động ngay mà không cần sửa interface. `mcp_server.py` cũng tái dùng `retrieve_dense` mà không cần sửa gì thêm.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Chưa thêm score threshold filter — retrieval_worker hiện trả về tất cả top_k chunks dù score thấp hay cao. Kết quả: các câu trong grading như `gq01`, `gq05`, `gq07`, `gq08` đều trả về `confidence: 0.1` vì ChromaDB không có đủ dữ liệu SLA, không có filter để abstain sớm.

**Nhóm phụ thuộc vào tôi ở đâu?**

`synthesis_worker` hoàn toàn phụ thuộc vào `retrieved_chunks` do tôi cung cấp — nếu retrieval empty thì synthesis mặc định trả "Không đủ thông tin" với confidence 0.1–0.3.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi cần `index.py` (do thành viên khác implement) đã chạy thành công và có collection `rag_lab` trong `chroma_db/`. Nếu collection rỗng hoặc embedding model khác, `retrieve_dense` trả về garbage.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thêm **score threshold filtering** vào `retrieve_dense`: chỉ trả về chunk có `score >= 0.5`, trả về empty sớm nếu không chunk nào đạt ngưỡng thay vì để synthesis phải "đoán" từ context kém chất lượng. Bằng chứng từ grading: `gq01` (SLA P1 notification) và `gq05` (P1 escalation sau 10 phút) đều trả về `sources: []`, `confidence: 0.1` — pipeline đã retrieve empty nhưng synthesis vẫn được gọi và trả về "Không đủ thông tin". Với threshold filter, abstain sẽ xảy ra sớm hơn và confidence sẽ phản ánh đúng chất lượng evidence.
