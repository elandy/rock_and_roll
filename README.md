[![CI](https://github.com/elandy/rock_and_roll/actions/workflows/ci.yml/badge.svg)](https://github.com/elandy/rock_and_roll/actions/workflows/ci.yml)

# Rock & Roll Podcast Service

A FastAPI + PostgreSQL REST API that ingests rock & roll podcasts from the iTunes Search API, enriches them with RSS metadata, extracts artwork color palettes, and exposes a searchable podcast catalog.

## Features

* Bulk podcast ingestion from the iTunes Search API
* Single podcast ingestion by iTunes collection ID
* Idempotent ingestion (safe to run multiple times)
* RSS metadata enrichment (description and language)
* Artwork download and color palette extraction
* Paginated podcast listing with search and filters
* Single podcast lookup
* Streaming NDJSON export for large catalogs
* API-key authentication
* Interactive OpenAPI documentation
* Automated test suite

## Tech Stack

* Python 3.13
* FastAPI
* PostgreSQL
* SQLAlchemy 2.0
* Alembic
* uv
* Docker Compose
* httpx
* Pydantic v2

## Prerequisites

* Docker
* Docker Compose

No local Python installation is required.

## Quick Start

Clone the repository:

```bash
git clone <repository-url>
cd rock_and_roll
```

Create an environment file:

```bash
cp .env.example .env
```

Start the application:

```bash
docker compose up --build
```

Run database migrations:

```bash
docker compose exec api uv run alembic upgrade head
```

Open the interactive API documentation:

```text
http://localhost:8000/docs
```

## Configuration

Configure the service using environment variables.

| Variable          | Description                     | Default                    |
| ----------------- | ------------------------------- |----------------------------|
| `DATABASE_URL`    | PostgreSQL connection string    | Docker default             |
| `API_KEY`         | API key for protected endpoints | `supersecret`              |
| `ITUNES_BASE_URL` | iTunes Search API base URL      | `https://itunes.apple.com` |

## Authentication

All endpoints except `/health` require an API key.

Include the header:

```http
X-API-Key: supersecret
```

Swagger UI also supports authentication through the **Authorize** button.

## API Overview

### Health

```http
GET /health
```

Public endpoint that verifies the application's health.

### Bulk Ingestion

```http
POST /ingestion/bulk
```

Example:

```text
POST /ingestion/bulk?term=rock&limit=20
```

Returns a summary:

```json
{
  "fetched": 20,
  "stored": 18,
  "skipped": 2
}
```

### Single Ingestion

```text
POST /ingestion/single?collection_id=1484275082
```

### List Podcasts

```text
GET /podcasts
```

Supports:

* `page`
* `page_size`
* `search`
* `category`
* `country`

Example:

```text
GET /podcasts?search=history&page=1&page_size=10
```

### Get One Podcast

```text
GET /podcasts/{id}
```

### Export Catalog

```text
GET /export/podcasts
```

Returns a streaming **NDJSON** response suitable for large datasets.
This endpoint returns NDJSON (newline-delimited JSON), so tools like curl, jq, or line-oriented processors are the intended clients rather than Swagger's JSON viewer.

## Running Tests

Run the full test suite:

```bash
docker compose exec api uv run pytest
```

Run a specific test file:

```bash
docker compose exec api uv run pytest tests/test_ingestion.py
```

## Continuous Integration

GitHub Actions runs the test suite automatically on pushes to main and on pull requests.

The CI workflow:

* Starts PostgreSQL 16 as a service.
* Installs Python and project dependencies using uv.
* Applies the Alembic migrations.
* Runs the full pytest suite.

This validates both database migrations and application behavior in a clean environment.

## Deployment

The application has also been deployed to FastAPI Cloud with Neon PostgreSQL as the managed database.

The deployed environment uses environment variables for configuration and secrets rather than storing deployment credentials in the repository.

The deployment and its trade-offs are documented in NOTES.md.

## Database Migrations

Create a migration:

```bash
docker compose exec api uv run alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
docker compose exec api uv run alembic upgrade head
```

## Fallback Behavior

If the iTunes API is unavailable or rate-limits requests, ingestion automatically falls back to the bundled sample response located at:

```text
sample_data/itunes_rock.json
```

This keeps ingestion functional even when the external service is unavailable.

## Image Processing

During ingestion the service:

1. Downloads podcast artwork.
2. Stores the image locally.
3. Extracts a dominant color palette.
4. Saves the palette as podcast metadata.

If image downloading or processing fails, the podcast is still stored.

## Project Structure

```text
app/
  api/
  db/
  repositories/
  schemas/
  services/
  utils/

alembic/
tests/
sample_data/
```

## Notes

Implementation decisions, trade-offs, architecture, scaling considerations, and production deployment ideas are documented in `NOTES.md`.
