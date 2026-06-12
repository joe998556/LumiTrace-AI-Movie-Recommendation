# Operations Runbook

This runbook explains how to operate LumiTrace locally and how to diagnose the most common setup issues.

## Services

LumiTrace is split into two services:

```text
Flask backend     -> app.py, port 8080
BERT recommender  -> ai_engine/bert_service.py, port 5001
```

The Flask backend can run without the BERT service, but personalized recommendations need `REMOTE_SEARCH_URL` to point to a running BERT service.

## Local Startup

1. Install dependencies.

```bash
pip install -r requirements.txt
```

2. Create `.env`.

```bash
cp .env.example .env
```

3. Fill in local values.

```text
TMDB_API_KEY=your_tmdb_key
RAPID_API_KEY=your_rapidapi_key
REMOTE_SEARCH_URL=http://127.0.0.1:5001/search
OLLAMA_URL=
SSL_VERIFY=false
```

4. Run the setup checker.

```bash
python tools/check_setup.py
```

5. Start the Flask backend.

```bash
python app.py
```

6. Open the local app.

```text
http://localhost:8080
```

## Health Check

Use the backend health endpoint:

```text
http://localhost:8080/api/health
```

The response reports local readiness without exposing secrets. It should not include raw API keys, private service URLs, local database rows, or generated vector contents.

## BERT Recommendation Service

The BERT service needs a generated vector index:

```text
movie_vectors.json
```

or:

```text
final_boss_vectors.json
```

Generate the basic BERT vector index:

```bash
python ai_engine/generate_vectors.py
```

Start the BERT service:

```bash
python ai_engine/bert_service.py
```

Check service status:

```text
http://127.0.0.1:5001/status
```

## Common Issues

### Recommendations return empty results

Check:

- `REMOTE_SEARCH_URL` is set.
- `ai_engine/bert_service.py` is running.
- `movie_vectors.json` or `final_boss_vectors.json` exists in the project root.
- User favorites contain movie overviews.

### TMDB search does not work

Check:

- `TMDB_API_KEY` is present in `.env`.
- The Flask backend was restarted after editing `.env`.
- Network access to TMDB is available.

### Streaming links are incomplete

The project uses TMDB watch providers first, then attempts Streaming Availability data when configured. Some platforms or regions may only resolve to search pages instead of direct watch links.

### Do not commit local runtime files

Before committing, check:

```bash
git status --short --ignored
```

The following should remain ignored:

- `.env`
- `dev_v4.db`
- `.venv/`
- `.claude/`
- `movie_vectors.json`
- `final_boss_vectors.json`
