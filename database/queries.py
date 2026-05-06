from datetime import datetime

from database.db import get_db

def get_user_by_id(user_id):
    row = get_db().execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    if row is None:
        return None
    try:
        member_since = datetime.strptime(row["created_at"][:10], "%Y-%m-%d").strftime("%B %Y")
    except (ValueError, TypeError):
        member_since = row["created_at"]
    return {"name": row["name"], "email": row["email"], "member_since": member_since}

def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    use_date = date_from and date_to
    date_clause = " AND date BETWEEN ? AND ?" if use_date else ""
    params = [user_id] + ([date_from, date_to] if use_date else []) + [limit]
    rows = get_db().execute(
        'SELECT date, description, category, amount FROM expenses '
        'WHERE user_id = ?' + date_clause + ' ORDER BY date DESC LIMIT ?',
        params
    ).fetchall()
    return [dict(r) for r in rows]

def get_summary_stats(user_id, date_from=None, date_to=None):
    db = get_db()
    use_date = date_from and date_to
    date_clause = " AND date BETWEEN ? AND ?" if use_date else ""
    params = (user_id, date_from, date_to) if use_date else (user_id,)
    row = db.execute(
        'SELECT COALESCE(SUM(amount), 0) AS total_spent, COUNT(*) AS transaction_count '
        'FROM expenses WHERE user_id = ?' + date_clause,
        params
    ).fetchone()
    top = db.execute(
        'SELECT category FROM expenses WHERE user_id = ?' + date_clause +
        ' GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1',
        params
    ).fetchone()
    return {
        "total_spent": row["total_spent"],
        "transaction_count": row["transaction_count"],
        "top_category": top["category"] if top else "—",
    }

def get_category_breakdown(user_id, date_from=None, date_to=None):
    use_date = date_from and date_to
    date_clause = " AND date BETWEEN ? AND ?" if use_date else ""
    params = (user_id, date_from, date_to) if use_date else (user_id,)
    rows = get_db().execute(
        'SELECT category AS name, SUM(amount) AS total '
        'FROM expenses WHERE user_id = ?' + date_clause +
        ' GROUP BY category ORDER BY total DESC',
        params
    ).fetchall()
    if not rows:
        return []
    grand_total = sum(r["total"] for r in rows)
    result = []
    allocated = 0
    for i, r in enumerate(rows):
        if i < len(rows) - 1:
            pct = round(r["total"] / grand_total * 100)
            allocated += pct
        else:
            pct = 100 - allocated
        result.append({"name": r["name"], "total": r["total"], "percentage": pct})
    return result
