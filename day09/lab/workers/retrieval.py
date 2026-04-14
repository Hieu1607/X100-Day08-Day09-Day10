"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - top_k (optional): số chunks cần lấy

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_logs: log input/output của worker này (append vào list)

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os

from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3

# Tên collection ChromaDB. Day 09 kế thừa index từ Day 08 (`rag_lab`),
# có thể override qua env DAY09_COLLECTION nếu rebuild.
COLLECTION_NAME = os.getenv("DAY09_COLLECTION", "rag_lab")
EMBEDDING_MODEL = "text-embedding-3-small"

# Neo path vào vị trí file để CWD nào cũng tìm đúng chroma_db của day09/lab/.
# Override bằng env CHROMA_DB_PATH nếu cần.
_LAB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", os.path.join(_LAB_ROOT, "chroma_db"))


def _get_embedding_fn():
    """
    Trả về embedding function.
    Dùng shopaikey gateway (OpenAI-compatible) để khớp model
    `text-embedding-3-small` mà Day 08 đã dùng để build collection `rag_lab`.
    Fallback random chỉ để test local khi thiếu dependency/API key.
    """
    try:
        from openai import OpenAI

        api_key = os.getenv("SHOPAIKEY_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing SHOPAIKEY_API_KEY/OPENAI_API_KEY")

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.shopaikey.com/v1",
            default_headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )

        def embed(text: str) -> list:
            resp = client.embeddings.create(input=text, model=EMBEDDING_MODEL)
            return resp.data[0].embedding

        return embed
    except Exception as e:
        print(f"⚠️  Embedding via shopaikey failed: {e}")

    # Fallback: random embeddings cho test (KHÔNG dùng production)
    import random

    def embed(text: str) -> list:
        return [random.random() for _ in range(384)]

    print("⚠️  WARNING: Using random embeddings (test only).")
    return embed


def _get_collection():
    """
    Kết nối ChromaDB collection.
    Sprint 2: dùng collection `rag_lab` kế thừa từ Day 08 (đã có 30 chunks).
    Override bằng env DAY09_COLLECTION nếu rebuild riêng cho Day 09.
    """
    import chromadb

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    try:
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        collection = client.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        print(
            f"⚠️  Collection '{COLLECTION_NAME}' chưa có data. "
            "Chạy index script trong README trước (hoặc copy chroma_db từ Day 08)."
        )
    return collection


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → trả về top_k chunks.

    Returns:
        list of {"text": str, "source": str, "score": float, "metadata": dict}
    """
    top_k = max(1, int(top_k or DEFAULT_TOP_K))

    embed = _get_embedding_fn()
    query_embedding = embed(query)

    try:
        collection = _get_collection()
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"],
        )

        chunks = []
        for doc, dist, meta in zip(
            results["documents"][0],
            results["distances"][0],
            results["metadatas"][0],
        ):
            meta = meta or {}
            score = float(max(0.0, min(1.0, 1 - float(dist))))
            chunks.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "score": round(score, 4),
                    "metadata": meta,
                }
            )
        return chunks

    except Exception as e:
        print(f"⚠️  ChromaDB query failed: {e}")
        # Fallback: return empty (abstain)
        return []


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    # Ưu tiên key theo contract (`top_k`), giữ backward compatibility.
    top_k = state.get("top_k", state.get("retrieval_top_k", DEFAULT_TOP_K))

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)
        sources = list(dict.fromkeys(c["source"] for c in chunks))

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n▶ Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            print(f"    [{c['score']:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")
