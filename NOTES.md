# NOTES.md

## Architecture Overview

The service follows a simple layered architecture:

* **FastAPI** exposes the REST API.
* **iTunes Search API** provides the initial podcast catalog.
* **RSS feeds** enrich podcasts with descriptions and language.
* **Image processing** downloads artwork and extracts color palettes.
* **PostgreSQL** stores the normalized podcast catalog.
* **SQLAlchemy** handles persistence.
* **Alembic** manages schema migrations.

### Data Flow

```text
iTunes API
     │
     ▼
 Ingestion Service
     │
     ├────────────► RSS metadata enrichment
     │
     ├────────────► Artwork download
     │
     └────────────► Color palette extraction
                     │
                     ▼
               PostgreSQL
                     │
                     ▼
                 FastAPI API
                     │
                     ▼
                  API Client
```

---

## Data Model

The main entity is `Podcast`.

| Field           | Purpose                      |
| --------------- | ---------------------------- |
| `id`            | Internal UUID primary key    |
| `source`        | External provider (`itunes`) |
| `source_id`     | External iTunes identifier   |
| `title`         | Podcast title                |
| `author`        | Publisher/author             |
| `description`   | RSS-enriched description     |
| `feed_url`      | RSS feed                     |
| `podcast_url`   | Public podcast page          |
| `image_url`     | Original artwork URL         |
| `image_path`    | Local stored image           |
| `category`      | Primary genre                |
| `genres`        | All genres (JSONB)           |
| `country`       | Country                      |
| `language`      | RSS language                 |
| `color_palette` | Extracted colors (JSONB)     |
| `created_at`    | Creation timestamp           |
| `updated_at`    | Update timestamp             |

### Why UUIDs?

The external iTunes `collectionId` is preserved as `source_id`, while the service exposes a stable internal UUID. This decouples internal storage from external providers.

---

## Design Decisions

### FastAPI

Chosen for:

* automatic OpenAPI generation
* dependency injection
* straightforward request validation
* async support for external API calls

### PostgreSQL

Chosen because it fits the data model well and supports:

* JSONB fields (`genres`, `color_palette`)
* indexing
* reliable relational storage

### SQLAlchemy + Alembic

Provides:

* typed ORM models
* clean repository layer
* repeatable schema migrations

### API Key Authentication

A static API key was chosen instead of JWT because the assignment explicitly allows it and there are no user accounts or roles.

This keeps authentication simple while still protecting the required endpoints.

### NDJSON Export

The export endpoint returns newline-delimited JSON (`application/x-ndjson`) rather than a single JSON array.

Reasons:

* supports streaming
* keeps memory usage bounded
* scales better for large catalogs

The implementation uses SQLAlchemy's `yield_per()` to fetch records in batches.

---

## Ingestion Pipeline

Both ingestion endpoints share the same pipeline.

1. Fetch podcast(s) from iTunes.
2. Normalize and validate the data.
3. Skip duplicates.
4. Enrich from RSS.
5. Download artwork.
6. Extract a color palette.
7. Persist to PostgreSQL.
8. Return an ingestion summary.

### Idempotency

Duplicate records are prevented by:

* checking existing `(source, source_id)` records before insertion
* enforcing a unique database constraint
* handling race conditions during insertion

Repeated ingestion requests safely skip existing podcasts.

---

## Handling Messy Data

Real podcast feeds are inconsistent, so the service intentionally treats enrichment as **best effort**.

Current behavior includes:

* missing titles are skipped
* duplicate records are skipped
* HTML is cleaned from RSS descriptions
* script/style content is removed
* HTML entities are decoded
* malformed RSS feeds do not fail ingestion
* image download failures do not fail ingestion
* missing optional metadata is allowed

The goal is to preserve valid podcast records even when enrichment fails.

---

## Fallback Strategy

The assignment requires ingestion to continue when the external provider is unavailable.

If iTunes returns network errors or becomes unavailable, the service falls back to:

```text
sample_data/itunes_rock.json
```

This behavior is implemented for both:

* bulk ingestion
* single podcast lookup

and is covered by automated tests.

---

## API Design

Protected endpoints:

* `/ingestion/*`
* `/podcasts/*`
* `/export/*`

Public endpoint:

* `/health`

Pagination is performed at the database level using `OFFSET` and `LIMIT`.

Search currently supports:

* title
* author
* description

Additional filters:

* category
* country

---

## Testing Strategy

The project prioritizes meaningful behavior over coverage percentage.

Tests include:

### Unit tests

* normalization
* RSS parsing
* HTML cleaning
* image processing
* iTunes client

### Integration tests

* ingestion pipeline
* RSS enrichment
* duplicate handling
* graceful failures
* fallback behavior

### API tests

* authentication
* validation
* pagination
* search
* filters
* export
* podcast lookup
* error responses

---

## Trade-offs

### Synchronous enrichment

Artwork processing and RSS enrichment happen during ingestion.

This keeps the implementation simple for the assignment, although production systems would likely move those tasks to background workers.

### Local image storage

Images are stored locally instead of object storage.

For this project it avoids unnecessary infrastructure while still demonstrating the complete processing pipeline.

### Simple search

Search uses PostgreSQL `ILIKE`.

For a larger catalog I would replace this with trigram indexes or PostgreSQL full-text search.

---

## Production Deployment

In production I would package the application as a Docker image and deploy it behind a load balancer on a container platform such as Kubernetes or AWS ECS.

Configuration and secrets would come from environment variables managed by a secret manager rather than being stored in the repository.

The production stack would include:

* FastAPI application containers
* managed PostgreSQL
* object storage for images
* reverse proxy/load balancer
* centralized logging
* monitoring and alerting

New versions would be deployed using rolling deployments to avoid downtime.

---

## Scaling to Millions of Episodes

If the service evolved into a continuously running ingestion platform, I would separate ingestion from request handling.

A possible architecture would be:

```text
Scheduler
    │
    ▼
Job Queue
    │
    ▼
Ingestion Workers
    │
    ├────► iTunes API
    ├────► RSS Feeds
    └────► Image Processing
              │
              ▼
        Object Storage
              │
              ▼
         PostgreSQL
              │
              ▼
          FastAPI API
```

Key improvements would include:

* background workers for enrichment
* retry/backoff for external services
* PostgreSQL connection pooling
* object storage instead of local files
* trigram/full-text search indexes
* caching frequently requested searches
* metrics and structured logging
* horizontal scaling of API and worker processes

The streaming NDJSON export already aligns well with large datasets because it avoids loading the full catalog into memory.

---

## AI Usage

AI-assisted development was used to accelerate implementation, testing, and documentation.

The generated code was reviewed, integrated, and understood before being included in the final solution.
