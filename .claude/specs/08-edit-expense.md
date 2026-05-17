# Spec: Edit Expense

## Overview
Step 8 replaces the `/expenses/<id>/edit` stub with a working edit flow. A
logged-in user can click an "Edit" button on any of their own expenses from the
profile page, update any field (amount, category, date, description), and save
the change. A `GET` request renders the form pre-filled with the existing
expense data; a `POST` request validates the input, updates the row in the
`expenses` table, and redirects back to `/profile` on success. The route must
verify that the expense belongs to the current user before allowing any access
or modification.

## Depends on
- Step 1: Database setup — the `expenses` table must exist.
- Step 3: Login / logout — `session["user_id"]` must be set for the auth guard.
- Step 5: Backend routes for profile page — `get_recent_transactions` must
  return expense rows with an `id` field so edit links can be generated.
- Step 7: Add expense — establishes the `create_expense` helper pattern that
  this step follows for `update_expense`.

## Routes
- `GET  /expenses/<int:id>/edit` — render edit form pre-filled with expense data — logged-in only
- `POST /expenses/<int:id>/edit` — validate and update the expense, redirect to `/profile` — logged-in only

## Database changes
No new tables or columns.

Two new helper functions must be added to `database/db.py`:

```python
def get_expense_by_id(expense_id):
    # Returns a single expense row (sqlite3.Row) or None

def update_expense(expense_id, amount, category, date, description):
    # Updates amount, category, date, description for the given expense_id and commits
```

## Templates
- **Create:** `templates/edit_expense.html`
  - Extends `base.html` via `{% block content %}`
  - Contains a single `<form method="POST">` pre-filled with existing values
  - Same fields as `add_expense.html`: `amount`, `category`, `date`, `description`
  - Displays a validation error message when the template receives an `error` variable
  - On validation failure the form re-populates with the values the user typed
  - Uses `url_for("edit_expense", id=expense.id)` in the `action` attribute
  - Styling via `static/css/style.css` only; no new CSS file is needed

- **Modify:** `templates/profile.html`
  - Add an "Edit" link/button on each row in the Recent Transactions list
  - Link target: `url_for("edit_expense", id=transaction.id)`
  - Button must only render when `transaction.id` is available

## Files to change
- `app.py`
  - Replace the `edit_expense` stub with a full implementation:
    - Add `methods=["GET", "POST"]` to the `@app.route` decorator
    - Add a login guard: redirect to `/login` if `session.get("user_id")` is falsy
    - Fetch the expense with `get_expense_by_id(id)`; return 404 if not found
    - Verify `expense["user_id"] == session["user_id"]`; return 403 if not
    - On `GET`: render `edit_expense.html` with the expense and categories
    - On `POST`:
      1. Read `amount`, `category`, `date`, `description` from `request.form`
      2. Validate: same rules as `add_expense` (positive float, valid category, valid date)
      3. On failure: re-render the form with `error` and submitted values
      4. On success: call `update_expense(...)`, then `redirect(url_for("profile"))`
  - Import `get_expense_by_id` and `update_expense` from `database.db`

- `database/db.py`
  - Add `get_expense_by_id(expense_id)` function
  - Add `update_expense(expense_id, amount, category, date, description)` function

- `templates/profile.html`
  - Add "Edit" link on each transaction row pointing to the edit route

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — `?` placeholders in every SQL statement
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values in any template or stylesheet
- All templates extend `base.html`
- Ownership check is mandatory: verify `expense["user_id"] == session["user_id"]`
  before rendering or processing the form; return 403 otherwise
- Use `abort(404)` / `abort(403)` from Flask for error responses
- The same seven `EXPENSE_CATEGORIES` constant from `app.py` must be passed to
  the template; do not hardcode categories in the template
- `amount` must be cast to `float`; reject on `ValueError`
- `date` must be validated with `datetime.strptime(value, "%Y-%m-%d")`; reject on `ValueError`
- `description` is optional — treat an empty string as `None` when updating

## Definition of done
- [ ] `GET /expenses/<id>/edit` returns 200 and renders the edit form pre-filled
  with the expense's existing values for a logged-in owner
- [ ] `GET /expenses/<id>/edit` redirects to `/login` for an unauthenticated visitor
- [ ] `GET /expenses/<id>/edit` returns 403 when the expense belongs to a
  different user
- [ ] `GET /expenses/<id>/edit` returns 404 for a non-existent expense id
- [ ] Submitting a valid form updates the row in `expenses` and redirects to `/profile`
- [ ] The updated values are reflected in the Recent Transactions list on `/profile`
- [ ] Submitting with `amount` left blank or set to `0` shows a validation error
  and does not update the row
- [ ] Submitting with a category not in the allowed list shows a validation error
- [ ] Submitting with a malformed date shows a validation error
- [ ] On validation failure the form re-displays with the submitted values pre-filled
- [ ] Each transaction row on `/profile` has an "Edit" link pointing to the correct
  edit URL
- [ ] `pytest` passes with no errors after implementation
