from pathlib import Path
import sqlite3
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "support_tickets.csv"
DB_PATH = BASE_DIR / "tickets.db"

COLUMNS = [
    "ticket_id", "created_at", "category", "priority", "status",
    "response_time_hrs", "resolution_time_hrs", "agent_id",
    "customer_rating", "issue_summary"
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    missing = [c for c in COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df = df[COLUMNS].copy()
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    if df["created_at"].isna().any():
        raise ValueError("Invalid created_at values found in dataset")
    conn = get_connection()
    df.to_sql("support_tickets", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON support_tickets(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_priority ON support_tickets(priority)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON support_tickets(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_agent ON support_tickets(agent_id)")
    conn.commit()
    conn.close()
    return len(df)


def query(sql: str, params=()):
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        return rows
    finally:
        conn.close()
