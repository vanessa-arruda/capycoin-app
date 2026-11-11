# Capycoin 🐾

Gamified financial education for kids to help them save money and have control of it in a gamefied way.
the activities will be chores and plays that will give them points that can be exchanged by rewards set by their parents.

## Parents accounts

- sets how many kids account will be related to their account (and approve the link after the kid creates profile - using email)
- sets points value for each activity
- sets which activities they turn available from the existent list available
- review and approve the activity the kids sent for review/approval
- sets the period for how long each activity is available for conclusion (like temporary quests in a game) and how many times they can do that activity per day/week/month.
- see the board with all current available activity
- see how many points and which activities the kids have right now.

## Child accounts

- child receives an invite to create their profile as kid (with their name, email and a capybara avatar)
- can list all available activities
- can choose which activity they wanna pick up
- can see all on going activity they chose
- see all completed activities they did
- can see list of rewards
- can exchange the points they have for the rewards available up to the total points available.
- can see all points they have
- gains level for each amount of activities completed, certain levels, unlock new special items for exchange.

## How to run

Requires [uv](https://docs.astral.sh/uv/). It installs Python 3.15 and the dependencies into `app-backend/.venv`.

```bash
make be-install
make be-migrate
make be-dev
```

`make be-migrate` needs a `.env` at the repo root with the database settings (`username`, `password`, `host`, `port`, `dbname`). See [docs/database.md](docs/database.md) for the data model.

### Container image

```bash
make be-image                    # builds capycoin-be:latest from app-backend/Containerfile
podman run --rm --env-file .env capycoin-be alembic upgrade head
podman run -d -p 8000:8000 --env-file .env capycoin-be
```

- **Contents:** the app, its dependencies and the Alembic migrations, running as a non-root user on port 8000. Tests, dev tools and `.env` are not included.
- **Settings:** the image reads its settings from environment variables, so pass them with `--env-file` or `-e`. These are the same keys as `.env`, plus `cors_origins` and `app_url` (see `.env.example`).
- **Migrations:** run them with the same image before starting a new version.
- **Behind a reverse proxy:** set `FORWARDED_ALLOW_IPS` to the proxy's address, so rate limits see the client's IP and not the proxy's.
- **More workers:** set `WEB_CONCURRENCY` to the number of worker processes.
- **Health check:** the image calls `GET /health` every 30 seconds; Docker and Compose use it. Podman ignores health checks from the image, so pass `--health-cmd` there if you need one.
- **Other build tools:** Podman and Buildah read `Containerfile` and `.containerignore`. With Docker, run `docker build -f Containerfile app-backend`; Docker does not read `.containerignore`, so tests and dev files end up in the image, but it still works. In Kubernetes, point a probe at `/health`.

## first steps

- 1 - Set up  FastAPI app and simple hello world route;
- 2 - Set up  database connection (SQLAlchemy + Supabase/PostgreSQL);
- 3 - Set up  configuration loader (.env variables);
- 4 - Set up  basic models (Parent, Child, Activity);
- 5 - Set up  basic API routers (like /parent, /child);
- 6 - Make simple Pydantic schemas (for request/response)
