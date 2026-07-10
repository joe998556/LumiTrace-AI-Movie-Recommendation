# LumiTrace

[![CI](https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation/actions/workflows/ci.yml/badge.svg)](https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-14b8a6.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-5eead4.svg)](https://www.python.org/)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/joe998556/LumiTrace-AI-Movie-Recommendation?quickstart=1)

**A local-first semantic movie taste engine built around what you watched and how you rated it.**

LumiTrace combines precomputed sentence-transformer movie embeddings, transparent rating signals, metadata re-ranking, and a polished Web client. It requires no LumiTrace account, keeps the taste profile in the browser, and can run its main recommendation path on an ordinary CPU.

## Why This Architecture

Most visitors should not have to download or run a Transformer model. LumiTrace separates expensive preparation from inexpensive recommendation:

```text
Offline, once                                Online, per recommendation
licensed catalog text -> encoder -> index    movie IDs + ratings -> vector lookup
                                             -> one matrix multiply -> re-rank
```

For the normal **watched + 1-10 rating** flow, the server never runs an encoder at request time. The catalog is already encoded. The online service only looks up saved movie vectors, forms a taste profile, retrieves candidates, applies low-rating penalties to the shortlist, and returns movie IDs with evidence.

This gives the project three useful modes:

| Mode | Setup | Runtime | Best for |
|---|---|---|---|
| Bundled demo | 1,000-movie MovieLens index | CPU, no Transformer loaded | Immediate clone-and-run AI preview |
| Metadata | No usable seed in the index | Browser + configured movie API | Explicit fallback and browsing |
| Full semantic | Same index + matching encoder | CPU/GPU encoder loaded on demand | Optional free-text scene playlists |

## Product Experience

- First Signal onboarding for a quick initial taste profile
- Saved films, 1-10 ratings, notes, and More/Less feedback
- Explainable recommendations with source films and rating evidence
- Familiar-to-Surprise diversity control and one-redraw roulette
- Tonight, Two People, Taste Map, Journal, and comparison tools
- Portable JSON export/import without API keys
- Optional OpenAI-compatible narration on trusted self-hosts

## Five-Minute Local Preview

For the lowest-friction preview, use the **Open in GitHub Codespaces** badge above. The container builds the app, starts the bundled semantic index, forwards port `7860`, and opens the Web client. No model download or vector generation is required.

For poster-backed browsing, create a TMDB API key at <https://www.themoviedb.org/settings/api> after reviewing the provider's current terms.

```powershell
git clone https://github.com/joe998556/LumiTrace-AI-Movie-Recommendation.git
cd LumiTrace-AI-Movie-Recommendation
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-demo.txt
Copy-Item .env.example .env
python app.py
```

Open <http://localhost:8080>, enter the TMDB key in **Settings**, and start saving and rating movies. Browser requests made with your key go directly to TMDB; the LumiTrace backend does not receive it.

The repository already contains a compact 1,000-movie MovieLens/MiniLM index, so watched-and-rated recommendations work without downloading a model or building vectors. Poster metadata is hydrated in the browser with the user's own provider key.

## Bundled AI Demo

`demo_index/` is generated from MovieLens Latest Small using title, genre, and community-tag text encoded by `sentence-transformers/all-MiniLM-L6-v2`:

```text
demo_index/
  manifest.json    model, dimensions, source, license pointer
  movies.json      MovieLens-derived ranking metadata
  vectors.npy      1,000 normalized float16 vectors (~0.8 MB)
  MOVIELENS_README.txt  upstream data terms, included unchanged
```

Rebuild it reproducibly with:

```powershell
python -m pip install -r requirements.txt
python tools\build_movielens_demo.py --limit 1000 --output demo_index
```

MovieLens data carries separate research/non-commercial conditions; see [DATA_LICENSE.md](DATA_LICENSE.md). The MIT software license does not replace the data license.

## Private Full Index

LumiTrace still supports private 30,000-movie indexes. The compact format avoids parsing a 500 MB float-filled JSON document. For BGE-M3, a 30,000 x 1,024 float16 matrix uses about 61 MB before metadata; 768-dimensional legacy indexes are smaller.

The repository deliberately does **not** distribute the existing TMDB-derived 30k index. TMDB's current API terms contain specific AI/ML restrictions. Use the API-based builder only if you have reviewed the current terms and obtained any permission required for your use:

```powershell
python -m pip install -r requirements.txt
python tools\bootstrap_recommender.py --preset xlarge --tmdb-key YOUR_TMDB_KEY --acknowledge-data-rights
```

The builder writes `movie_index/`. Presets are `demo` (200), `small` (1,000), `medium` (5,000), `large` (15,000), and `xlarge` (30,000).

### Migrate an Existing JSON Index

```powershell
python tools\convert_vector_index.py movie_vectors.json --output movie_index --model YOUR_ORIGINAL_MODEL
```

Legacy JSON does not record its encoder reliably, so conversion requires the original model name. Legacy JSON remains directly readable, so migration does not have to happen immediately.

## Docker

```powershell
docker compose up --build
```

Open <http://localhost:8080>. The bundled demo index is active immediately. The image runs one Web process with the vector engine in-process, uses one worker to avoid duplicating the index in RAM, and disables live text encoding by default.

To mount a private full index instead:

```powershell
$env:LUMITRACE_INDEX_DIR = ".\movie_index"
$env:LUMITRACE_MIN_VOTE_COUNT = "100"
docker compose up --build
```

### Optional LLM Narration

Recommendation ranking never depends on an LLM. A trusted self-host may let its own users supply an OpenAI-compatible narrator by setting:

```text
LUMITRACE_ALLOW_CLIENT_LLM=true
```

Local Ollama or LM Studio targets additionally require `LUMITRACE_ALLOW_PRIVATE_LLM=true`. Do not enable either option on an anonymous public demo that should never receive visitor API keys.

## Publish a Safe Live Demo

The recommended public setup is a [Docker-based Hugging Face Space](https://huggingface.co/docs/hub/en/spaces-sdks-docker) or another small CPU container host. The repository supplies one container for both the UI and API, and its licensed demo index starts without extra model assets.

For an authorized custom index, package it separately:

```powershell
python tools\convert_vector_index.py movie_index --output movie_index --archive lumitrace-index-v1.zip
```

Upload the archive only to storage whose terms permit your dataset. Keep it private if redistribution is not appropriate, then configure:

```text
LUMITRACE_INDEX_URL=https://storage.example/lumitrace-index-v1.zip
LUMITRACE_INDEX_SHA256=<checksum printed by the packaging command>
LUMITRACE_VECTOR_FILE=movie_index
LUMITRACE_TEXT_SEARCH=disabled
LUMITRACE_MIN_VOTE_COUNT=100
LOCK_REMOTE_SEARCH_URL=true
```

The container verifies the archive checksum and validates its manifest before serving it. Hugging Face Docker Spaces support custom FastAPI/Flask containers and optional hardware upgrades; free hardware may sleep when idle.

For a separate static frontend, set `DEPLOYED_API_BASE` in `config.js` (or define `window.LUMITRACE_API_BASE` before it loads) and allow only that origin through `LUMITRACE_ALLOWED_ORIGINS`. A same-origin deployment needs no override.

For an Internet-facing service, place [Cloudflare rate limiting](https://developers.cloudflare.com/workers/runtime-apis/bindings/rate-limit/) or an equivalent gateway in front of the container. LumiTrace also enforces a defensive local request limit, but edge rate limiting should remain the primary protection.

## Recommendation API

The stable endpoint accepts aligned records instead of fragile parallel arrays:

```http
POST /api/recommendations
Content-Type: application/json

{
  "items": [
    { "tmdb_id": 329865, "rating": 9, "genre_ids": [18, 878] },
    { "tmdb_id": 157336, "rating": 8.5, "genre_ids": [12, 18, 878] }
  ],
  "exclude_ids": [329865, 157336],
  "top_k": 12,
  "diversity": 0.55
}
```

See [openapi.yaml](openapi.yaml) for the complete contract. The old `/api/semantic-recommendations` and standalone `/search` routes remain available for existing clients.

## Privacy and Security Defaults

- Favorites, ratings, notes, and feedback remain in browser storage.
- There is no account system or server-side taste-profile synchronization.
- TMDB keys are sent directly from the browser to TMDB when supplied by a user.
- `.env`, private vector indexes, databases, generated archives, and model files are ignored by Git; only the separately licensed demo index is tracked.
- Public deployments lock browser-selected proxy targets by default.
- Public deployments reject client-supplied LLM credentials by default.
- API bodies are capped at 64 KiB; IDs, ratings, languages, list sizes, and `top_k` are bounded.
- Gateway tokens stay server-side and are compared in constant time.
- Remote index archives require SHA-256 verification and safe ZIP extraction.

## Data and Provider Terms

- Software source: [MIT License](LICENSE).
- Bundled demo transformation: [MovieLens conditions and citation](DATA_LICENSE.md).
- MiniLM model: Apache-2.0 according to its model card.
- TMDB requests and content: subject to the [current TMDB API Terms of Use](https://www.themoviedb.org/api-terms-of-use). LumiTrace does not distribute a TMDB-derived vector index.

This repository is a non-commercial reference project, not legal advice. Operators are responsible for confirming that their data source, model, cache duration, and deployment comply with the applicable terms.

## Validation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
python -m py_compile app.py ai_engine\bert_service.py ai_engine\index_format.py tools\build_movielens_demo.py
node tests\test_recommendation_core.js
node tests\test_experience_contract.js
node tests\test_inline_scripts.js
```

The tests include a deterministic miniature vector index, an ID-and-rating recommendation check, API sanitization, rate limiting, privacy boundaries, and frontend contracts.

## Project Map

```text
app.py                          Web app, public API, rate limits, local/remote engine
ai_engine/bert_service.py       Vector retrieval, feedback penalty, evidence, text option
ai_engine/index_format.py       Safe compact index reader/writer
demo_index/                     Licensed, ready-to-run MovieLens semantic demo
DATA_LICENSE.md                 Demo-data provenance, conditions, and citation
tools/build_movielens_demo.py   Reproducible MovieLens/MiniLM demo-index builder
tools/bootstrap_recommender.py  TMDB downloader and offline BERT index builder
tools/convert_vector_index.py   JSON migration and deployable archive packaging
Dockerfile / compose.yaml       One-container public demo and self-hosting
.devcontainer/                  One-click GitHub Codespaces preview
recommendation-core.js          Browser taste state and API contract
experience.js                   Onboarding, taste tools, and portable data controls
openapi.yaml                    Public recommendation API specification
```

Contributions are welcome; start with [CONTRIBUTING.md](CONTRIBUTING.md). Security concerns belong in [SECURITY.md](SECURITY.md).

Movie metadata and posters are provided by TMDB. This product uses the TMDB API but is not endorsed, certified, or otherwise approved by TMDB.

Released under the [MIT License](LICENSE).
