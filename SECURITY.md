# Security Policy

## Supported Version

Security fixes target the latest GitHub Release and the current `main` branch.

## Reporting

Use GitHub private vulnerability reporting when it is available. Do not place API keys, Trakt credentials, OAuth tokens, personal taste exports, signing material, or working exploit details in a public issue.

Non-sensitive hardening suggestions may be filed as normal issues.

## Application Boundary

LumiTrace has no account or first-party backend. The Android app communicates directly with:

- TMDB over HTTPS after the user enters a personal API key;
- Trakt over HTTPS only after the user configures and authorizes that optional integration;
- Google AI Edge Gallery through an explicit Android intent when the user requests an explanation.

Watched movies, ratings, journal notes, profiles, recommendation traces, and credentials are stored in app-private Android storage. The app requests AndroidX Security encrypted preferences and falls back to app-private preferences if encrypted storage cannot be initialized on a device. Android backup is disabled.

## User Responsibilities

- Obtain API credentials from the provider and follow its current terms.
- Do not share screenshots or exported files that expose credentials or private notes.
- Verify the SHA-256 checksum attached to a GitHub Release when installing outside an app store.
- Treat a rooted or otherwise compromised phone as outside the app's protection boundary.

The repository never needs a TMDB key to compile. A key found in source code, an issue, a build log, or a release asset should be considered exposed and rotated immediately.
