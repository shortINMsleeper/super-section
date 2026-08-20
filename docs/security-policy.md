# Browser security policy

## Threat model

Treat the public URL as discoverable by scanners and bots. Security must not depend on obscurity.

## Enforced in the current static site

`index.html` uses a CSP meta policy that denies network capabilities by default and only permits the resources the page currently needs:

- scripts: same-origin files only
- images: same-origin files only
- styles: same-origin plus the existing inline stylesheet
- API/network connections: blocked
- frames, objects, media and workers: blocked
- `<base>` changes and form submission: blocked
- inline script attributes are blocked

The page also uses `Referrer-Policy: no-referrer` via a meta tag.

The interactive JavaScript lives in `assets/site.js` rather than an inline `<script>`, so `script-src` does not require `unsafe-inline`.

## GitHub Pages limitation

GitHub Pages does not provide this repository with arbitrary custom HTTP response headers. Some important protections therefore cannot be reliably enforced by HTML meta tags, including:

- `X-Content-Type-Options: nosniff`
- `Permissions-Policy`
- CSP `frame-ancestors` (clickjacking protection)

If the project later needs authenticated pages, API/LLM features, sensitive user data, or stronger browser isolation, move the frontend behind a host/CDN/reverse proxy that can set response headers. At that point add at least `X-Content-Type-Options: nosniff`, a restrictive `Permissions-Policy`, and CSP `frame-ancestors 'none'` (or the minimum required allowlist).

## Future API/LLM rule

Never place API keys or service credentials in browser-delivered HTML, JavaScript, JSON, source maps, or other public assets. Browser requests must go to an authenticated backend that owns the provider credential and applies server-side rate limits, quotas, model allowlists, token/input limits, timeouts, budget controls, logging redaction, and a kill switch.

CORS or Origin checks alone are not authentication.
