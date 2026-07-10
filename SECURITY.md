# Security Policy

## Supported Version

Security fixes target the latest commit on `main`.

## Reporting

Use GitHub private vulnerability reporting when it is available for this repository. Do not include API keys, gateway tokens, private URLs, user taste exports, or working exploit details in a public issue.

For a non-sensitive hardening suggestion, open a normal GitHub issue and label it `security`.

## Deployment Boundary

LumiTrace is a reference implementation, not an authentication gateway. An Internet-facing deployment should use TLS, an edge rate limiter, bounded request bodies, monitored logs, and a private origin whenever possible.

Never place a permanent shared secret in browser JavaScript. A public endpoint must be treated as discoverable and protected through limits and isolation rather than URL secrecy.
