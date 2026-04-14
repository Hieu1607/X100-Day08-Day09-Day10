"""
mcp_server.py — Mock MCP Server
Sprint 3: Implement ít nhất 2 MCP tools.

Mô phỏng MCP (Model Context Protocol) interface trong Python.
Agent (MCP client) gọi dispatch_tool() thay vì hard-code từng API.

Tools available:
    1. search_kb(query, top_k)           → tìm kiếm Knowledge Base
    2. get_ticket_info(ticket_id)        → tra cứu thông tin ticket (mock data)
    3. check_access_permission(level, requester_role)  → kiểm tra quyền truy cập
    4. create_ticket(priority, title, description)     → tạo ticket mới (mock)

Sử dụng:
    from mcp_server import dispatch_tool, list_tools

    # Discover available tools
    tools = list_tools()

    # Call a tool
    result = dispatch_tool("search_kb", {"query": "SLA P1", "top_k": 3})

Sprint 3 TODO:
    - Option Standard: Sử dụng file này as-is (mock class) — complete.
    - Option Advanced: Có thể thay dispatch_tool() bằng HTTP hoặc `mcp` library client/server.

Chạy thử:
    python mcp_server.py
"""

import os
from importlib.util import find_spec
from datetime import datetime
from typing import Any, Dict


# ─────────────────────────────────────────────
# Tool Definitions (Schema Discovery)
# Giống với cách MCP server expose tool list cho client
# ─────────────────────────────────────────────

TOOL_SCHEMAS = {
    "search_kb": {
        "name": "search_kb",
        "description": "Tìm kiếm Knowledge Base nội bộ bằng semantic search. Trả về top-k chunks liên quan nhất.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Câu hỏi hoặc keyword cần tìm"},
                "top_k": {"type": "integer", "description": "Số chunks cần trả về", "default": 3},
            },
            "required": ["query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "chunks": {"type": "array"},
                "sources": {"type": "array"},
                "total_found": {"type": "integer"},
            },
        },
    },
    "get_ticket_info": {
        "name": "get_ticket_info",
        "description": "Tra cứu thông tin ticket từ hệ thống Jira nội bộ.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "ID ticket (VD: IT-1234, P1-LATEST)"},
            },
            "required": ["ticket_id"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "priority": {"type": "string"},
                "status": {"type": "string"},
                "assignee": {"type": "string"},
                "created_at": {"type": "string"},
                "sla_deadline": {"type": "string"},
            },
        },
    },
    "check_access_permission": {
        "name": "check_access_permission",
        "description": "Kiểm tra điều kiện cấp quyền truy cập theo Access Control SOP.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "access_level": {"type": "integer", "description": "Level cần cấp (1, 2, hoặc 3)"},
                "requester_role": {"type": "string", "description": "Vai trò của người yêu cầu"},
                "is_emergency": {"type": "boolean", "description": "Có phải khẩn cấp không", "default": False},
            },
            "required": ["access_level", "requester_role"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "can_grant": {"type": "boolean"},
                "required_approvers": {"type": "array"},
                "emergency_override": {"type": "boolean"},
                "source": {"type": "string"},
            },
        },
    },
    "create_ticket": {
        "name": "create_ticket",
        "description": "Tạo ticket mới trong hệ thống Jira (MOCK — không tạo thật trong lab).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["priority", "title"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "url": {"type": "string"},
                "created_at": {"type": "string"},
            },
        },
    },
}


# ─────────────────────────────────────────────
# Tool Implementations
# ─────────────────────────────────────────────

def tool_search_kb(query: str, top_k: int = 3) -> dict:
    """
    Tìm kiếm Knowledge Base bằng semantic search.

    Ưu tiên retrieval worker/ChromaDB. Nếu index chưa có hoặc dependency lỗi,
    fallback sang lexical search trên data/docs để MCP tool vẫn trả evidence thật.
    """
    top_k = _coerce_top_k(top_k)

    if find_spec("chromadb") is None:
        chroma_error = "ChromaDB is not installed."
    else:
        try:
            # Tái dùng retrieval logic từ workers/retrieval.py
            import sys
            sys.path.insert(0, os.path.dirname(__file__))
            from workers.retrieval import retrieve_dense
            chunks = retrieve_dense(query, top_k=top_k)
            if chunks:
                return _format_kb_result(chunks)
        except Exception as e:
            chroma_error = str(e)
        else:
            chroma_error = "ChromaDB returned no chunks."

    chunks = _lexical_search_docs(query, top_k=top_k)
    result = _format_kb_result(chunks)
    result["fallback_used"] = "lexical_docs"
    result["fallback_reason"] = chroma_error
    return result


def _coerce_top_k(top_k: Any) -> int:
    try:
        return max(1, min(10, int(top_k)))
    except (TypeError, ValueError):
        return 3


def _format_kb_result(chunks: list) -> dict:
    sources = list(dict.fromkeys(c.get("source", "unknown") for c in chunks))
    return {
        "chunks": chunks,
        "sources": sources,
        "total_found": len(chunks),
    }


def _lexical_search_docs(query: str, top_k: int = 3) -> list:
    docs_dir = os.path.join(os.path.dirname(__file__), "data", "docs")
    if not os.path.isdir(docs_dir):
        return []

    query_terms = {
        token.lower()
        for token in query.replace("/", " ").replace("-", " ").split()
        if len(token) >= 2
    }

    scored_chunks = []
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(docs_dir, fname)
        with open(path, encoding="utf-8") as f:
            text = f.read().strip()

        lower_text = text.lower()
        score_hits = sum(1 for term in query_terms if term in lower_text)
        keyword_boost = 0
        for keyword in ("p1", "sla", "refund", "hoàn tiền", "flash sale", "access", "level"):
            if keyword in query.lower() and keyword in lower_text:
                keyword_boost += 2

        score = score_hits + keyword_boost
        if score == 0:
            continue

        excerpt = text[:1200]
        scored_chunks.append(
            {
                "text": excerpt,
                "source": fname,
                "score": round(min(0.95, 0.45 + score * 0.05), 4),
                "metadata": {
                    "retrieval": "lexical_fallback",
                    "matched_terms": score_hits,
                },
            }
        )

    scored_chunks.sort(key=lambda c: c["score"], reverse=True)
    return scored_chunks[:top_k]


# Mock ticket database
MOCK_TICKETS = {
    "P1-LATEST": {
        "ticket_id": "IT-9847",
        "priority": "P1",
        "title": "API Gateway down — toàn bộ người dùng không đăng nhập được",
        "status": "in_progress",
        "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True,
        "escalated_to": "senior_engineer_team",
        "notifications_sent": ["slack:#incident-p1", "email:incident@company.internal", "pagerduty:oncall"],
    },
    "IT-9847": {
        "ticket_id": "IT-9847",
        "priority": "P1",
        "title": "API Gateway down — toàn bộ người dùng không đăng nhập được",
        "status": "in_progress",
        "assignee": "nguyen.van.a@company.internal",
        "created_at": "2026-04-13T22:47:00",
        "sla_deadline": "2026-04-14T02:47:00",
        "escalated": True,
        "escalated_to": "senior_engineer_team",
        "notifications_sent": ["slack:#incident-p1", "email:incident@company.internal", "pagerduty:oncall"],
    },
    "IT-1234": {
        "ticket_id": "IT-1234",
        "priority": "P2",
        "title": "Feature login chậm cho một số user",
        "status": "open",
        "assignee": None,
        "created_at": "2026-04-13T09:15:00",
        "sla_deadline": "2026-04-14T09:15:00",
        "escalated": False,
    },
}


def tool_get_ticket_info(ticket_id: str) -> dict:
    """
    Tra cứu thông tin ticket (mock data).
    """
    if not ticket_id:
        return {"error": "ticket_id is required."}

    ticket = MOCK_TICKETS.get(ticket_id.upper())
    if ticket:
        return ticket
    # Không tìm thấy
    return {
        "error": f"Ticket '{ticket_id}' không tìm thấy trong hệ thống.",
        "available_mock_ids": list(MOCK_TICKETS.keys()),
    }


# Mock access control rules
ACCESS_RULES = {
    1: {
        "required_approvers": ["Line Manager"],
        "emergency_can_bypass": False,
        "note": "Standard user access",
    },
    2: {
        "required_approvers": ["Line Manager", "IT Admin"],
        "emergency_can_bypass": True,
        "emergency_bypass_note": "Level 2 có thể cấp tạm thời với approval đồng thời của Line Manager và IT Admin on-call.",
        "note": "Elevated access",
    },
    3: {
        "required_approvers": ["Line Manager", "IT Admin", "IT Security"],
        "emergency_can_bypass": False,
        "note": "Admin access — không có emergency bypass",
    },
}


def tool_check_access_permission(access_level: int, requester_role: str, is_emergency: bool = False) -> dict:
    """
    Kiểm tra điều kiện cấp quyền theo Access Control SOP.
    """
    try:
        access_level = int(access_level)
    except (TypeError, ValueError):
        return {"error": f"Access level '{access_level}' không hợp lệ. Levels: 1, 2, 3."}

    rule = ACCESS_RULES.get(access_level)
    if not rule:
        return {"error": f"Access level {access_level} không hợp lệ. Levels: 1, 2, 3."}

    can_grant = True
    notes = []

    if is_emergency and rule.get("emergency_can_bypass"):
        notes.append(rule.get("emergency_bypass_note", ""))
        can_grant = True
    elif is_emergency and not rule.get("emergency_can_bypass"):
        notes.append(f"Level {access_level} KHÔNG có emergency bypass. Phải follow quy trình chuẩn.")

    return {
        "access_level": access_level,
        "can_grant": can_grant,
        "required_approvers": rule["required_approvers"],
        "approver_count": len(rule["required_approvers"]),
        "requester_role": requester_role,
        "emergency_override": bool(is_emergency and rule.get("emergency_can_bypass", False)),
        "notes": notes,
        "source": "access_control_sop.txt",
    }


def tool_create_ticket(priority: str, title: str, description: str = "") -> dict:
    """
    Tạo ticket mới (MOCK — in log, không tạo thật).
    """
    priority = (priority or "").upper()
    if priority not in {"P1", "P2", "P3", "P4"}:
        return {"error": "priority must be one of P1, P2, P3, P4."}
    if not title:
        return {"error": "title is required."}

    mock_id = f"IT-{9900 + sum(ord(ch) for ch in title) % 99}"
    ticket = {
        "ticket_id": mock_id,
        "priority": priority,
        "title": title,
        "description": description[:200],
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "url": f"https://jira.company.internal/browse/{mock_id}",
        "note": "MOCK ticket — không tồn tại trong hệ thống thật",
    }
    return ticket


# ─────────────────────────────────────────────
# Dispatch Layer — MCP server interface
# ─────────────────────────────────────────────

TOOL_REGISTRY = {
    "search_kb": tool_search_kb,
    "get_ticket_info": tool_get_ticket_info,
    "check_access_permission": tool_check_access_permission,
    "create_ticket": tool_create_ticket,
}


def list_tools() -> list:
    """
    MCP discovery: trả về danh sách tools có sẵn.
    Tương đương với `tools/list` trong MCP protocol.
    """
    return list(TOOL_SCHEMAS.values())


def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    """
    MCP execution: nhận tool_name và input, gọi tool tương ứng.
    Tương đương với `tools/call` trong MCP protocol.

    Args:
        tool_name: tên tool (phải có trong TOOL_REGISTRY)
        tool_input: input dict (phải match với tool's inputSchema)

    Returns:
        Tool output dict, hoặc error dict nếu thất bại
    """
    if tool_name not in TOOL_REGISTRY:
        return {
            "error": f"Tool '{tool_name}' không tồn tại. Available: {list(TOOL_REGISTRY.keys())}"
        }
    if not isinstance(tool_input, dict):
        return {"error": f"Input for tool '{tool_name}' must be a dict."}

    schema = TOOL_SCHEMAS[tool_name]["inputSchema"]
    missing_required = [
        field for field in schema.get("required", [])
        if field not in tool_input or tool_input[field] in (None, "")
    ]
    if missing_required:
        return {
            "error": f"Missing required input for tool '{tool_name}': {missing_required}",
            "schema": schema,
        }

    tool_fn = TOOL_REGISTRY[tool_name]
    try:
        result = tool_fn(**tool_input)
        return result
    except TypeError as e:
        return {
            "error": f"Invalid input for tool '{tool_name}': {e}",
            "schema": schema,
        }
    except Exception as e:
        return {
            "error": f"Tool '{tool_name}' execution failed: {e}",
        }


# ─────────────────────────────────────────────
# Test & Demo
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MCP Server — Tool Discovery & Test")
    print("=" * 60)

    # 1. Discover tools
    print("\n📋 Available Tools:")
    for tool in list_tools():
        print(f"  • {tool['name']}: {tool['description'][:60]}...")

    # 2. Test search_kb
    print("\n🔍 Test: search_kb")
    result = dispatch_tool("search_kb", {"query": "SLA P1 resolution time", "top_k": 2})
    if result.get("chunks"):
        for c in result["chunks"]:
            print(f"  [{c.get('score', '?')}] {c.get('source')}: {c.get('text', '')[:70]}...")
    else:
        print(f"  Result: {result}")

    # 3. Test get_ticket_info
    print("\n🎫 Test: get_ticket_info")
    ticket = dispatch_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
    print(f"  Ticket: {ticket.get('ticket_id')} | {ticket.get('priority')} | {ticket.get('status')}")
    if ticket.get("notifications_sent"):
        print(f"  Notifications: {ticket['notifications_sent']}")

    # 4. Test check_access_permission
    print("\n🔐 Test: check_access_permission (Level 3, emergency)")
    perm = dispatch_tool("check_access_permission", {
        "access_level": 3,
        "requester_role": "contractor",
        "is_emergency": True,
    })
    print(f"  can_grant: {perm.get('can_grant')}")
    print(f"  required_approvers: {perm.get('required_approvers')}")
    print(f"  emergency_override: {perm.get('emergency_override')}")
    print(f"  notes: {perm.get('notes')}")

    # 5. Test invalid tool
    print("\n❌ Test: invalid tool")
    err = dispatch_tool("nonexistent_tool", {})
    print(f"  Error: {err.get('error')}")

    print("\n✅ MCP server test done.")
    print("\nStandard Sprint 3 MCP mock is ready. HTTP/real MCP server remains optional for bonus +2.")
