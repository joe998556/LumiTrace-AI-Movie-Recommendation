# Security Policy

LumiTrace is designed so public source builds do not contain private credentials or private infrastructure details.

## Do Not Commit

- TMDB API keys
- AI gateway tokens
- IIS rewrite secrets
- server IP allowlists
- Android release keystores
- `local.properties`
- `secrets.properties`
- generated APK/AAB files

## AI Gateway Guidance

The Android app may know a public HTTPS gateway URL, but it must not contain a long-lived token. Put gateway authentication at the reverse proxy or backend layer instead.

Recommended deployment shape:

```text
Android app -> HTTPS reverse proxy -> private BERT service
```

The reverse proxy can add private headers, apply rate limits, and hide the internal model host.

## Reporting Issues

Do not open a public issue containing live API keys, gateway tokens, private server IP addresses, or screenshots that reveal infrastructure details.
