"""
eval_trace.py — Trace Evaluation & Comparison
Sprint 4: Chạy pipeline với test questions, phân tích trace, so sánh single vs multi.

Chạy:
    python eval_trace.py                  # Chạy 15 test questions
    python eval_trace.py --grading        # Chạy grading questions (sau 17:00)
    python eval_trace.py --analyze        # Phân tích trace đã có
    python eval_trace.py --compare        # So sánh single vs multi

Outputs:
    artifacts/traces/          — trace của từng câu hỏi
    artifacts/grading_run.jsonl — log câu hỏi chấm điểm
    artifacts/eval_report.json  — báo cáo tổng kết
"""

import json
import os
import sys
import argparse
import csv
import re
from datetime import datetime
from typing import Optional

# ─────────────────────────────────────────────
# Absolute paths — neo vào vị trí file để chạy được từ bất kỳ CWD nào.
# ─────────────────────────────────────────────
LAB_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(LAB_ROOT, "data")
ARTIFACTS_DIR = os.path.join(LAB_ROOT, "artifacts")
TRACES_DIR = os.path.join(ARTIFACTS_DIR, "traces")
GRADING_LOG_PATH = os.path.join(ARTIFACTS_DIR, "grading_run.jsonl")
EVAL_REPORT_PATH = os.path.join(ARTIFACTS_DIR, "eval_report.json")
DEFAULT_TEST_QUESTIONS = os.path.join(DATA_DIR, "test_questions.json")
DEFAULT_GRADING_QUESTIONS = os.path.join(DATA_DIR, "grading_questions.json")

# Day 08 results (để fallback baseline trong compare_single_vs_multi)
REPO_ROOT = os.path.dirname(os.path.dirname(LAB_ROOT))
DAY08_RESULTS_DIR = os.path.join(REPO_ROOT, "day08", "lab", "results")
DAY08_SCORECARD_PATH = os.path.join(DAY08_RESULTS_DIR, "scorecard_baseline.md")
DAY08_AB_CSV_PATH = os.path.join(DAY08_RESULTS_DIR, "ab_comparison.csv")


def _get_graph_api():
    """Lazy import graph để mode analyze/compare chạy được ngay cả khi thiếu runtime deps."""
    if LAB_ROOT not in sys.path:
        sys.path.insert(0, LAB_ROOT)
    from graph import run_graph, save_trace
    return run_graph, save_trace


ABSTAIN_PATTERNS = [
    "khong du thong tin",
    "không đủ thông tin",
    "khong tim thay thong tin",
    "không tìm thấy thông tin",
    "toi khong biet",
    "tôi không biết",
    "insufficient",
    "not enough information",
]


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _fmt_rate(count: int, total: int) -> str:
    if total <= 0:
        return "0/0 (0%)"
    return f"{count}/{total} ({round(100 * count / total)}%)"


def _percentile(values: list[float], q: float) -> int:
    if not values:
        return 0
    if q <= 0:
        return int(round(min(values)))
    if q >= 100:
        return int(round(max(values)))
    sorted_vals = sorted(values)
    idx = int(round((len(sorted_vals) - 1) * (q / 100.0)))
    return int(round(sorted_vals[idx]))


def _is_abstain(answer: str) -> bool:
    normalized = (answer or "").strip().lower()
    return any(p in normalized for p in ABSTAIN_PATTERNS)


def _parse_percent_str(value: str) -> Optional[float]:
    if not isinstance(value, str):
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", value)
    if not match:
        return None
    return float(match.group(1))


def _parse_scorecard_markdown(md_path: str) -> dict:
    metrics = {}
    if not os.path.exists(md_path):
        return metrics
    with open(md_path, encoding="utf-8") as f:
        text = f.read()

    # Ví dụ dòng: | Faithfulness | 4.30/5 |
    table_pattern = re.compile(
        r"\|\s*(Faithfulness|Relevance|Context Recall|Completeness)\s*\|\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*5\s*\|",
        flags=re.IGNORECASE,
    )
    for metric_name, score in table_pattern.findall(text):
        key = metric_name.lower().replace(" ", "_") + "_score"
        metrics[key] = round(float(score), 2)
    return metrics


def _load_day08_baseline(day08_results_file: Optional[str] = None) -> dict:
    """Load baseline Day 08 từ file truyền vào hoặc fallback từ artifacts/results."""
    # TODO: Load Day 08 results nếu có
    # Nếu không có, dùng baseline giả lập để format
    baseline = {
        "total_questions": 15,
        "avg_confidence": 0.82,
        "avg_latency_ms": 2500,
        "abstain_rate": "20%",
        "multi_hop_accuracy": "Not tracked",
    }

    # 1) Ưu tiên file chỉ định qua tham số
    if day08_results_file and os.path.exists(day08_results_file):
        try:
            with open(day08_results_file, encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict) and "day08_single_agent" in payload:
                payload = payload["day08_single_agent"]
            if isinstance(payload, dict):
                baseline.update(payload)
                return baseline
        except Exception:
            pass

    # 2) Fallback: dùng scorecard markdown từ Day 08 (absolute path)
    baseline.update(_parse_scorecard_markdown(DAY08_SCORECARD_PATH))

    # 3) Fallback: tính abstain rate từ ab_comparison.csv (baseline_dense)
    ab_csv_path = DAY08_AB_CSV_PATH
    if os.path.exists(ab_csv_path):
        try:
            total = 0
            abstains = 0
            with open(ab_csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("config_label") != "baseline_dense":
                        continue
                    total += 1
                    if _is_abstain(row.get("answer", "")):
                        abstains += 1
            if total:
                baseline["total_questions"] = total
                baseline["abstain_rate"] = f"{round(100 * abstains / total)}%"
        except Exception:
            pass

    return baseline


# ─────────────────────────────────────────────
# 1. Run Pipeline on Test Questions
# ─────────────────────────────────────────────

def run_test_questions(questions_file: str = DEFAULT_TEST_QUESTIONS) -> list:
    """
    Chạy pipeline với danh sách câu hỏi, lưu trace từng câu.

    Returns:
        list of (question, result) tuples
    """
    run_graph, save_trace = _get_graph_api()

    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    print(f"\n📋 Running {len(questions)} test questions from {questions_file}")
    print("=" * 60)

    results = []
    for i, q in enumerate(questions, 1):
        question_text = q["question"]
        q_id = q.get("id", f"q{i:02d}")

        print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

        try:
            result = run_graph(question_text)

            # Save individual trace
            trace_file = save_trace(result, TRACES_DIR)
            print(f"  ✓ route={result.get('supervisor_route', '?')}, "
                  f"conf={result.get('confidence', 0):.2f}, "
                  f"{result.get('latency_ms', 0)}ms")

            results.append({
                "id": q_id,
                "question": question_text,
                "expected_answer": q.get("expected_answer", ""),
                "expected_sources": q.get("expected_sources", []),
                "difficulty": q.get("difficulty", "unknown"),
                "category": q.get("category", "unknown"),
                "result": result,
            })

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({
                "id": q_id,
                "question": question_text,
                "error": str(e),
                "result": None,
            })

    print(f"\n✅ Done. {sum(1 for r in results if r.get('result'))} / {len(results)} succeeded.")
    return results


# ─────────────────────────────────────────────
# 2. Run Grading Questions (Sprint 4)
# ─────────────────────────────────────────────

def run_grading_questions(questions_file: str = DEFAULT_GRADING_QUESTIONS) -> str:
    """
    Chạy pipeline với grading questions và lưu JSONL log.
    Dùng cho chấm điểm nhóm (chạy sau khi grading_questions.json được public lúc 17:00).

    Returns:
        path tới grading_run.jsonl
    """
    if not os.path.exists(questions_file):
        print(f"❌ {questions_file} chưa được public (sau 17:00 mới có).")
        return ""

    run_graph, _ = _get_graph_api()

    with open(questions_file, encoding="utf-8") as f:
        questions = json.load(f)

    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    output_file = GRADING_LOG_PATH

    print(f"\n🎯 Running GRADING questions — {len(questions)} câu")
    print(f"   Output → {output_file}")
    print("=" * 60)

    with open(output_file, "w", encoding="utf-8") as out:
        for i, q in enumerate(questions, 1):
            q_id = q.get("id", f"gq{i:02d}")
            question_text = q["question"]
            print(f"[{i:02d}/{len(questions)}] {q_id}: {question_text[:65]}...")

            try:
                result = run_graph(question_text)
                mcp_tools_raw = result.get("mcp_tools_used", [])
                mcp_tool_names = []
                for tool_item in mcp_tools_raw:
                    if isinstance(tool_item, dict):
                        mcp_tool_names.append(tool_item.get("tool", "unknown"))
                    else:
                        mcp_tool_names.append(str(tool_item))

                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": result.get("final_answer", "PIPELINE_ERROR: no answer"),
                    "sources": result.get("retrieved_sources") or result.get("sources", []),
                    "supervisor_route": result.get("supervisor_route") or "unknown",
                    "route_reason": result.get("route_reason") or "missing_route_reason",
                    "workers_called": result.get("workers_called", []),
                    "mcp_tools_used": mcp_tool_names,
                    "confidence": round(_to_float(result.get("confidence", 0.0), 0.0), 3),
                    "hitl_triggered": result.get("hitl_triggered", False),
                    "latency_ms": result.get("latency_ms"),
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"  ✓ route={record['supervisor_route']}, conf={record['confidence']:.2f}")
            except Exception as e:
                record = {
                    "id": q_id,
                    "question": question_text,
                    "answer": f"PIPELINE_ERROR: {e}",
                    "sources": [],
                    "supervisor_route": "error",
                    "route_reason": str(e),
                    "workers_called": [],
                    "mcp_tools_used": [],
                    "confidence": 0.0,
                    "hitl_triggered": False,
                    "latency_ms": None,
                    "timestamp": datetime.now().isoformat(),
                }
                print(f"  ✗ ERROR: {e}")

            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n✅ Grading log saved → {output_file}")
    return output_file


# ─────────────────────────────────────────────
# 3. Analyze Traces
# ─────────────────────────────────────────────

def analyze_traces(traces_dir: str = TRACES_DIR) -> dict:
    """
    Đọc tất cả trace files và tính metrics tổng hợp.

    Metrics:
    - routing_distribution: % câu đi vào mỗi worker
    - avg_confidence: confidence trung bình
    - avg_latency_ms: latency trung bình
    - mcp_usage_rate: % câu có MCP tool call
    - hitl_rate: % câu trigger HITL
    - source_coverage: các tài liệu nào được dùng nhiều nhất

    Returns:
        dict of metrics
    """
    if not os.path.exists(traces_dir):
        print(f"⚠️  {traces_dir} không tồn tại. Chạy run_test_questions() trước.")
        return {}

    trace_files = sorted([f for f in os.listdir(traces_dir) if f.endswith(".json")])
    if not trace_files:
        print(f"⚠️  Không có trace files trong {traces_dir}.")
        return {}

    traces = []
    for fname in trace_files:
        trace_path = os.path.join(traces_dir, fname)
        try:
            with open(trace_path, encoding="utf-8") as f:
                traces.append(json.load(f))
        except UnicodeDecodeError:
            with open(trace_path, encoding="utf-8", errors="ignore") as f:
                traces.append(json.load(f))

    # Compute metrics
    routing_counts: dict[str, int] = {}
    confidences: list[float] = []
    latencies: list[float] = []
    mcp_calls = 0
    mcp_tool_total = 0
    hitl_triggers = 0
    abstain_count = 0
    missing_route_reason = 0
    missing_supervisor_route = 0
    source_counts = {}

    confidence_buckets = {
        "0.00-0.29": 0,
        "0.30-0.59": 0,
        "0.60-0.79": 0,
        "0.80-1.00": 0,
    }

    for t in traces:
        route = t.get("supervisor_route") or "unknown"
        routing_counts[route] = routing_counts.get(route, 0) + 1

        if route == "unknown":
            missing_supervisor_route += 1

        if not (t.get("route_reason") or "").strip():
            missing_route_reason += 1

        conf = _to_float(t.get("confidence", 0), 0.0)
        confidences.append(conf)

        if conf < 0.3:
            confidence_buckets["0.00-0.29"] += 1
        elif conf < 0.6:
            confidence_buckets["0.30-0.59"] += 1
        elif conf < 0.8:
            confidence_buckets["0.60-0.79"] += 1
        else:
            confidence_buckets["0.80-1.00"] += 1

        lat = t.get("latency_ms")
        if lat is not None:
            latencies.append(_to_float(lat, 0.0))

        tools_used = t.get("mcp_tools_used") or []
        if tools_used:
            mcp_calls += 1
            mcp_tool_total += len(tools_used)

        if t.get("hitl_triggered"):
            hitl_triggers += 1

        if _is_abstain(t.get("final_answer", "")):
            abstain_count += 1

        for src in t.get("retrieved_sources", []):
            source_counts[src] = source_counts.get(src, 0) + 1

    total = len(traces)
    top_sources = sorted(source_counts.items(), key=lambda x: -x[1])[:5]

    metrics = {
        "total_traces": total,
        "routing_distribution": {k: _fmt_rate(v, total) for k, v in routing_counts.items()},
        "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
        "confidence_buckets": confidence_buckets,
        "avg_latency_ms": round(sum(latencies) / len(latencies)) if latencies else 0,
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
        "latency_p99_ms": _percentile(latencies, 99),
        "mcp_usage_rate": _fmt_rate(mcp_calls, total),
        "mcp_tool_calls_total": mcp_tool_total,
        "hitl_rate": _fmt_rate(hitl_triggers, total),
        "abstain_rate": f"{round(100 * abstain_count / total)}%" if total else "0%",
        "trace_quality": {
            "missing_supervisor_route": missing_supervisor_route,
            "missing_route_reason": missing_route_reason,
        },
        "top_sources": top_sources,
    }

    return metrics


# ─────────────────────────────────────────────
# 4. Compare Single vs Multi Agent
# ─────────────────────────────────────────────

def compare_single_vs_multi(
    multi_traces_dir: str = TRACES_DIR,
    day08_results_file: Optional[str] = None,
) -> dict:
    """
    So sánh Day 08 (single agent RAG) vs Day 09 (multi-agent).

    TODO Sprint 4: Điền kết quả thực tế từ Day 08 vào day08_baseline.

    Returns:
        dict của comparison metrics
    """
    multi_metrics = analyze_traces(multi_traces_dir)
    day08_baseline = _load_day08_baseline(day08_results_file)

    d8_latency = _to_float(day08_baseline.get("avg_latency_ms", 0), 0.0)
    d9_latency = _to_float(multi_metrics.get("avg_latency_ms", 0), 0.0)

    d8_conf = _to_float(day08_baseline.get("avg_confidence", 0), 0.0)
    d9_conf = _to_float(multi_metrics.get("avg_confidence", 0), 0.0)

    d8_abstain = _parse_percent_str(str(day08_baseline.get("abstain_rate", "")))
    d9_abstain = _parse_percent_str(str(multi_metrics.get("abstain_rate", "")))

    if d8_latency > 0:
        latency_delta_pct = round(((d9_latency - d8_latency) / d8_latency) * 100, 1)
        latency_delta_text = (
            f"Day 09 latency: {int(round(d9_latency))}ms vs Day 08: {int(round(d8_latency))}ms "
            f"(delta: {latency_delta_pct:+.1f}%)"
        )
    else:
        latency_delta_text = "Không đủ dữ liệu Day 08 để tính latency delta"

    confidence_delta_text = f"Day 09 avg confidence: {d9_conf:.3f} vs Day 08: {d8_conf:.3f} (delta: {d9_conf - d8_conf:+.3f})"

    if d8_abstain is not None and d9_abstain is not None:
        abstain_delta_text = f"Day 09 abstain rate: {d9_abstain:.0f}% vs Day 08: {d8_abstain:.0f}% (delta: {d9_abstain - d8_abstain:+.0f}pp)"
    else:
        abstain_delta_text = "Không đủ dữ liệu abstain_rate để tính delta"

    comparison = {
        "generated_at": datetime.now().isoformat(),
        "day08_single_agent": day08_baseline,
        "day09_multi_agent": multi_metrics,
        "analysis": {
            "routing_visibility": "Day 09 có route_reason + supervisor_route cho từng câu → dễ debug hơn Day 08",
            "latency_delta": latency_delta_text,
            "accuracy_delta": confidence_delta_text,
            "abstain_delta": abstain_delta_text,
            "debuggability": "Multi-agent: có thể test từng worker độc lập. Single-agent: không thể.",
            "mcp_benefit": "Day 09 có thể extend capability qua MCP không cần sửa core. Day 08 phải hard-code.",
            "routing_quality": f"Day 09 routing distribution: {multi_metrics.get('routing_distribution', {})}",
        },
    }

    return comparison


# ─────────────────────────────────────────────
# 5. Save Eval Report
# ─────────────────────────────────────────────

def save_eval_report(comparison: dict) -> str:
    """Lưu báo cáo eval tổng kết ra file JSON."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    output_file = EVAL_REPORT_PATH
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    return output_file


# ─────────────────────────────────────────────
# 6. CLI Entry Point
# ─────────────────────────────────────────────

def print_metrics(metrics: dict):
    """Print metrics đẹp."""
    if not metrics:
        return
    print("\n📊 Trace Analysis:")
    for k, v in metrics.items():
        if isinstance(v, list):
            print(f"  {k}:")
            for item in v:
                print(f"    • {item}")
        elif isinstance(v, dict):
            print(f"  {k}:")
            for kk, vv in v.items():
                print(f"    {kk}: {vv}")
        else:
            print(f"  {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day 09 Lab — Trace Evaluation")
    parser.add_argument("--grading", action="store_true", help="Run grading questions")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing traces")
    parser.add_argument("--compare", action="store_true", help="Compare single vs multi")
    parser.add_argument("--test-file", default=DEFAULT_TEST_QUESTIONS, help="Test questions file")
    args = parser.parse_args()

    if args.grading:
        # Chạy grading questions
        log_file = run_grading_questions()
        if log_file:
            print(f"\n✅ Grading log: {log_file}")
            print("   Nộp file này trước 18:00!")

    elif args.analyze:
        # Phân tích traces
        metrics = analyze_traces()
        print_metrics(metrics)

    elif args.compare:
        # So sánh single vs multi
        comparison = compare_single_vs_multi()
        report_file = save_eval_report(comparison)
        print(f"\n📊 Comparison report saved → {report_file}")
        print("\n=== Day 08 vs Day 09 ===")
        for k, v in comparison.get("analysis", {}).items():
            print(f"  {k}: {v}")

    else:
        # Default: chạy test questions
        results = run_test_questions(args.test_file)

        # Phân tích trace
        metrics = analyze_traces()
        print_metrics(metrics)

        # Lưu báo cáo
        comparison = compare_single_vs_multi()
        report_file = save_eval_report(comparison)
        print(f"\n📄 Eval report → {report_file}")
        print("\n✅ Sprint 4 complete!")
        print("   Next: Điền docs/ templates và viết reports/")
