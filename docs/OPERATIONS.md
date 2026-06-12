# Operations Runbook

This runbook explains how to operate LumiTrace locally and how to diagnose the most common setup issues.

## Services

LumiTrace has a simple public demo path and an optional advanced BERT path:

```text
Public demo backend   -> app.py, port 8080
Optional BERT service -> ai_engine/bert_service.py, port 5001
```

The public demo does not require registration, a database, or a generated vector file. Users paste their own TMDB API key into the web UI, save favorite movies in browser localStorage, and request recommendations from the main page.

## Local Startup

1. Install dependencies.

```bash
pip install -r requirements.txt
```

2. Optional: create `.env`.

```bash
cp .env.example .env
```

3. Optional: fill in local values. The public demo can also accept a TMDB key directly in the web UI.

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

7. Paste a TMDB API key into the page, load trending movies, save favorites, and click "你適合看以下這些".

## Health Check

Use the backend health endpoint:

```text
http://localhost:8080/api/health
```

The response reports local readiness without exposing secrets. It should not include raw API keys, private service URLs, local database rows, or generated vector contents.

## BERT Recommendation Service

The public demo does not need the BERT service. The BERT service is for advanced semantic recommendation experiments and needs a generated vector index:

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

- A TMDB API key was entered in the UI.
- At least one movie has been saved as a favorite.
- Favorite movies include genre IDs from TMDB.
- Network access to TMDB is available.

### TMDB search does not work

Check:

- A TMDB API key was entered in the UI, or `TMDB_API_KEY` is present in `.env`.
- The Flask backend is running on port 8080.
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
