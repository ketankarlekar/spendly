# Spec: Delete Expense

## Overview
Step 9 replaces the `/expenses/<id>/delete` stub with a working delete flow.
A logged-in user can click a "Delete" button on any of their own expenses from
the profile page. A browser `confirm()` dialog asks for confirmation before the
form is submitted; if confirmed, a `POST` request is sent to the delete route,
which verifies ownership, removes the row from the `expenses` table, and
redirects back to `/profile`. Because HTML forms cannot send `DELETE` requests,
the route uses `POST` to avoid accidental deletion via `GET` (e.g. link
pre-fetching). The route must verify the expense belongs to the current user
before deleting.

## Depends on
- Step 1: Database setup — the `expenses` table must exist.
- Step 3: Login / logout — `session["user_id"]` must be set for the auth guard.
- Step 5: Backend routes for profile page — `get_recent_transactions` must
  return expense rows with an `id` field so delete buttons can be generated.
- Step 8: Edit expense — establishes `get_expense_by_id` which this step reuses
  for the ownership check.

## Routes
- `POST /expenses/<int:id>/delete` — verify ownership, delete the expense, redirect to `/profile` — logged-in only

The existing `GET /expenses/<int:id>/delete` stub in `app.py` must be replaced
with this `POST`-only route (change `methods` to `["POST"]`).

## Database changes
No new tables or columns.

One new helper function must be added to `database/db.py`:

```python
def delete_expense(expense_id):
    # Deletes the expense row with the given id and commits
```

## Templates
- **Create:** none

- **Modify:** `templates/profile.html`
  - Add a "Delete" button on each row in the Recent Transactions list, alongside
    the existing "Edit" link
  - The button must be inside a `<form method="POST">` whose `action` attribute
    uses `url_for("delete_expense", id=transaction.id)`
  - Add an `onsubmit` handler on the form that calls `confirm()` and cancels
    submission if the user clicks Cancel:
    `onsubmit="return confirm('Delete this expense?');"`
  - The submit button should be styled to look like a danger/destructive action
    (use a CSS variable for the colour — never hardcode hex)
  - Button must only render when `transaction.id` is available

## Files to change
- `app.py`
  - Replace the `delete_expense` stub with a full implementation:
    - Change `methods` on the `@app.route` decorator to `["POST"]`
    - Add a login guard: redirect to `/login` if `session.get("user_id")` is falsy
    - Fetch the expense with `get_expense_by_id(id)`; return 404 if not found
    - Verify `expense["user_id"] == session["user_id"]`; return 403 if not
    - Call `delete_expense(id)`, then `redirect(url_for("profile"))`
  - Import `delete_expense` from `database.db`

- `database/db.py`
  - Add `delete_expense(expense_id)` function

- `templates/profile.html`
  - Add "Delete" form/button on each transaction row

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — `?` placeholders in every SQL statement
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values in any template or stylesheet
- All templates extend `base.html`
- Use `POST` for the delete route — never `GET` (prevents CSRF via link pre-fetch)
- Ownership check is mandatory: verify `expense["user_id"] == session["user_id"]`
  before deleting; return 403 otherwise
- Use `abort(404)` / `abort(403)` from Flask for error responses
- Use `confirm()` in vanilla JS on the form's `onsubmit` to prevent accidental deletion
- Do not add a separate confirmation page — the browser dialog is sufficient

## Definition of done
- [ ] `POST /expenses/<id>/delete` deletes the expense and redirects to `/profile`
  for the logged-in owner
- [ ] The deleted expense no longer appears in the Recent Transactions list on `/profile`
- [ ] A `GET` request to `/expenses/<id>/delete` returns 405 Method Not Allowed
- [ ] `POST /expenses/<id>/delete` redirects to `/login` for an unauthenticated visitor
- [ ] `POST /expenses/<id>/delete` returns 403 when the expense belongs to a
  different user
- [ ] `POST /expenses/<id>/delete` returns 404 for a non-existent expense id
- [ ] Each transaction row on `/profile` has a "Delete" button that submits a
  `POST` form to the correct delete URL
- [ ] Clicking "Delete" shows a browser `confirm()` dialog before submitting
- [ ] Cancelling the confirm dialog does not delete the expense
- [ ] `pytest` passes with no errors after implementation
