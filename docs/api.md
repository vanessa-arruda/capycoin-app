# API

This document describes the Capycoin backend API: how users sign up and log in, how sessions work, who can do what, and every endpoint for the parents' features. The data model behind it is in [database.md](database.md).

**Status:** the API is being built in steps. The status column of each endpoint table says what exists today. Everything else in this document is the agreed design; update the status column as endpoints are implemented.

## Conventions

- **Base URL:** the backend root, for example `http://localhost:8000` in development.
- **Format:** JSON request and response bodies.
- **Authentication:** every endpoint except the public auth endpoints needs an `Authorization: Bearer <session token>` header.
- **IDs:** UUIDs (version 7, ordered by creation time).
- **Times:** moments are ISO 8601 in UTC, for example `2026-11-10T09:30:00Z`; requests must include an offset (`Z` or `+01:00`), or get `422`. Calendar days (such as a task's `starts_on`) are `YYYY-MM-DD` in the household's timezone. See [Times and dates](database.md#times-and-dates).
- **Pagination:** list endpoints that can grow return `{"items": [...], "next_before": "<id or null>"}`. Pass `?before=<next_before>&limit=<n>` to get the next page. `limit` defaults to 50, maximum 100.
- **Errors:** `{"detail": "<message>"}`, with these status codes:

| Status | Meaning |
|---|---|
| 401 | Not logged in, or the session is expired or revoked. |
| 403 | Logged in and allowed to see the resource, but the role is not enough (for example a non-admin parent inviting someone). |
| 404 | Not found, **or no access**. Records in households the user does not belong to always return 404, so their existence is never revealed. |
| 409 | The request conflicts with the current state (for example approving a request that was already reviewed). |
| 422 | Invalid input, including IDs in the body that do not belong to the household. |
| 429 | Too many attempts. Try again later. |

## Roles

A user has one account **type** (`parent` or `kid`) and a **membership** in each household they belong to. A parent can be the **admin** of a household; each household has exactly one admin, normally the parent who created it.

```mermaid
flowchart LR
    U[User] -->|type| P[parent]
    U -->|type| K[kid]
    P -->|membership with is_admin| A[Admin of household]
    P -->|membership| PM[Parent of household]
    K -->|membership| KM[Kid of household]
```

Permissions depend on the role **in the household of the request**. A parent who is admin of one household and a plain parent in another has admin rights only in the first.

### Permissions

| Action | Admin | Parent | Kid | Not a member |
|---|:-:|:-:|:-:|:-:|
| View household | ✅ | ✅ | ✅ | 404 |
| Edit household name and timezone | ✅ | ✅ | 403 | 404 |
| Delete household | ✅ | 403 | 403 | 404 |
| View members | ✅ | ✅ | 403 | 404 |
| Invite or uninvite parents, remove a parent | ✅ | 403 | 403 | 404 |
| Create, edit or delete kid accounts | ✅ | 403 | 403 | 404 |
| View kids, balances and transaction history | ✅ | ✅ | 403 | 404 |
| Add or remove credits | ✅ | ✅ | 403 | 404 |
| Manage tasks | ✅ | ✅ | 403 | 404 |
| Manage prizes | ✅ | ✅ | 403 | 404 |
| Approve or deny task submissions and prize claims | ✅ | ✅ | 403 | 404 |
| Own account, notifications and notification settings | ✅ | ✅ | ✅ | n/a |

Kid endpoints (seeing their tasks, submitting, claiming prizes) are not part of this document yet.

## Authentication

There are two ways to log in. Both end with a **session token**.

1. **One-time code by email.** Parents always have an email; kids may have one. This is also how parents sign up, which proves they own the email address.
2. **Username or email plus password.** Kids without email use this. Parents can set a password in their settings and then use it too.

### Sign-up and login with a code

```mermaid
sequenceDiagram
    actor User
    participant API
    participant DB
    participant Email

    User->>API: POST /auth/otp/request {email}
    API->>DB: invalidate earlier login codes for this email,<br/>store hash of a new 6-digit code (10 min)
    API->>Email: send code
    API-->>User: 202 (same response whether or not an account exists)

    User->>API: POST /auth/otp/verify {email, code, display_name?}
    API->>DB: find newest unused, unexpired login code for email
    alt wrong code
        API->>DB: attempts += 1 (code is dead after 5)
        API-->>User: 401
    else correct code
        API->>DB: mark code used
        alt account exists
            API->>DB: create session
            API-->>User: 200 {token, expires_at, user}
        else no account and display_name given
            API->>DB: create parent account + session
            API-->>User: 201 {token, expires_at, user}
        else no account and no display_name
            API-->>User: 422 display_name is required to create an account
        end
    end
```

Rules:

- Codes are 6 digits, valid for 10 minutes, usable once, and dead after 5 wrong attempts. Only a hash of the code is stored, and codes are compared in constant time.
- Every code has a **purpose**: `login` (sent by `POST /auth/otp/request`) or `email_validation` (sent when a parent adds an email to a kid's account). A code works only for the purpose it was sent for, so a code from one email can't be used for the other action.
- Requesting a new code invalidates earlier unused codes for that email and purpose.
- An email can receive at most 3 codes per 15 minutes, counting every purpose; more requests get 429.
- `POST /auth/otp/request` never reveals whether an account exists.
- Sign-up always creates a **parent**. Kid accounts are only created by a household admin.

### Login with a password

```mermaid
sequenceDiagram
    actor User
    participant API
    participant DB

    User->>API: POST /auth/login {login, password}
    API->>DB: find user by email or username (lowercased)
    alt user found, has a password, password matches
        API->>DB: create session
        API-->>User: 200 {token, expires_at, user}
    else anything else
        API-->>User: 401 "Invalid login or password"
    end
```

- `login` is an email or a username. Both are matched in lowercase.
- Every failure gives the same 401 message, so it does not reveal which accounts exist or which ones have a password.
- Passwords are hashed with Argon2 (`pwdlib`). They must be 8 to 128 characters.
- Repeated failures will be rate limited per login and per IP address (429). Not implemented yet; planned for the hardening step.

### Sessions

A session is a row in the `sessions` table. The client receives a random token (32 bytes, URL-safe). The database stores only its SHA-256 hash, so a database leak does not expose usable tokens.

```mermaid
stateDiagram-v2
    [*] --> Active: login or sign-up
    Active --> Active: request (last_used_at refreshed)
    Active --> Expired: 7 days without use<br/>or 30 days after login
    Active --> Revoked: logout, or password changed
    Expired --> [*]
    Revoked --> [*]
```

- **Lifetime:** a session expires 30 days after login, or after 7 days without use, whichever comes first. `last_used_at` is refreshed at most every 5 minutes, so most requests do not write to the database.
- **Logout** revokes the current session.
- **Changing the password** revokes all other sessions of that user.
- **Deleting a user** deletes their sessions.
- Database sessions were chosen over JWTs because every request already reads the database to check household membership, so JWTs would save nothing, and they cannot be revoked immediately.

### Checking access on every request

```mermaid
flowchart TD
    R[Request] --> T{Bearer token valid?<br/>exists, not expired, not revoked}
    T -- no --> E401[401]
    T -- yes --> H{Path has /households/:hid?}
    H -- no --> OWN[Only the caller's own data:<br/>/me, /notifications]
    H -- yes --> M{Caller is a member<br/>of household hid?}
    M -- no --> E404[404]
    M -- yes --> ROLE{Role allowed<br/>for this endpoint?}
    ROLE -- no --> E403[403]
    ROLE -- yes --> REC{Record found by id<br/>AND household_id = hid?}
    REC -- no --> E404b[404]
    REC -- yes --> BODY{IDs in the body belong<br/>to household hid?}
    BODY -- no --> E422[422]
    BODY -- yes --> OK[Handle the request]
```

How this is built, and what every new endpoint must follow:

1. `get_current_user` reads the bearer token and loads the user, or returns 401.
2. Household routers are created with `household_router()` from `api/deps.py`. It mounts them under `/households/{household_id}` with a router-level dependency (`get_membership`) that loads the caller's membership, or returns 404. It runs for every endpoint in the router, so an endpoint cannot skip it.
3. Endpoints declare the role they need with a parameter type: `Membership` (any member), `ParentMembership` (a parent of the household, else 403) or `AdminMembership` (the admin, else 403). `ParentUser` is for routes outside a household that need a parent account, such as creating one. These checks run before the request body is validated, so a caller without access never learns what the body should look like.
4. Records are always loaded with the household in the query, for example `WHERE tasks.id = :id AND tasks.household_id = :household_id`. Submissions and claims are joined to their task or prize to check the household. Never load a record by id alone and check afterwards.
5. IDs in request bodies (such as `kid_ids`) are checked against the household's members too.
6. Endpoints outside households (`/me`, `/notifications`) always filter by the caller's own user id.
7. Responses use explicit Pydantic response models, never ORM objects, so hashes and internal fields cannot leak.
8. Tests: `tests/test_access.py` has a table (`ROUTES`) that lists every route with the access it needs. One parametrized test calls each route as an anonymous user, a parent of another household, a kid, a non-admin parent, and with record ids from another household, and checks the status codes above. Another test fails if any route is missing from that table.

### Database access from outside the backend

Supabase publishes tables in the `public` schema through its REST API. The backend is the only client of the database, so a migration enables Row Level Security on every table, with no policies, and removes access for Supabase's `anon` and `authenticated` roles. The backend connects as the owner of the tables, which RLS does not apply to. A test fails if any table is missing RLS, so new tables cannot be published by accident.

### Email

Emails (codes and invitations) go through the `EmailSender` interface in `app-backend/core/email/`. The backend is chosen by the `email_backend` setting. Today the only backend is `console`, which prints emails to the server output. A real provider will be a new module next to `console.py`; the console backend can then be removed without touching the code that sends emails.

## Endpoints

`{hid}` is a household id. "Parent" includes the admin.

### Auth

| Method | Path | Who | Status |
|---|---|---|---|
| POST | `/auth/otp/request` | anyone | implemented |
| POST | `/auth/otp/verify` | anyone | implemented |
| POST | `/auth/login` | anyone | implemented |
| POST | `/auth/logout` | logged in | implemented |

- `POST /auth/otp/request` `{email}` → `202`.
- `POST /auth/otp/verify` `{email, code, display_name?}` → `200` (login) or `201` (new parent account) with `{token, expires_at, user}`. `401` for a wrong or expired code, `422` if the account does not exist and `display_name` is missing.
- `POST /auth/login` `{login, password}` → `200 {token, expires_at, user}` or `401`.
- `POST /auth/logout` → `204`. Revokes the current session.

### My account

| Method | Path | Who | Status |
|---|---|---|---|
| GET | `/me` | logged in | implemented |
| PATCH | `/me` | logged in | implemented |
| PUT | `/me/password` | logged in | implemented |
| GET | `/me/households` | logged in | implemented |
| GET | `/me/notification-preferences` | logged in | implemented |
| PUT | `/me/notification-preferences` | logged in | implemented |

- `PATCH /me` `{display_name?, username?}`. Omitted fields are unchanged; `"username": null` removes the username (`422` if the user has no email, since they could no longer log in). Usernames are 3 to 50 characters of `a-z 0-9 _ . -` and are stored in lowercase. `409` if the username is taken. Changing the email is not supported yet.
- `PUT /me/password` `{current_password?, new_password}` → `204`. `current_password` is required when a password is already set; a missing or wrong one gives `422`. Revokes the user's other sessions.
- `GET /me/households` → `[{id, name, timezone, is_admin}]`, the households the user belongs to, sorted by name.
- `GET /me/notification-preferences` → `[{type, channel, enabled}]` for every type sent to the caller's account type and every channel, with defaults filled in. `PUT` takes `{preferences: [{type, channel, enabled}]}` (up to 50), saves them and returns the full list. A type that is not sent to the caller's account type gives `422`. Only choices that differ from the default are stored.

### Households and members

| Method | Path | Who | Status |
|---|---|---|---|
| POST | `/households` | parent account | implemented |
| GET | `/households/{hid}` | member | implemented |
| PATCH | `/households/{hid}` | parent | implemented |
| DELETE | `/households/{hid}` | admin | implemented |
| GET | `/households/{hid}/members` | parent | implemented |
| DELETE | `/households/{hid}/members/{user_id}` | admin | implemented |

- `POST /households` `{name, timezone}` → `201`. The caller becomes the admin. `timezone` must be a valid IANA name such as `Europe/Stockholm`.
- `GET /households/{hid}` → `{id, name, timezone}`.
- `PATCH /households/{hid}` `{name?, timezone?}`. Omitted fields are unchanged; `null` gives `422`.
- `DELETE /households/{hid}` `{confirm_name}` → `204`. `confirm_name` must equal the household name exactly (`422` otherwise). Deletes everything in the household (see database.md).
- `GET /households/{hid}/members` → `[{user_id, role, display_name, username, email, is_admin, joined_at}]`, the admin first, then parents, then kids.
- `DELETE /households/{hid}/members/{user_id}` → `204`. Removes a **parent** from the household. The admin cannot remove themselves (`409`). Kids are removed through the kid endpoints (`422` here). `404` if the user is not a member of this household.

### Invitations

| Method | Path | Who | Status |
|---|---|---|---|
| GET | `/households/{hid}/invitations` | admin | implemented |
| POST | `/households/{hid}/invitations` | admin | implemented |
| DELETE | `/households/{hid}/invitations/{invitation_id}` | admin | implemented |
| POST | `/invitations/accept` | logged-in parent | implemented |

```mermaid
sequenceDiagram
    actor Admin
    actor Invitee
    participant API
    participant Email

    Admin->>API: POST /households/{hid}/invitations {email}
    API->>API: store hash of a random token, expires in 7 days
    API->>Email: link with the token
    API-->>Admin: 201
    Invitee->>API: sign up or log in with that email
    Invitee->>API: POST /invitations/accept {token}
    alt token valid, pending, not expired,<br/>caller is a parent with the invited email
        API->>API: add membership, mark invitation accepted
        API-->>Invitee: 200 {household}
    else invited email differs from caller's
        API-->>Invitee: 403
    else invalid, expired, revoked or used token
        API-->>Invitee: 404
    end
```

- `POST` `{email}` → `201 {id, email, status, expires_at, created_at}`. `409` if that email already has an open invitation or belongs to a member. An expired invitation for the same email is revoked and replaced.
- The email links to `{app_url}/invitations/accept#token=<token>`. `app_url` is a setting (default `http://localhost:5173`). The token is in the URL fragment, which browsers do not send to servers, so it stays out of server and proxy logs. The web app reads it and calls `POST /invitations/accept`.
- `GET` lists open invitations: pending and not expired, newest first. `DELETE` revokes a pending one (`204`); `404` if it is not pending.
- `POST /invitations/accept` `{token}` → `200 {id, name, timezone}` of the household. `409` if the caller is already a member. Kid accounts get `403`.
- Only the user whose email matches the invitation can accept it. Parents' emails are always verified, because parents sign up with a one-time code.
- Sending invitations is not rate limited yet; planned for the hardening step.

### Kids and wallet

| Method | Path | Who | Status |
|---|---|---|---|
| GET | `/households/{hid}/kids` | parent | implemented |
| POST | `/households/{hid}/kids/email-code` | admin | implemented |
| POST | `/households/{hid}/kids` | admin | implemented |
| GET | `/households/{hid}/kids/{kid_id}` | parent | implemented |
| PATCH | `/households/{hid}/kids/{kid_id}` | admin | implemented |
| DELETE | `/households/{hid}/kids/{kid_id}` | admin | implemented |
| GET | `/households/{hid}/kids/{kid_id}/transactions` | parent | implemented |
| POST | `/households/{hid}/kids/{kid_id}/adjustments` | parent | implemented |

A kid logs in with a one-time code if they have an email, or with a username and password if they don't (or either, if they have both). An email is added only after the code sent to it is entered, so every email on an account is verified:

```mermaid
sequenceDiagram
    actor Parent
    participant API
    participant Inbox as Kid's inbox

    Parent->>API: POST /households/{hid}/kids/email-code {email}
    API->>Inbox: 6-digit code (purpose email_validation)
    API-->>Parent: 202
    Parent->>API: POST /households/{hid}/kids {display_name, email, code, username?, password?}
    alt code valid
        API->>API: create the kid with the verified email
        API-->>Parent: 201
    else wrong, expired or used code
        API-->>Parent: 422
    end
```

Without this check a parent could set an address they don't own, and its owner would land in the kid's account when logging in with a code, and could not sign up with it.

- `POST /kids/email-code` `{email}` → `202`. Sends a code to the address, saying who wants to add it and to which household. Same limits as login codes.
- `POST /kids` `{display_name, email?, code?, username?, password?}` → `201`. Needs `email` with its `code`, or `username` and `password`, or both. A wrong code gives `422` (not `401`, which would mean the parent's session ended). `409` if the username or email is taken; the email check runs after the code check, so it reveals nothing to someone who can't read the inbox.
- Kid responses are `{id, display_name, username, email, balance, reserved, available}`. `balance` is the sum of the kid's credits in this household, `reserved` the cost of their pending prize claims, and `available` is `balance - reserved`.
- `GET /kids` lists the household's kids by name. `GET`, `PATCH` and `DELETE` on `/kids/{kid_id}` return `404` if the id is not a kid of this household.
- `PATCH /kids/{kid_id}` `{display_name?, username?, password?, email?, code?}`. Omitted fields are unchanged. A new `email` needs a `code` from `POST /kids/email-code`. `"email": null` or `"username": null` removes it, as long as the kid can still log in (`422` otherwise). `null` for `display_name` or `password` gives `422`. Setting `password` revokes the kid's sessions.
- `DELETE /kids/{kid_id}` → `204`. Removes the kid from this household, with their assignments, submissions, claims, credits and notifications here (and parents' notifications about them). The account itself is deleted only if the kid belongs to no other household.
- `GET /transactions` → paginated credit log for this household, newest first. Each entry is `{id, amount, kind, note, task_submission_id, task_title, prize_claim_id, prize_name, created_by, created_at}`; `kind` is `task_reward`, `prize_claim` or `manual_adjustment`.
- `POST /adjustments` `{amount, note}` → `201` with the new entry. `amount` is a non-zero integer from -1,000,000 to 1,000,000, positive to add and negative to remove credits. `note` (1 to 500 characters) tells the kid why. A balance may go negative. The kid gets a `credits_adjusted` notification.

### Tasks

| Method | Path | Who | Status |
|---|---|---|---|
| GET | `/households/{hid}/tasks` | parent | implemented |
| POST | `/households/{hid}/tasks` | parent | implemented |
| GET | `/households/{hid}/tasks/{task_id}` | parent | implemented |
| PATCH | `/households/{hid}/tasks/{task_id}` | parent | implemented |
| DELETE | `/households/{hid}/tasks/{task_id}` | parent | implemented |

- `POST` `{title, description?, reward, recurrence?, starts_on, due_at?, kid_ids}` → `201`.
  - `reward` is 1 to 1,000,000. `recurrence` is `none` (default), `daily`, `weekly` or `monthly`.
  - `starts_on` is a calendar day in the household's timezone. For one-off tasks `due_at` is the deadline; for recurring tasks it is when they stop repeating. `due_at` must not fall on a day before `starts_on`, counted in the household's timezone.
  - `kid_ids` has 1 to 50 ids, duplicates ignored. Every id must be a kid of this household (`422` otherwise).
- Task responses are `{id, title, description, reward, recurrence, starts_on, due_at, archived_at, kid_ids, created_by, created_at, updated_at}`.
- `GET` list is paginated, newest first. Filters: `?kid_id=`, `?archived=true|false` (default `false`).
- `PATCH` takes the same fields, all optional. `null` clears `description` or `due_at`; for the other fields it gives `422`. `kid_ids` replaces the assignment list. A new `reward` applies to submissions approved after the change. Archived tasks cannot be changed (`409`).
- `DELETE` archives the task (`204`, also when it is already archived). Archived tasks are hidden from kids; their pending submissions can still be reviewed.

### Prizes

| Method | Path | Who | Status |
|---|---|---|---|
| GET | `/households/{hid}/prizes` | parent | implemented |
| POST | `/households/{hid}/prizes` | parent | implemented |
| GET | `/households/{hid}/prizes/{prize_id}` | parent | implemented |
| PATCH | `/households/{hid}/prizes/{prize_id}` | parent | implemented |
| DELETE | `/households/{hid}/prizes/{prize_id}` | parent | implemented |

- `POST` `{name, description?, cost}` → `201`. `cost` is 1 to 1,000,000.
- Prize responses are `{id, name, description, cost, archived_at, created_by, created_at, updated_at}`.
- `GET` list is paginated, newest first. Filter: `?archived=true|false` (default `false`).
- `PATCH` takes the same fields, all optional. `null` clears `description`; for `name` or `cost` it gives `422`. A new `cost` does not change pending claims, which keep the cost from when they were made. Archived prizes cannot be changed (`409`).
- `DELETE` archives the prize (`204`, also when it is already archived). Pending claims can still be reviewed.

### Approvals

| Method | Path | Who | Status |
|---|---|---|---|
| GET | `/households/{hid}/task-submissions` | parent | implemented |
| GET | `/households/{hid}/task-submissions/{submission_id}` | parent | implemented |
| POST | `/households/{hid}/task-submissions/{submission_id}/approve` | parent | implemented |
| POST | `/households/{hid}/task-submissions/{submission_id}/deny` | parent | implemented |
| GET | `/households/{hid}/prize-claims` | parent | implemented |
| GET | `/households/{hid}/prize-claims/{claim_id}` | parent | implemented |
| POST | `/households/{hid}/prize-claims/{claim_id}/approve` | parent | implemented |
| POST | `/households/{hid}/prize-claims/{claim_id}/deny` | parent | implemented |

- Lists filter by `?status=pending|approved|denied` (default `pending`) and `?kid_id=`, and are paginated, newest first.
- Submissions are `{id, task_id, task_title, reward, kid_id, kid_display_name, period_start, status, note, submitted_at, reviewed_by, reviewed_at, review_note}`. `reward` is the task's current reward, which an approval credits.
- Claims are `{id, prize_id, prize_name, cost, kid_id, kid_display_name, status, requested_at, reviewed_by, reviewed_at, review_note}`. `cost` was fixed when the kid claimed the prize.
- `approve` and `deny` take an optional body `{note?}` (up to 500 characters, shown to the kid) and return the updated request. `409` if it is no longer pending. The kid gets a notification (`task_approved`, `task_denied`, `prize_claim_approved` or `prize_claim_denied`).
- Requests for archived tasks and prizes can still be reviewed.
- A task approval credits the task's current `reward`. A prize approval debits the claim's `cost` and needs the kid's balance, minus their other pending claims, to cover it (`409` otherwise). Pending claims keep their credits reserved: if a credit removal left a kid unable to cover all their pending claims, a parent denies one before approving another.

```mermaid
sequenceDiagram
    actor Parent
    participant API
    participant DB

    Parent->>API: POST .../task-submissions/{id}/approve
    API->>DB: BEGIN
    API->>DB: lock the kid's household_members row (FOR UPDATE)
    API->>DB: load submission WHERE id AND task.household_id = hid
    alt not pending
        API->>DB: ROLLBACK
        API-->>Parent: 409
    else pending
        API->>DB: status = approved, reviewed_by, reviewed_at
        API->>DB: insert credit_transactions (+reward)
        API->>DB: insert notification for the kid
        API->>DB: COMMIT
        API-->>Parent: 200
    end
```

The lock on the kid's membership row makes concurrent approvals and claims for the same kid run one after another, so two requests cannot spend the same credits.

### Notifications

| Method | Path | Who | Status |
|---|---|---|---|
| GET | `/notifications` | logged in | implemented |
| GET | `/notifications/{notification_id}` | recipient | implemented |
| POST | `/notifications/{notification_id}/read` | recipient | implemented |
| POST | `/notifications/read-all` | logged in | implemented |

- Notifications are `{id, household_id, type, read_at, created_at, subject}`. `subject` summarizes what it is about, so a client can show it without another request: `{kind, id, kid_id, kid_display_name, title, status, amount, note}`.
  - `kind` is `task_submission`, `prize_claim` or `credit_transaction`, and `id` is that record's id.
  - `title` is the task title or prize name, and `status` the review status (both `null` for credit changes).
  - `amount` is the task's reward, the claim's cost, or the credits added (positive) or removed (negative).
  - `note` is the parent's review note or the adjustment note.
- `GET /notifications` filters: `?household_id=`, `?unread=true`. Paginated, newest first. Only the caller's own notifications, from households they still belong to.
- `GET /notifications/{id}` → one notification. `404` for anyone but the recipient, and for households the recipient left.
- `POST /notifications/{id}/read` → `204`. Reading it again keeps the first `read_at`.
- `POST /notifications/read-all` takes an optional `{household_id}` → `204`.

Parents get `task_submitted` and `prize_claimed`. Kids get `task_approved`, `task_denied`, `prize_claim_approved`, `prize_claim_denied` and `credits_adjusted`. A notification is created only when the recipient has not turned off its `in_app` channel. Without a saved preference, `in_app` is on and `email` is off (no notification emails are sent yet).

### Health

| Method | Path | Who | Status |
|---|---|---|---|
| GET | `/health` | anyone | implemented |

Returns `{"status": "ok"}` when the API can reach the database.

## Not covered yet

- Kid endpoints: seeing tasks, submitting with a photo, claiming prizes, wallet and notifications.
- Photo upload and signed links to view photos.
- Changing a parent's own email address (it would reuse the `email_validation` code).
- Adding an existing kid to a second household.
- Transferring the admin role.
- Email delivery through a real provider.
