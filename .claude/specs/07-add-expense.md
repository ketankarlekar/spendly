# Spec: Add Expense

## Overview
Step 7 replaces the `/expenses/add` stub route with a working form that lets a
logged-in user record a new expense. A `GET` request renders the blank form;
a `POST` request validates the input, inserts the row into the `expenses` table,
and redirects to `/profile` on success. This is the first route that writes
user-generated data, so input validation and the ownership tie (storing
`session["user_id"]` as `user_id`) are critical.

## Depends on
- Step 1: Database setup — the `expenses` table must exist with columns
  `id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.
- Step 3: Login / logout — `session["user_id"]` must be set for the auth guard.

## Routes
- `GET  /expenses/add` — render the blank add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the expense, redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The `expenses` table already has every required field.

A new helper function must be added to `database/db.py`:

```python
def create_expense(user_id, amount, category, date, description):
    ...
```

It inserts one row into `expenses` using parameterised queries and commits.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html` via `{% block content %}`
  - Contains a single `<form method="POST">` with these fields:
    - `amount` — `<input type="number" step="0.01" min="0.01">` (required)
    - `category` — `<select>` with options: Food, Transport, Bills, Health,
      Entertainment, Shopping, Other (required)
    - `date` — `<input type="date">` (required); default value should be
      today's date in `YYYY-MM-DD` format
    - `description` — `<input type="text">` (optional, max 200 chars)
  - Displays a validation error message when the template receives an `error`
    variable
  - On validation failure the form re-populates with the values the user typed
    (pass them back as template variables)
  - Uses `url_for("add_expense")` in the `action` attribute — never a hardcoded path
  - Styling via `static/css/style.css` only; no new CSS file is needed

## Files to change
- `app.py`
  - Change the `add_expense` stub:
    - Add `methods=["GET", "POST"]` to the `@app.route` decorator
    - Add a login guard: redirect to `/login` if `session.get("user_id")` is falsy
    - On `GET`: render `add_expense.html` with `today` passed as the default date
    - On `POST`:
      1. Read `amount`, `category`, `date`, `description` from `request.form`
      2. Validate: `amount` must be a positive number, `category` must be one of
         the seven allowed values, `date` must be a valid `YYYY-MM-DD` string
      3. On failure: re-render the form with an `error` message and the submitted values
      4. On success: call `create_expense(...)`, then `redirect(url_for("profile"))`

- `database/db.py`
  - Add `create_expense(user_id, amount, category, date, description)` function

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — `?` placeholders in every SQL statement
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables — never hardcode hex values in any template or stylesheet
- All templates extend `base.html`
- The seven valid categories are: `Food`, `Transport`, `Bills`, `Health`,
  `Entertainment`, `Shopping`, `Other` — define them as a constant in `app.py`
  and pass them to the template; do not hardcode in the template
- `amount` must be cast to `float` in the route; reject anything that raises
  `ValueError` during conversion
- `date` must be validated with `datetime.strptime(value, "%Y-%m-%d")`; reject
  on `ValueError`
- `description` is optional — treat an empty string as `None` when inserting
- Do not modify any route that is already fully implemented

## Definition of done
- [ ] `GET /expenses/add` returns 200 and renders the add-expense form for a
  logged-in user
- [ ] `GET /expenses/add` redirects to `/login` for an unauthenticated visitor
- [ ] Submitting a valid form inserts a row in `expenses` tied to the current
  user's `user_id`
- [ ] After a successful submit the user is redirected to `/profile`
- [ ] The new expense appears in the Recent Transactions list on `/profile`
- [ ] Submitting with `amount` left blank or set to `0` shows a validation error
  and does not insert a row
- [ ] Submitting with a category not in the allowed list shows a validation error
- [ ] Submitting with a malformed date (e.g. `not-a-date`) shows a validation
  error
- [ ] On validation failure the form re-displays with the previously entered
  values pre-filled
- [ ] `pytest` passes with no errors after implementation
