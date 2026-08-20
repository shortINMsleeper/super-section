# GitHub Pages runbook

## Public URL

- `https://shortinmsleeper.github.io/super-section/`

## Deployment flow

1. Merge changes to `main`.
2. `.github/workflows/pages.yml` runs the source quality gate.
3. The workflow builds a minimal Pages artifact containing only `index.html` and `assets/ashikaga-01.jpg` through `assets/ashikaga-04.jpg`.
4. The artifact is deployed to the `github-pages` environment.
5. `scripts/smoke_live.py` checks the live URL, the Ashikaga name, absence of Music / PV / Video headings, and HTTP responses for all four images.

## Initial repository setting

Repository Settings → Pages → Build and deployment → Source must be set to **GitHub Actions**.

## Recovery

If deployment fails after a repository setting change, make a new `main` push (or manually run the Pages workflow) and inspect the `preflight`, `deploy`, and `smoke` jobs in that order.

## Security boundary

- Normal jobs use read-only repository contents permission.
- `pages: write` and `id-token: write` are limited to the deploy job.
- Pages-related third-party actions are pinned to commit SHAs.
- The deployed artifact excludes repository scripts and workflow files.
