# Spec: Analytics

## Overview
Step 10 replaces the "Coming Soon" placeholder on `/analytics` with a real
analytics page. It gives a logged-in user insight into their spending beyond the
profile summary: a month-by-month spending trend for the last 6 months, a
category breakdown with bars, the user's top 5 largest expenses, and headline
figures (total spent, average per day, average per transaction, change versus
the previous equivalent period). The page honours the same `date_from` /
`date_to` query-string filter and presets as the profile page. Charts are built
with plain HTML/CSS bars — no JavaScript chart libraries. This is the final
step on the roadmap and only reads existing data.

## Depends on
- Step 1: Database setup (`expenses` table)
- Step 3: Login / logout (`session["user_id"]` auth guard)
- Step 5: Backend connection (`database/queries.py` helpers, incl.
  `get_category_breakdown`)
- Step 6: Date filter (validation and preset logic in `profile()`)
- Steps 7–9: Add / edit / delete expense (so there is data to analyse)

## Routes
- `GET /analytics` — render the analytics page, optionally filtered by
  `date_from` and `date_to` query params (`YYYY-MM-DD`) — logged-in only
  (unauthenticated users are redirected to `/login`; route already exists as a
  stub)

## Database changes
No database changes. All figures are derived from the existing `expenses`
table (`amount`, `category`, `date`, `user_id`).

New read-only helpers must be added to `database/queries.py` (no schema change):

```python
def get_monthly_totals(user_id, months=6):
    # list of {"month": "YYYY-MM", "label": "Apr 2026", "total": float}
    # exactly `months` entries ending with the current month, oldest first;
    # months with no expenses have total 0

def get_top_expenses(user_id, limit=5, date_from=None, date_to=None):
    # list of {"id", "date", "description", "category", "amount"},
    # ordered by amount DESC, then date DESC

def get_analytics_summary(user_id, date_from=None, date_to=None):
    # {"total_spent", "transaction_count", "avg_per_transaction",
    #  "avg_per_day", "previous_total", "change_pct"}
    # previous_total / change_pct are None when no date range is active or the
    # previous period total is 0
```

## Templates
- **Modify:** `templates/analytics.html`
  - Remove the "Coming Soon" card, blobs, dots and inline SVG with hardcoded
    hex fill
  - Add, in order: filter bar (same presets as profile), headline stat cards,
    6-month trend bars, category breakdown bars, top 5 expenses table
  - Empty state when the user has no expenses in range
- **Modify:** `templates/base.html` — only if the navbar has no link to
  Analytics; add one using `url_for("analytics")`

## Files to change
- `app.py` — `analytics()` view: read/validate `date_from` / `date_to`, build
  presets, call the query helpers, pass data to the template
- `database/queries.py` — add the three helpers above
- `templates/analytics.html` — see Templates
- `static/css/analytics.css` — replace placeholder styles (if currently in
  another stylesheet, remove the "coming soon" rules)
- `CLAUDE.md` — add step 10 to the roadmap and new files to the structure

## Files to create
- `tests/test_analytics.py`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never format values into SQL
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values (this includes SVG attributes)
- All templates extend `base.html`
- Every query is scoped with `WHERE user_id = ?` using `session["user_id"]`;
  never trust a user id from the request
- Routes in `app.py` contain no SQL; read-only queries live in
  `database/queries.py`
- Date validation and preset calculation reuse the logic from `profile()`.
  Extract it into a shared helper in `app.py` instead of copy-pasting; the
  profile behaviour must not change
- Invalid or reversed date ranges fall back to unfiltered and flash
  "Start date must be before end date." for the reversed case
- Bar widths come from computed percentages passed by the view (set via a CSS
  custom property on the element), not hardcoded values; no inline hex colours
- Currency symbol is ₹ everywhere
- `url_for()` for all links, including presets
- Vanilla CSS only; no JS charting libraries

## Definition of done
- [ ] Visiting `/analytics` while logged out redirects to `/login`
- [ ] Visiting `/analytics` while logged in shows the analytics page, not the
  "Coming Soon" placeholder
- [ ] Headline cards show total spent, average per day, average per
  transaction, and (when a range is active) % change versus the previous
  period of equal length
- [ ] The 6-month trend shows exactly 6 bars ending in the current month, with
  zero-spend months shown as empty bars
- [ ] The category breakdown matches the profile page for the same filter
- [ ] The top 5 expenses are the user's largest in range, highest first
- [ ] All filter presets and a custom range update every section
- [ ] A reversed range flashes an error and falls back to unfiltered; a
  malformed date does not crash the page
- [ ] A user with no expenses in range sees ₹0.00 and an empty-state message,
  with no errors
- [ ] One user never sees another user's data on the page
- [ ] The profile page's date filter behaves exactly as before
- [ ] No hardcoded hex values in the template or CSS, and `pytest tests/` passes
