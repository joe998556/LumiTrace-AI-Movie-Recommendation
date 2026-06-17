# LumiTrace Android v1.0.1

This release makes LumiTrace easier for public users to try with their own Windows PC and Android phone.

## Highlights

- Android APK can connect to a private LAN BERT endpoint such as `http://192.168.1.23:5001/search`.
- Added `LumiTrace-Windows-AI-Setup.bat` for guided Windows setup.
- The BAT reminds users to apply for a TMDB API key, asks for the key, and does not commit it to Git.
- Users can choose data size: `demo`, `small`, `medium`, `large`, or `xlarge`.
- The setup script builds `movie_vectors.json`, detects the PC LAN IP, prints the phone endpoint, and starts the BERT server.
- Updated the Android setup copy so Settings clearly supports local PC endpoints and HTTPS gateways.
- No embedded lab endpoint, fixed server IP, gateway token, TMDB key, APK signing key, or private infrastructure detail.

## First-Time User Flow

1. Apply for a TMDB API key:

```text
https://www.themoviedb.org/settings/api
```

2. Install:

```text
LumiTrace-v1.0.1-release.apk
```

3. Download the Source code zip from this release and extract it on Windows.
4. Double-click:

```text
LumiTrace-Windows-AI-Setup.bat
```

5. Paste your TMDB API key.
6. Choose the data size.
7. Wait for the BERT vectors to build.
8. Copy the endpoint printed by the BAT, for example:

```text
http://192.168.1.23:5001/search
```

9. In the Android app, open Settings and paste:

- your TMDB API key
- the BERT endpoint printed by the BAT

10. Mark and rate watched movies, then open **AI Recommend**.

The Windows PC and Android phone must be on the same Wi-Fi/LAN. Keep the BERT server window open while using AI recommendations.

## Data Size Guide

| Preset | Approx. movies | Best for |
| --- | ---: | --- |
| `demo` | 200 | Fast smoke test |
| `small` | 1,000 | First real run |
| `medium` | 5,000 | Better coverage |
| `large` | 15,000 | Long run |
| `xlarge` | 30,000 | GPU/overnight run |

## Security

Private LAN endpoints are intended for local testing only.

For public internet access, use:

```text
Android app -> HTTPS reverse proxy -> private BERT service
```

Do not put long-lived gateway tokens in the APK.
