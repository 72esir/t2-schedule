# Backend Migrations

This project now uses Alembic for schema migrations.

## Files

- `alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/versions/`

## Fresh database

For a new empty database:

```powershell
alembic upgrade head
```

With Docker Compose:

```powershell
docker compose exec -T backend alembic upgrade head
```

## Existing database

If the database was created earlier with `create_all()` or manual SQL files, do not run the initial Alembic migration directly on top of it.

Instead:

1. Make sure the existing schema already matches current models.
2. Stamp the database with the initial revision.

```powershell
alembic stamp 20260425_0001
```

With Docker Compose:

```powershell
docker compose exec -T backend alembic stamp 20260425_0001
```

After that, use normal upgrades:

```powershell
alembic upgrade head
```

## Create a new migration

```powershell
alembic revision --autogenerate -m "describe change"
```

With Docker Compose:

```powershell
docker compose exec -T backend alembic revision --autogenerate -m "describe change"
```

## Current app behavior

- `AUTO_CREATE_SCHEMA` is now disabled by default.
- `backend.app` only calls `Base.metadata.create_all()` when `AUTO_CREATE_SCHEMA=true`.
- Alembic should be treated as the primary schema management tool.
