import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).with_name("spendly.db")


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = [
        row["name"]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]

    print(f"Database: {DB_PATH}")
    print("Tables:")
    for table in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"- {table} ({count} rows)")

        rows = cur.execute(f"SELECT * FROM {table} LIMIT 5").fetchall()
        for row in rows:
            print(f"  {dict(row)}")
        if not rows:
            print("  <empty>")

    conn.close()


if __name__ == "__main__":
    main()
