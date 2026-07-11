# Contributing to LumiTrace

LumiTrace is an Android-first, local-only movie taste engine. Contributions should improve the app while preserving its simple public contract: install the APK, enter a personal TMDB key, and keep taste data on the device.

## Development Setup

1. Fork and clone the repository.
2. Open the repository root in Android Studio.
3. Use Android Studio's bundled JDK and install Android SDK 36 when prompted.
4. Let Gradle sync, then run the `app` configuration on an emulator or connected Android device.
5. Enter your own TMDB API key inside the app. Never put it in source code or Gradle files.

Command-line checks on Windows:

```powershell
.\gradlew.bat :app:testDebugUnitTest :app:lintDebug :app:assembleDebug
```

## Good First Contributions

- Add deterministic ranking fixtures and recommendation regression tests.
- Improve accessibility labels, contrast, focus order, and large-text behavior.
- Improve empty, offline, and provider-error states.
- Add UI tests for profile, rating, Tonight, and settings workflows.
- Clarify MovieLens data provenance or Android build documentation.

## Product Boundaries

- Do not add a required LumiTrace backend, account, analytics collector, or hidden endpoint.
- Do not commit API keys, OAuth tokens, signing keys, taste exports, or private URLs.
- Do not silently upload watched movies, ratings, notes, or profiles.
- Keep Trakt and AI Edge Gallery optional and explicitly initiated by the user.
- Do not add generated datasets unless redistribution terms and provenance are documented.
- Preserve the direct TMDB model: the user supplies a key and the app calls TMDB over HTTPS.

## Pull Requests

- Keep each change focused and describe its visible behavior.
- Add unit or instrumentation coverage when ranking, storage, networking, or navigation changes.
- Include Android version, device or emulator, and sanitized reproduction steps for bug fixes.
- Run the full Gradle command above before requesting review.

Bug reports and feature proposals are available through the repository issue templates.
