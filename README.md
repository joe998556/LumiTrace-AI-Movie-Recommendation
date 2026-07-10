# LumiTrace

LumiTrace is a local-first movie taste engine for the Web. It turns watched films, 1-10 ratings, immediate feedback, and optional free-text prompts into an explainable recommendation list without bundling an API key, a private endpoint, or a user account system.

## What You Can Do

- **First Signal**: on first use, rate ten familiar films with Like, Not for me, or Not seen to create a starting taste profile.
- **Semantic recommendations**: retrieve candidates from a self-hosted BERT vector index, then balance familiar matches and surprising discoveries.
- **Grounded reasons**: show the saved films, genres, rating signals, and low-rated similarities behind each recommendation. An optional LLM only narrates that supplied evidence.
- **Taste tools**: use Tonight, Two people, Taste map, Journal, comparison, More/Less like this, and a one-redraw roulette pick.
- **Private taste data**: keep favorites, ratings, notes, and feedback in the browser; export or import a portable JSON taste file without exporting API keys.

## Run Locally

Create a TMDB API key at <https://www.themoviedb.org/settings/api>, then:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python app.py
```

Open <http://localhost:8080>, then add your TMDB key in **Settings**.

The metadata path works immediately. It ranks TMDB discovery results from your saved films and ratings even when the optional semantic service is not running.

## Enable Semantic Retrieval

Build a local movie-vector index. The presets trade setup time and disk use for catalog coverage:

```powershell
python tools\bootstrap_recommender.py --preset demo --tmdb-key YOUR_TMDB_KEY
python ai_engine\bert_service.py --host 127.0.0.1 --port 5001 --vectors movie_vectors.json
```

Then add this to your untracked `.env` and restart the Web backend:

```text
REMOTE_SEARCH_URL=http://127.0.0.1:5001/search
LOCK_REMOTE_SEARCH_URL=true
```

`movie_vectors.json` is generated locally and ignored by Git. `demo` is suitable for a smoke test; `small`, `medium`, `large`, and `xlarge` build progressively broader catalogs.
The vector builder and service must use the same embedding model. LumiTrace validates the vector dimension at startup and gives a rebuild message instead of failing during a recommendation request.

## Optional LLM Narration

Settings accepts an OpenAI-compatible URL, API key, and model name. The key lives in `sessionStorage` by default and disappears when the browser session ends. A user can explicitly choose **Remember this key on this device** to store it locally.

The LLM receives only the already-computed recommendation evidence and is asked for a short spoiler-free explanation. It never chooses, filters, or reorders films.

For public deployments, private and loopback LLM targets are rejected by default. A local self-host may deliberately enable its own Ollama or LM Studio endpoint with:

```text
LUMITRACE_ALLOW_PRIVATE_LLM=true
```

## How Recommendations Work

1. The browser collects saved films, 1-10 ratings, and direct More/Less feedback.
2. The optional semantic service loads one normalized BERT movie-vector matrix at startup.
3. Positive signals (`6-10`) form a weighted taste center; `5` stays neutral.
4. The service uses one vectorized Torch matrix multiplication and a short candidate list.
5. Low ratings (`1-4`) are handled as a post-ranking similarity penalty, never as a negative semantic vector.
6. A diversity pass reduces repeated genres, languages, and franchises according to the Familiar-to-Surprise control.

See [ALGORITHM.md](ALGORITHM.md) for the precise ranking and evidence rules.

## Security Defaults

- `.env`, vector indexes, local databases, and generated downloads are ignored by Git.
- The public backend locks `REMOTE_SEARCH_URL` by default, so a browser cannot turn it into an arbitrary request proxy.
- When the BERT gateway requires a header, set `REMOTE_SEARCH_TOKEN` only in `.env`; the browser never receives it.
- The health endpoint reports configuration booleans only, never keys, tokens, or host secrets.

## Validate

```powershell
.\.venv\Scripts\python.exe -m pytest -q
python -m py_compile app.py ai_engine\bert_service.py tools\bootstrap_recommender.py
node --check script.js
node --check recommendation-core.js
node --check experience.js
```

## Project Map

```text
app.py                         Flask Web and proxy backend
ai_engine/bert_service.py      Lite semantic retrieval and evidence API
tools/bootstrap_recommender.py TMDB downloader and vector builder
recommendation-core.js         Shared browser taste and recommendation helpers
experience.js                  Onboarding, taste tools, import/export, and modes
index.html                     Main Web workspace
favorites.html                 Saved-film collection
settings.html                  TMDB, BERT, and optional LLM settings
```

Movie metadata and posters are provided by TMDB. This product uses the TMDB API but is not endorsed, certified, or otherwise approved by TMDB.
