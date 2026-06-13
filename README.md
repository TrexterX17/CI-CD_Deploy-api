# IP Info API

A small Flask API that returns basic metadata about an IP address — whether it's private, a loopback address, multicast, and which IP version it is. The application is intentionally simple; the point of this repo is to demonstrate a CI/CD pipeline built with GitHub Actions with security baked in at each stage.

---

## What the App Does

Send a GET request to `/ip/<address>` and get back a JSON object:

```
GET /ip/8.8.8.8

{
  "ip": "8.8.8.8",
  "version": "IPv4",
  "is_private": false,
  "is_loopback": false,
  "is_multicast": false
}
```

There's also a `/health` endpoint for liveness checks and a root `/` endpoint that returns the API version.

---

## Pipeline Overview

The pipeline lives in `.github/workflows/` and is split across two workflow files:

### `ci.yml` — Main CI/CD Pipeline

This runs on every push and pull request to `main`. It has six jobs:

| Job | What it does |
|---|---|
| **test** | Runs the pytest suite with coverage reporting |
| **lint** | Checks code style with `ruff` |
| **dependency-scan** | Audits `requirements.txt` for known CVEs using `pip-audit` |
| **sast** | Runs `bandit` to catch common Python security issues (hardcoded credentials, use of `eval`, insecure subprocess calls, etc.) |
| **build-and-push** | Builds the Docker image and pushes it to GitHub Container Registry — only runs on `main` after all four checks above pass |
| **image-scan** | Runs `trivy` against the freshly pushed image to catch OS-level and library-level vulnerabilities — results are uploaded to the GitHub Security tab as SARIF |

The build-and-push job only triggers if all the earlier jobs pass and the event is a direct push to `main` (not a pull request). This means a PR can't introduce broken or insecure code and get it built into an image.

### `secret-scan.yml` — Secret Detection

Runs `gitleaks` on every push and pull request. This checks the full git history (not just the diff) for accidentally committed secrets — API keys, tokens, passwords, etc. Keeping this as a separate workflow makes it easier to see secret-scan results independently from the rest of CI.

---

## Security Choices and Reasoning

**Dependency scanning with `pip-audit`**  
Third-party packages are a common attack surface. `pip-audit` checks every dependency against the OSV (Open Source Vulnerabilities) database and fails the build if anything has a known CVE. I chose `pip-audit` over alternatives like `safety` because it doesn't require an API key and works cleanly in CI without extra configuration.

**Static analysis with `bandit`**  
Bandit is a Python-specific SAST tool that flags things like use of `assert` for security checks, shell injection risks, and hardcoded secrets. Running it at medium severity (`-ll`) avoids noise from low-severity stylistic warnings while still catching real issues.

**Secret scanning with `gitleaks`**  
Secrets that get committed even briefly are a risk — they can live in git history even after deletion. Gitleaks scans the entire commit history on each run, not just changed files, which catches things that were committed and then removed.

**Container image scanning with `trivy`**  
Even if the application code is clean, the base image can introduce vulnerabilities. Trivy checks both OS packages and Python libraries inside the built image for CVEs at CRITICAL and HIGH severity. Results are uploaded as SARIF so they appear directly in GitHub's Security tab rather than just in log output.

**Non-root container user**  
The Dockerfile creates a dedicated system user (`appuser`) and switches to it before the app starts. Running as root inside a container is unnecessary and increases the blast radius if the container is compromised.

**Least-privilege workflow permissions**  
Each workflow and job sets `permissions` explicitly rather than relying on defaults. Jobs that only need to read code request `contents: read`; only the build job requests `packages: write` for pushing to GHCR.

**Gate on security jobs before build**  
The `build-and-push` job uses `needs: [test, lint, dependency-scan, sast]`, so the image is never built or published if any of those checks fail.

---

## Running Locally

**Without Docker:**

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

**With Docker:**

```bash
docker build -t ipinfo-api .
docker run -p 5000:5000 ipinfo-api
```

**Tests:**

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=app
```

**Security tools (optional, same as CI):**

```bash
pip install bandit pip-audit ruff
bandit -r app.py -ll
pip-audit -r requirements.txt
ruff check .
```

---

## Repository Settings Worth Noting

A few things I'd configure in the repository settings that go beyond the workflow files:

- **Branch protection on `main`** — require status checks to pass before merging, and require at least one reviewer on PRs. This prevents bypassing the pipeline by pushing directly.
- **GitHub secret scanning** — GitHub's built-in secret scanning can be enabled under Security settings. It runs in addition to Gitleaks and covers a broader set of token patterns for known services.
- **Dependabot** — adds a `dependabot.yml` to get automated PRs when dependencies have new versions or known vulnerabilities, so the dependency-scan job doesn't catch something and leave it to sit.
- **CODEOWNERS** — useful once there's a team; ensures the right people are automatically requested as reviewers for changes to sensitive files like workflow definitions.

---

## What I Would Add Given More Time

- **OIDC-based authentication to GHCR** — instead of using `GITHUB_TOKEN` (which is fine for this), a production setup would use GitHub's OIDC provider to authenticate to a registry or cloud provider without storing long-lived credentials at all.
- **Image signing with Cosign** — sign the container image after pushing so consumers can verify it hasn't been tampered with.
- **SBOM generation** — use `syft` or `trivy` to produce a Software Bill of Materials alongside each build. Increasingly expected in security-conscious environments.
- **Rate limiting** — the API has no rate limiting right now. In production I'd put this behind a reverse proxy (nginx or similar) or use a middleware library to prevent abuse.
- **Input size validation** — the `/ip/` route validates format but not length. A proper production app would cap input length before it ever reaches the validation logic.
- **Structured logging** — replace Flask's default logger with `structlog` or similar so log output is machine-parseable and can be shipped to a SIEM.

---

## Deployed Image

The latest image is published to GitHub Container Registry on each push to `main`:

```
ghcr.io/<your-github-username>/ipinfo-api:latest
```

Pull and run it with:

```bash
docker pull ghcr.io/<your-github-username>/ipinfo-api:latest
docker run -p 5000:5000 ghcr.io/<your-github-username>/ipinfo-api:latest
```