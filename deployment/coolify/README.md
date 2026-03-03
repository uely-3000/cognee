# Deploy Cognee API on Coolify (Dockerfile)

This guide deploys the Cognee API from a monorepo subdirectory on Coolify, using:

- Supabase (external Postgres) for relational storage
- Qdrant (existing Coolify service) for vectors
- FalkorDB (existing Coolify service) for graph storage

## 1) Coolify Service Setup

- Source: your Git repository
- Build Pack: Dockerfile
- Base Directory: `cognee`
- Dockerfile Location: `Dockerfile`
- Exposed Port: `8000`

The container starts `gunicorn` via `entrypoint.sh` and listens on `0.0.0.0:8000`.

## 2) Network Setup

Connect this Cognee service to the same Docker network used by your Qdrant and FalkorDB
services in Coolify (Connect to Predefined Network). This allows internal DNS names like
`qdrant` and `falkordb`.

## 3) Persistent Volume

Add a persistent volume in Coolify for Cognee local data:

- Container path: `/app/.cognee_data`

Optional second mount (if you want system files separated):

- Container path: `/app/.cognee_system`

The Dockerfile sets defaults:

- `DATA_ROOT_DIRECTORY=/app/.cognee_data`
- `SYSTEM_ROOT_DIRECTORY=/app/.cognee_system`

## 4) Required Environment Variables

### LLM

```dotenv
LLM_API_KEY=your_key
LLM_PROVIDER=openai
LLM_MODEL=openai/gpt-4o-mini
```

### Relational DB (Supabase Postgres)

```dotenv
DB_PROVIDER=postgres
DB_HOST=db.your-project-ref.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USERNAME=postgres
DB_PASSWORD=your_supabase_db_password
```

If your setup requires Supabase pooler, use `DB_PORT=6543`.

### Vector DB (Qdrant community adapter)

```dotenv
VECTOR_DB_PROVIDER=qdrant
VECTOR_DB_URL=http://qdrant:6333
VECTOR_DB_KEY=
VECTOR_DATASET_DATABASE_HANDLER=qdrant
```

### Graph DB (FalkorDB community adapter)

```dotenv
GRAPH_DATABASE_PROVIDER=falkor
GRAPH_DATABASE_URL=falkordb
GRAPH_DATABASE_PORT=6379
GRAPH_DATASET_DATABASE_HANDLER=falkor_graph_local
```

### Security + Runtime

```dotenv
ENVIRONMENT=production
HOST=0.0.0.0
CORS_ALLOWED_ORIGINS=https://your-app-domain.com
ACCEPT_LOCAL_FILE_PATH=False
ALLOW_HTTP_REQUESTS=True
REQUIRE_AUTHENTICATION=True
```

If your API is internal-only, tighten `CORS_ALLOWED_ORIGINS` accordingly.

## 5) Community Adapter Registration

The API now auto-registers community adapters at startup when providers/handlers indicate
Qdrant or FalkorDB usage:

- Qdrant: `VECTOR_DB_PROVIDER=qdrant` or `VECTOR_DATASET_DATABASE_HANDLER=qdrant`
- FalkorDB: `GRAPH_DATABASE_PROVIDER=falkor` / `VECTOR_DB_PROVIDER=falkor` or handler values

If the adapter package is missing, startup fails with a clear error message.

## 6) Deploy and Verify

1. Push changes to the branch tracked by Coolify.
2. Trigger Deploy in Coolify.
3. Check runtime logs for migration and startup success.
4. Verify health endpoint:

```bash
curl https://your-cognee-domain/health
```

Expected response contains API health status (HTTP 200).
