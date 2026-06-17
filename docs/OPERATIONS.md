# Operations Runbook

This runbook explains how to operate LumiTrace locally and how to diagnose the most common setup issues.

## Services

LumiTrace has a simple public demo path and an optional advanced BERT path:

```text
Public demo backend   -> app.py, port 8080
Optional BERT service -> ai_engine/bert_service.py, port 5001
```

The public demo does not require registration, a database, or a generated vector file. Users paste their own TMDB API key into the web UI, save favorite movies in browser localStorage, and request recommendations from the main page.

When `REMOTE_SEARCH_URL` is configured, the web demo first asks the BERT semantic service for recommendations. If the service is not configured or unavailable, the UI falls back to TMDB metadata ranking.

Generated vector indexes are service-side files. They are not loaded into browser `localStorage`.

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
LUMITRACE_VECTOR_FILE=movie_vectors.json
LUMITRACE_DEVICE=auto
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

7. Paste a TMDB API key into the page, load trending movies, save favorites, and click "Show My Recommendations".

## Health Check

Use the backend health endpoint:

```text
http://localhost:8080/api/health
```

The response reports local readiness without exposing secrets. It should not include raw API keys, private service URLs, local database rows, generated vector contents, or local filesystem paths.

## BERT Recommendation Service

The public demo does not need the BERT service. The BERT service is for advanced semantic recommendation experiments and needs a generated vector index:

```text
movie_vectors.json
```

or:

```text
final_boss_vectors.json
```

Generate the BERT vector index with the interactive English bootstrapper:

```bash
python tools/bootstrap_recommender.py
```

Preset guide:

| Preset | Approx. movies | Notes |
| --- | ---: | --- |
| `demo` | 200 | Fast smoke test |
| `small` | 1,000 | Practical first local index |
| `medium` | 5,000 | Better coverage, GPU recommended |
| `large` | 15,000 | Long build |
| `xlarge` | 30,000 | Overnight/GPU build |

Non-interactive example:

```bash
python tools/bootstrap_recommender.py --preset small --tmdb-key YOUR_TMDB_KEY
```

Windows APK users should prefer the guided setup:

```text
LumiTrace-Windows-AI-Setup.bat
```

Developer-only vector setup still supports:

```text
setup_recommender.bat
```

Start the BERT service:

```bash
python ai_engine/bert_service.py
```

Check service status:

```text
http://127.0.0.1:5001/status
```

Set the web backend to use the BERT service:

```text
REMOTE_SEARCH_URL=http://127.0.0.1:5001/search
```

Then restart:

```bash
python app.py
```

## Running BERT On A Separate GPU Machine

On the GPU machine:

```bash
pip install -r requirements.txt
python tools/bootstrap_recommender.py --preset medium --device cuda
python ai_engine/bert_service.py --host 0.0.0.0 --port 5001
```

On the backend machine, point `.env` to the GPU machine's LAN IP:

```text
REMOTE_SEARCH_URL=http://GPU_PC_IP:5001/search
```

This keeps the lightweight public backend on a CPU machine while the heavier embedding/index service runs on the GPU machine.

The bootstrapper defaults to English TMDB metadata (`en-US`) so generated vectors use English titles and overviews when TMDB provides them.

## Common Issues

### Recommendations return empty results

Check:

- A TMDB API key was entered in the UI.
- At least one movie has been saved as a favorite.
- Favorite movies include genre IDs or overviews from TMDB.
- Network access to TMDB is available.
- If using BERT mode, `REMOTE_SEARCH_URL` points to a running BERT service.

### TMDB search does not work

Check:

- A TMDB API key was entered in the UI, or `TMDB_API_KEY` is present in `.env`.
- The Flask backend is running on port 8080.
- Network access to TMDB is available.

### BERT mode is slow

Check:

- Use `--preset demo` or `--preset small` for the first run.
- Use `--device cuda` on a CUDA-capable GPU machine.
- Keep `movie_vectors.json` on a fast local disk.
- Use the CPU backend with a remote GPU BERT service if the machines are on the same LAN.
- The current service uses a linear Torch tensor similarity scan. If you need larger indexes or concurrent public traffic, move retrieval to Faiss, HNSWLib, SQLite vector extensions, or another ANN/vector index.

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
- `movie_vectors*.json`
- `final_boss_vectors*.json`
