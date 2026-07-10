# Contributing to LumiTrace

Thanks for helping improve a transparent, self-hostable movie recommender.

## Start Here

1. Fork and clone the repository.
2. Create a virtual environment and install `requirements.txt`.
3. Copy `.env.example` to `.env`; never commit the resulting file.
4. Run `python app.py` and open `http://localhost:8080`.
5. Run all checks before opening a pull request.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
python -m py_compile app.py ai_engine\bert_service.py ai_engine\index_format.py
node tests\test_recommendation_core.js
node tests\test_experience_contract.js
```

## Good First Contributions

- Add deterministic recommendation fixtures and regression cases.
- Improve accessibility and keyboard behavior without changing the visual identity.
- Add translations while keeping English as the source copy.
- Improve Docker and CPU deployment documentation.
- Add adapters for independently hosted, license-compatible movie indexes.

## Pull Requests

- Keep changes focused and explain observable behavior.
- Add tests for recommendation, API, storage, or security changes.
- Do not commit API keys, gateway tokens, internal endpoints, model caches, vector indexes, databases, or personal taste exports.
- Do not add generated datasets unless their redistribution terms are documented.
- Preserve the local-first default: taste history should not leave the browser without an explicit, reviewable feature.

Bug reports should include the operating system, Python version, browser, deployment mode, and a sanitized error message.
