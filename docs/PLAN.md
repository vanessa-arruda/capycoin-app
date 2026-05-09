# Capycoin — Refactor & Build Plan

A gamified chores-and-rewards app for kids, built for the family.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + SQLAlchemy + Alembic |
| Database | PostgreSQL (Docker container on VPS) |
| Auth | JWT (python-jose + passlib — already in requirements) |
| Frontend | Next.js + Tailwind CSS |
| Infra | Docker Compose on family VPS |
| Backend tests | pytest + httpx (async TestClient) |
| Frontend tests | Jest + React Testing Library + Playwright (E2E) |

---

## Phase 1 — Backend Cleanup

### 1.1 Database connection

- [ ] Remove Supabase-specific config from `core/config.py` and `core/database.py`
- [ ] Use standard PostgreSQL env vars: `DATABASE_URL`
- [ ] Switch to async SQLAlchemy (`asyncpg`) for better FastAPI integration
- [ ] Replace `create_tables.py` script with Alembic migrations only

### 1.2 Fix and complete models

- [ ] `Household` — add `name` field validation; no structural changes needed
- [ ] `Parent` — looks good; verify relationships after Child fix
- [ ] `Child` — add missing `activities` relationship to `ChildActivity`; add `points_total` computed property; add `avatar` field (capybara avatar selection)
- [ ] `Activity` — add `category` field (chore, play, creative, etc.); keep `default_points`
- [ ] `ParentActivity` — add `points_override` (parent can change default points); add `max_per_day`, `max_per_week` limits; add `available_from` / `available_until` for timed quests; add `is_active` flag
- [ ] `ChildActivity` — looks complete; verify status enum transitions
- [ ] `Reward` — implement: `id`, `name`, `description`, `points_cost`, `household_id`, `is_active`, `created_at`; add `ChildReward` join table for redemptions
- [ ] Add `ChildReward` model: `id`, `child_id`, `reward_id`, `redeemed_at`, `approved_by`

### 1.3 Pydantic schemas

Create `app-backend/schemas/` with one file per domain:

- [ ] `schemas/auth.py` — `LoginRequest`, `TokenResponse`
- [ ] `schemas/parent.py` — `ParentCreate`, `ParentRead`
- [ ] `schemas/child.py` — `ChildCreate`, `ChildRead`, `ChildSummary` (points + level)
- [ ] `schemas/activity.py` — `ActivityCreate`, `ActivityRead`, `ParentActivityConfig`, `ChildActivityRead`
- [ ] `schemas/reward.py` — `RewardCreate`, `RewardRead`, `RedemptionRequest`

### 1.4 API routes

Create `app-backend/routers/` with one file per domain:

- [ ] `routers/auth.py` — `POST /auth/login`, `POST /auth/register`
- [ ] `routers/parents.py` — `GET /parents/me`, `GET /parents/me/children`, `GET /parents/me/activities`
- [ ] `routers/children.py` — `GET /children/me`, `GET /children/me/activities`, `GET /children/me/rewards`
- [ ] `routers/activities.py`:
  - `GET /activities` — global activity catalog
  - `POST /activities` — parent creates activity (parent only)
  - `POST /activities/{id}/enable` — parent enables activity for their household
  - `POST /child-activities` — child picks an activity
  - `POST /child-activities/{id}/submit` — child marks done
  - `PATCH /child-activities/{id}/review` — parent approves/rejects
- [ ] `routers/rewards.py`:
  - `GET /rewards` — list rewards for household
  - `POST /rewards` — parent creates reward
  - `POST /rewards/{id}/redeem` — child redeems
  - `PATCH /rewards/redemptions/{id}` — parent approves redemption

### 1.5 Auth middleware

- [ ] `core/auth.py` — JWT encode/decode, `get_current_parent`, `get_current_child`, `get_current_user` (either role)
- [ ] Role-based access: parents and children have separate login flows and route guards

### 1.6 Points & leveling logic

- [ ] Points are awarded to child when parent approves a `ChildActivity`
- [ ] Points are deducted when parent approves a `ChildReward` redemption
- [ ] Level thresholds (define in constants): 0–99 pts = Lv1, 100–299 = Lv2, 300–599 = Lv3, etc.
- [ ] `child.level` and `child.points_total` derived from `ChildActivity` approved records

---

## Phase 2 — Docker Compose & Local Dev

- [ ] `Dockerfile` for the FastAPI backend (multi-stage, slim image)
- [ ] `docker-compose.yml`:
  - `db` service: `postgres:16-alpine`, volume for data persistence
  - `backend` service: built from `./app-backend`, depends on `db`
  - `frontend` service: built from `./app-frontend`, depends on `backend`
- [ ] `.env.example` with all required vars (no secrets, just keys)
- [ ] Update `Makefile`:
  - `make up` → `docker compose up`
  - `make down` → `docker compose down`
  - `make migrate` → run Alembic migrations inside container
  - `make test-backend` → run pytest inside container
  - `make test-frontend` → run jest inside container

---

## Phase 3 — Frontend (Next.js)

Scaffold in `app-frontend/` using `create-next-app` with TypeScript and Tailwind.

### 3.1 Project structure

```
app-frontend/
  app/
    (auth)/
      login/
      register/
    (parent)/
      dashboard/
      activities/
      rewards/
      children/
    (child)/
      dashboard/
      activities/
      rewards/
      profile/
  components/
    ui/           # shared primitives (Button, Card, Badge, etc.)
    parent/       # parent-specific components
    child/        # child-specific components (gamified)
  lib/
    api.ts        # API client (fetch wrapper)
    auth.ts       # JWT storage + helpers
  __tests__/
```

### 3.2 Pages — Parent view

- [ ] Login page
- [ ] Dashboard: list of children with points summary
- [ ] Activities page: enable/disable global activities, set point values and limits
- [ ] Review queue: pending `ChildActivity` submissions to approve/reject
- [ ] Rewards page: create/manage rewards

### 3.3 Pages — Child view (gamified, kid-friendly)

- [ ] Login page (simple, email + password)
- [ ] Dashboard: capybara avatar, current points, current level, XP bar
- [ ] Activity board: available activities shown as quest cards
- [ ] My quests: active + completed activities
- [ ] Rewards store: available rewards with point costs
- [ ] Profile: avatar selection, stats

### 3.4 Shared

- [ ] Auth context (JWT stored in httpOnly cookie via Next.js middleware)
- [ ] Role detection: redirect parent → parent dashboard, child → child dashboard on login
- [ ] API client with auth headers

---

## Phase 4 — Testing

See `app-backend/tests/` and `app-frontend/__tests__/` for test files.

### Backend (pytest)

- [ ] `conftest.py` — in-memory SQLite test DB, FastAPI TestClient, fixtures for parent/child/household
- [ ] `test_auth.py` — register, login, invalid credentials, JWT validation
- [ ] `test_activities.py` — create, enable, pick, submit, approve, reject
- [ ] `test_rewards.py` — create reward, redeem, approve redemption, insufficient points
- [ ] `test_children.py` — points total, level calculation, avatar

### Frontend (Jest + RTL)

- [ ] `login.test.tsx` — renders form, submits, handles errors
- [ ] `activity-card.test.tsx` — renders activity, pick button interaction
- [ ] `dashboard-child.test.tsx` — shows correct points, level, avatar
- [ ] `dashboard-parent.test.tsx` — shows children summary, pending approvals count
- [ ] `review-queue.test.tsx` — approve/reject actions call correct API

### E2E (Playwright)

- [ ] Parent login → enable activity → child login → pick activity → submit → parent approves → child points updated
- [ ] Child redeems reward → parent approves → points deducted

---

## Phase 5 — VPS Deployment

- [ ] Clone repo on VPS
- [ ] Copy `.env` with production values to VPS (never commit)
- [ ] Run `docker compose up -d` on VPS
- [ ] Set up Nginx as reverse proxy:
  - `yourdomain.com` → Next.js frontend (port 3000)
  - `yourdomain.com/api` → FastAPI backend (port 8000)
- [ ] SSL with Let's Encrypt via Certbot (free HTTPS)
- [ ] Set up `docker compose restart` on VPS reboot (systemd service or cron)

---

## Current model status

| Model | Status |
|---|---|
| Household | Done — minor validation needed |
| Parent | Done |
| Child | Needs `activities` relationship + `avatar` field |
| Activity | Needs `category` field |
| ParentActivity | Needs `points_override`, limits, `is_active` |
| ChildActivity | Done |
| Reward | Empty — needs full implementation |
| ChildReward | Missing — needs to be created |
