# Scorecard: variant_hybrid_rerank
Generated: 2026-04-13 17:25

## Summary

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.30/5 |
| Relevance | 4.60/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.20/5 |

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Notes |
|----|----------|----------|----------|--------|----------|-------|
| q01 | SLA | 5 | 5 | 5 | 4 | Phần lớn từ ngữ match với chunks (>80%) |
| q02 | Refund | 5 | 5 | 5 | 5 | Phần lớn từ ngữ match với chunks (>80%) |
| q03 | Access Control | 5 | 4 | 5 | 3 | Phần lớn từ ngữ match với chunks (>80%) |
| q04 | Refund | 4 | 5 | 5 | 2 | Tỉ lệ match tốt (65-80%), có thể có thêm model kno |
| q05 | IT Helpdesk | 5 | 5 | 5 | 5 | Phần lớn từ ngữ match với chunks (>80%) |
| q06 | SLA | 5 | 4 | 5 | 4 | Phần lớn từ ngữ match với chunks (>80%) |
| q07 | Access Control | 5 | 5 | 5 | 3 | Phần lớn từ ngữ match với chunks (>80%) |
| q08 | HR Policy | 4 | 5 | 5 | 2 | Tỉ lệ match tốt (65-80%), có thể có thêm model kno |
| q09 | Insufficient Context | 3 | 4 | None | 2 | Match trung bình (50-65%), một phần thông tin từ m |
| q10 | Refund | 2 | 4 | 5 | 2 | Match thấp (<50%), nhiều thông tin không từ chunks |

# Scorecard: variant_dense_rerank
Generated: 2026-04-13 16:35

## Summary

| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.70/5 |
| Relevance | 3.20/5 |
| Context Recall | 5.00/5 |
| Completeness | 3.60/5 |

## Per-Question Results

| ID | Category | Faithful | Relevant | Recall | Complete | Notes |
|----|----------|----------|----------|--------|----------|-------|
| q01 | SLA | 5 | 2 | 5 | 3 | Heuristic overlap with retrieved context suggests  |
| q02 | Refund | 5 | 3 | 5 | 5 | Heuristic overlap with retrieved context suggests  |
| q03 | Access Control | 5 | 3 | 5 | 4 | Heuristic overlap with retrieved context suggests  |
| q04 | Refund | 5 | 4 | 5 | 4 | Heuristic overlap with retrieved context suggests  |
| q05 | IT Helpdesk | 5 | 4 | 5 | 5 | Heuristic overlap with retrieved context suggests  |
| q06 | SLA | 5 | 1 | 5 | 3 | Heuristic overlap with retrieved context suggests  |
| q07 | Access Control | 4 | 4 | 5 | 4 | Heuristic overlap with retrieved context suggests  |
| q08 | HR Policy | 5 | 3 | 5 | 4 | Heuristic overlap with retrieved context suggests  |
| q09 | Insufficient Context | 4 | 5 | None | 2 | Answer abstains instead of hallucinating |
| q10 | Refund | 4 | 3 | 5 | 2 | Answer abstains instead of hallucinating |
