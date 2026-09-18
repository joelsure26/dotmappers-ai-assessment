from typing import Any
from .database import query

ALLOWED_FILTERS = {"status", "priority", "category"}


def _where(filters: dict[str, Any]):
    filters = filters or {}
    clauses, params = [], []
    for key, value in filters.items():
        if key in ALLOWED_FILTERS and value:
            clauses.append(f"{key} = ?")
            params.append(value)
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def execute(intent: dict[str, Any]):
    name = intent.get("intent")
    filters = intent.get("filters") or {}

    if name == "count":
        where, params = _where(filters)
        rows = query(f"SELECT COUNT(*) AS count FROM support_tickets{where}", params)
        return {"type": "count", "data": rows[0]}

    if name == "agent_resolved_most":
        rows = query("""
            SELECT agent_id, COUNT(*) AS resolved_tickets
            FROM support_tickets WHERE status = 'Resolved'
            GROUP BY agent_id ORDER BY resolved_tickets DESC LIMIT 1
        """)
        return {"type": "table", "data": rows}

    if name == "agent_lowest_rating":
        rows = query("""
            SELECT agent_id, ROUND(AVG(customer_rating), 2) AS average_rating,
                   COUNT(customer_rating) AS rated_tickets
            FROM support_tickets WHERE customer_rating IS NOT NULL
            GROUP BY agent_id ORDER BY average_rating ASC LIMIT 1
        """)
        return {"type": "table", "data": rows}

    if name == "average_rating":
        category = filters.get("category")
        if category:
            rows = query("SELECT ROUND(AVG(customer_rating), 2) AS average_rating FROM support_tickets WHERE category = ? AND customer_rating IS NOT NULL", (category,))
        else:
            rows = query("SELECT ROUND(AVG(customer_rating), 2) AS average_rating FROM support_tickets WHERE customer_rating IS NOT NULL")
        return {"type": "count", "data": rows[0]}

    if name == "critical_not_resolved_within":
        hours = float(intent.get("hours") or 12)
        rows = query("""
            SELECT ticket_id, created_at, priority, status, resolution_time_hrs, agent_id, issue_summary
            FROM support_tickets
            WHERE priority = 'Critical'
              AND (status != 'Resolved' OR resolution_time_hrs > ?)
            ORDER BY resolution_time_hrs DESC
        """, (hours,))
        return {"type": "table", "data": rows, "meta": {"hours": hours}}

    if name == "unresolved_high_priority_older_than":
        hours = float(intent.get("hours") or 24)
        rows = query("""
            SELECT ticket_id, created_at, priority, status, agent_id, issue_summary
            FROM support_tickets
            WHERE priority IN ('High', 'Critical') AND status != 'Resolved'
              AND (julianday('now') - julianday(created_at)) * 24 > ?
            ORDER BY created_at ASC
        """, (hours,))
        return {"type": "table", "data": rows, "meta": {"hours": hours}}

    if name == "anomalies":
        # IQR anomaly detection for resolved tickets plus the explicit business rule.
        stats = query("""
            SELECT COUNT(*) AS n,
                   AVG(resolution_time_hrs) AS mean,
                   AVG(resolution_time_hrs * resolution_time_hrs) AS mean_sq
            FROM support_tickets WHERE resolution_time_hrs IS NOT NULL
        """)[0]
        rows = query("""
            WITH ranked AS (
                SELECT *,
                       ROW_NUMBER() OVER (ORDER BY resolution_time_hrs) AS rn,
                       COUNT(*) OVER () AS total
                FROM support_tickets WHERE resolution_time_hrs IS NOT NULL
            )
            SELECT ticket_id, created_at, priority, status, resolution_time_hrs, agent_id, issue_summary
            FROM ranked
            WHERE resolution_time_hrs >= (
                SELECT AVG(resolution_time_hrs) + 2.0 * (
                    AVG(resolution_time_hrs * resolution_time_hrs) - AVG(resolution_time_hrs) * AVG(resolution_time_hrs)
                )
                FROM support_tickets WHERE resolution_time_hrs IS NOT NULL
            )
            ORDER BY resolution_time_hrs DESC
        """)
        explicit = query("""
            SELECT ticket_id, created_at, priority, status, response_time_hrs, agent_id, issue_summary
            FROM support_tickets
            WHERE priority IN ('High','Critical') AND status != 'Resolved'
              AND (julianday('now') - julianday(created_at)) * 24 > 24
            ORDER BY created_at ASC
        """)
        return {"type": "anomalies", "data": {"long_resolution": rows, "old_high_priority_unresolved": explicit}}

    if name == "list_tickets":
        where, params = _where(filters)
        rows = query(f"SELECT * FROM support_tickets{where} ORDER BY created_at DESC LIMIT 100", params)
        return {"type": "table", "data": rows}

    raise ValueError(f"Unsupported intent: {name}")
