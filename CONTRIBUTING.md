# Contributing To LumiTrace

Thanks for your interest in LumiTrace. The project is an active prototype focused on AI-powered movie recommendation with BERT semantic embeddings.

## Good First Contribution Areas

- Improve documentation for setup, model usage, or recommendation flow.
- Add screenshots or a short demo walkthrough.
- Add a small sample vector index for smoke testing.
- Improve error messages when `movie_vectors.json` is missing.
- Improve recommendation explanations and ranking diagnostics.
- Add tests around backend API behavior.

## Development Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local `.env` from the example file:

```bash
cp .env.example .env
```

Do not commit `.env` or any private API keys.

Run the Flask backend:

```bash
python app.py
```

Run the BERT service separately when working on recommendations:

```bash
python ai_engine/bert_service.py
```

## Recommendation Pipeline Notes

The recommendation flow is documented in `ALGORITHM.md`. Changes to ranking behavior should explain which stage is affected:

- movie vector generation
- user taste profile
- semantic similarity search
- hybrid ranking
- filtering or penalties
- recommendation explanations

## Pull Request Checklist

Before opening a pull request:

- Keep generated files out of Git.
- Do not commit `.env`, API keys, local databases, model files, or vector files.
- Update README, ALGORITHM, ROADMAP, or CHANGELOG when behavior changes.
- Add notes about local testing or explain why testing was not run.

## Security

If you find a security issue, do not open a public issue with secrets, credentials, local database contents, or private service URLs. See `SECURITY.md`.
