import datetime as dt
from datetime import datetime

from database.db import get_db


def get_user_by_id(user_id):
    row = get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    try:
        member_since = datetime.strptime(row["created_at"][:10], "%Y-%m-%d").strftime(
            "%B %Y"
        )
    except (ValueError, TypeError):
        member_since = row["created_at"]
    return {"name": row["name"], "email": row["email"], "member_since": member_since}


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    use_date = date_from and date_to
    date_clause = " AND date BETWEEN ? AND ?" if use_date else ""
    params = [user_id] + ([date_from, date_to] if use_date else []) + [limit]
    rows = (
        get_db()
        .execute(
            "SELECT id, date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + date_clause + " ORDER BY date DESC LIMIT ?",
            params,
        )
        .fetchall()
    )
    return [dict(r) for r in rows]


def get_summary_stats(user_id, date_from=None, date_to=None):
    db = get_db()
    use_date = date_from and date_to
    date_clause = " AND date BETWEEN ? AND ?" if use_date else ""
    params = (user_id, date_from, date_to) if use_date else (user_id,)
    row = db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total_spent, COUNT(*) AS transaction_count "
        "FROM expenses WHERE user_id = ?" + date_clause,
        params,
    ).fetchone()
    top = db.execute(
        "SELECT category FROM expenses WHERE user_id = ?"
        + date_clause
        + " GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        params,
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
    rows = (
        get_db()
        .execute(
            "SELECT category AS name, SUM(amount) AS total "
            "FROM expenses WHERE user_id = ?"
            + date_clause
            + " GROUP BY category ORDER BY total DESC",
            params,
        )
        .fetchall()
    )
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


def get_monthly_totals(user_id, months=6):
    today = dt.date.today()
    year, month = today.year, today.month
    keys = []
    for _ in range(months):
        keys.append((year, month))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    keys.reverse()
    start = dt.date(keys[0][0], keys[0][1], 1).isoformat()
    rows = (
        get_db()
        .execute(
            "SELECT strftime('%Y-%m', date) AS month, SUM(amount) AS total "
            "FROM expenses WHERE user_id = ? AND date >= ? GROUP BY month",
            (user_id, start),
        )
        .fetchall()
    )
    totals = {r["month"]: r["total"] for r in rows}
    result = []
    for y, m in keys:
        key = f"{y:04d}-{m:02d}"
        label = dt.date(y, m, 1).strftime("%b %Y")
        result.append({"month": key, "label": label, "total": totals.get(key, 0)})
    return result


def get_top_expenses(user_id, limit=5, date_from=None, date_to=None):
    use_date = date_from and date_to
    date_clause = " AND date BETWEEN ? AND ?" if use_date else ""
    params = [user_id] + ([date_from, date_to] if use_date else []) + [limit]
    rows = (
        get_db()
        .execute(
            "SELECT id, date, description, category, amount FROM expenses "
            "WHERE user_id = ?" + date_clause + " ORDER BY amount DESC, date DESC LIMIT ?",
            params,
        )
        .fetchall()
    )
    return [dict(r) for r in rows]


def _period_total(db, user_id, date_from, date_to):
    return db.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses "
        "WHERE user_id = ? AND date BETWEEN ? AND ?",
        (user_id, date_from, date_to),
    ).fetchone()[0]


def get_analytics_summary(user_id, date_from=None, date_to=None):
    db = get_db()
    use_date = date_from and date_to
    date_clause = " AND date BETWEEN ? AND ?" if use_date else ""
    params = (user_id, date_from, date_to) if use_date else (user_id,)
    row = db.execute(
        "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt, MIN(date) AS first "
        "FROM expenses WHERE user_id = ?" + date_clause,
        params,
    ).fetchone()
    total, count = row["total"], row["cnt"]

    previous_total = change_pct = None
    if use_date:
        start = dt.date.fromisoformat(date_from)
        end = dt.date.fromisoformat(date_to)
        days = (end - start).days + 1
        prev_end = start - dt.timedelta(days=1)
        prev_start = prev_end - dt.timedelta(days=days - 1)
        previous_total = _period_total(
            db, user_id, prev_start.isoformat(), prev_end.isoformat()
        )
        if previous_total > 0:
            change_pct = round((total - previous_total) / previous_total * 100)
    elif row["first"]:
        first = dt.date.fromisoformat(row["first"])
        days = max((dt.date.today() - first).days + 1, 1)
    else:
        days = 1

    return {
        "total_spent": total,
        "transaction_count": count,
        "avg_per_transaction": total / count if count else 0,
        "avg_per_day": total / days,
        "previous_total": previous_total,
        "change_pct": change_pct,
    }
