# Security Policy

LumiTrace is a prototype project, but the repository is maintained with public-release safety in mind.

## Supported Version

The `main` branch is the actively maintained branch.

## What Not To Commit

Never commit:

- `.env`
- API keys or access tokens
- local SQLite databases such as `dev_v4.db`
- generated vector files such as `movie_vectors*.json` or `final_boss_vectors*.json`
- model weights or array files such as `*.pt`, `*.pth`, `*.pkl`, `*.npy`, `*.npz`
- local IDE, agent, or scratch files

These files are ignored by `.gitignore`, but contributors should still review staged files before committing.

## Secret Handling

Runtime secrets are loaded from `.env` through environment variables. Public configuration should use `.env.example` only.

In the public demo flow, a user's TMDB API key can also be entered in the browser UI. That key is stored in browser `localStorage` and sent only to the local Flask proxy as a request header. Do not paste real keys into issues, screenshots, logs, or pull requests.

The backend health endpoint intentionally returns only readiness booleans and status strings. It must not expose API keys, private URLs, database contents, user passwords, or local filesystem paths.

## Reporting Security Issues

If you discover a security issue, please avoid posting sensitive details in a public issue. Share a minimal description of the problem and avoid including:

- real API keys
- user credentials
- local database records
- private service URLs
- generated vector files that contain private data

## Current Security Limitations

LumiTrace is currently a prototype. Known areas for future hardening include:

- stricter CORS configuration for deployed environments
- token-based authentication if the project becomes more than a local demo
- rate limiting for API proxy endpoints
- stronger validation for user-provided request payloads
