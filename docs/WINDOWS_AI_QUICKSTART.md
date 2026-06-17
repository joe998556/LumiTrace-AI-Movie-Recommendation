# Windows AI Quickstart

This guide helps non-technical users run the optional LumiTrace BERT recommendation server on a Windows PC and connect the Android app over the same Wi-Fi/LAN.

## What This Is For

Use this only if you want the Android **AI Recommend** page to use your own local BERT model.

You do not need this for normal app features such as:

- browsing TMDB movies
- searching movies
- marking movies as watched
- rating movies
- writing notes

## Before You Start

You need:

- Windows PC
- Android phone on the same Wi-Fi/LAN
- Python 3.10+
- TMDB API key

Apply for a TMDB API key first:

```text
https://www.themoviedb.org/settings/api
```

The setup script will ask you to paste this key. The key is used to download movie metadata and build local vectors.

## Easiest Setup

1. Download `LumiTrace-v1.0.4-release.apk` from the latest GitHub Release and install it on Android.
2. Download the Source code zip from the same Release.
3. Extract the zip on your Windows PC.
4. Double-click:

```text
LumiTrace-Windows-AI-Setup.bat
```

If you downloaded the BAT as a separate Release asset, put it inside the extracted LumiTrace folder before running it.

The script will:

- ask for your TMDB API key
- let you choose the data size
- install Python dependencies into `.venv`
- download TMDB movie data
- download/load the BERT embedding model
- build `movie_vectors.json`
- detect your LAN IP address
- show the endpoint to paste into the Android app
- start the BERT server on port `5001`

Do not share screenshots that show your TMDB API key.

## Data Size Choices

| Preset | Approx. movies | Best for |
| --- | ---: | --- |
| `demo` | 200 | Fast smoke test |
| `small` | 1,000 | First real run |
| `medium` | 5,000 | Better coverage |
| `large` | 15,000 | Long run |
| `xlarge` | 30,000 | GPU/overnight run |

More movies usually means better coverage, but setup takes longer.

## Phone Setup

When the script finishes building vectors, it prints something like:

```text
http://192.168.1.23:5001/search
```

On Android:

1. Open LumiTrace.
2. Open Settings.
3. Paste your TMDB API key.
4. Paste the endpoint into **Connect BERT gateway**.
5. Save setup.
6. Mark and rate a few watched movies.
7. Open **AI Recommend**.
8. Tap **Run AI recommendation**.

The PC window must stay open while the phone uses AI Recommend.

## Firewall Notes

The BAT can try to add a Windows Firewall rule for TCP `5001`.

If the phone cannot connect:

- make sure phone and PC are on the same Wi-Fi/LAN
- run the BAT as Administrator
- allow TCP `5001` in Windows Firewall
- check that the endpoint IP matches your PC LAN IP

## Security Notes

The LAN endpoint is intended for your home/lab Wi-Fi only.

For public internet use, put the BERT service behind:

```text
Android app -> HTTPS reverse proxy -> private BERT service
```

Do not put long-lived gateway tokens inside the APK.
