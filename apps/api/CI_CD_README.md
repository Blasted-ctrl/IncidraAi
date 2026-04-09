"""
CI/CD PIPELINE DOCUMENTATION
=============================

GitHub Actions workflow for automated testing, building, and deploying
the Incident Triage API.


PIPELINE OVERVIEW
=================

┌─────────────────────────────────────────────────────────────┐
│                    Git Push to main/develop                 │
└────────────────────────┬────────────────────────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │      TEST JOB (Ubuntu)       │
          ├──────────────────────────────┤
          │ 1. Install dependencies     │
          │ 2. Run unit tests            │
          │ 3. Check coverage >= 85%     │
          │ 4. Run RAG evaluation        │
          │ 5. Check accuracy >= 70%     │
          │ 6. Upload to Codecov         │
          └──────────────┬───────────────┘
                         │
          ┌──────────────▼──────────────┐
          │    BUILD JOB (Ubuntu)        │
          ├──────────────────────────────┤
          │ 1. Set up Docker Buildx      │
          │ 2. Login to registry         │
          │ 3. Build image               │
          │ 4. Push if main branch       │
          │ 5. Tag with version/sha      │
          └──────────────┬───────────────┘
                         │
          ┌──────────────▼──────────────┐
          │   QUALITY GATES JOB          │
          ├──────────────────────────────┤
          │ 1. Check test status         │
          │ 2. Check build status        │
          │ 3. Fail if either failed     │
          └──────────────┬───────────────┘
                         │
                    ✓ SUCCESS
                    (or ✗ FAILURE)


SETUP
=====

1. GITHUB SECRETS REQUIRED

   These secrets must be configured in: Settings → Secrets and variables → Actions

   a) ANTHROPIC_API_KEY (Required for RAG evaluation)
      - Get from: https://console.anthropic.com/
      - Action: Settings → Add "ANTHROPIC_API_KEY"
      
   b) GITHUB_TOKEN (Automatic, no setup needed)
      - Used to push to GitHub Container Registry (ghcr.io)
      - Automatically created for every repo

   Optional: Docker Hub credentials (for push to Docker Hub)
      - Add DOCKER_USERNAME and DOCKER_PASSWORD if desired

2. GITHUB CONTAINER REGISTRY PERMISSIONS

   GitHub Actions automatically has permissions to push to ghcr.io.
   Images will be pushed to: ghcr.io/YOUR_ORG/my-monorepo/incident-triage-api


QUALITY GATES
=============

The pipeline enforces two quality thresholds:

1. CODE COVERAGE >= 85%
   - Measured by pytest-cov on unit tests
   - Run locally: pytest test/test_clustering_unit.py --cov=src
   - Fails build if: coverage < 85%

2. RAG EVALUATION ACCURACY >= 70%
   - Measured by RAGEvaluator against 20 golden incidents
   - Metrics: root cause, severity, services accuracy
   - Fails build if: overall_accuracy < 70%

Both gates must pass for:
  - Tests to succeed ✓
  - Docker image to be built ✓
  - Image to be pushed ✓


RUNNING LOCALLY
===============

Before pushing, developers should run quality gates locally:

WINDOWS (PowerShell):
  cd apps/api
  .\check_quality_gates.ps1

LINUX/MAC (Bash):
  cd apps/api
  bash check_quality_gates.sh

This validates:
  ✓ Coverage threshold
  ✓ Unit tests pass
  ✓ RAG evaluation passes

Only push if all local checks pass!


WORKFLOW TRIGGERS
=================

Workflow runs on:
  - Push to main branch
  - Push to develop branch
  - Pull requests to main or develop
  - Manual trigger via Actions tab (optional)

Branches: [main, develop]
Events: [push, pull_request]


DOCKER IMAGE TAGGING
====================

Images are tagged with:
  - Branch: ghcr.io/.../incident-triage-api:develop
  - Short SHA: ghcr.io/.../incident-triage-api:sha-abc123
  - Latest: ghcr.io/.../incident-triage-api:latest (main only)
  - Semver: ghcr.io/.../incident-triage-api:v1.0.0

Example:
  ghcr.io/your-org/my-monorepo/incident-triage-api:develop
  ghcr.io/your-org/my-monorepo/incident-triage-api:sha-1a2b3c4d
  ghcr.io/your-org/my-monorepo/incident-triage-api:latest


PULLING IMAGES
==============

Pull built images with:

Authentication (first time):
  docker login ghcr.io
  Username: YOUR_GITHUB_USERNAME
  Password: GITHUB_TOKEN (get from Settings → Personal access tokens)

Pull image:
  docker pull ghcr.io/your-org/my-monorepo/incident-triage-api:latest

Run container:
  docker run -p 8000:8000 \
    ghcr.io/your-org/my-monorepo/incident-triage-api:latest


ARTIFACT UPLOADS
================

Coverage reports automatically uploaded to Codecov:
  - https://codecov.io/github/YOUR_ORG/my-monorepo
  - Integrate with PR checks for coverage tracking
  - Set up badge in README


TROUBLESHOOTING
===============

1. "ANTHROPIC_API_KEY not set"
   Fix: Add to GitHub Secrets
        Settings → Secrets and variables → Actions
        New secret: ANTHROPIC_API_KEY = sk-ant-...

2. "Docker login failed"
   Fix: GITHUB_TOKEN is automatic, check:
        Settings → Actions → General → Workflow permissions
        Should have "Read and write permissions"

3. "Coverage < 85% detected"
   Fix: Run locally and improve test coverage
        pytest test/test_clustering_unit.py --cov=src
        Add tests for uncovered code paths

4. "RAG accuracy < 70%"
   Fix: Run evaluation locally
        python test/test_rag_evaluation.py
        Improve prompt templates or add more runbooks
        Check ANTHROPIC_API_KEY is valid

5. "Tests pass locally but fail in CI"
   Possible causes:
   - Missing dependencies
   - Environment differences
   - Database connection issues
   
   Check: CI logs in Actions tab → click failed workflow → see output


MONITORING
==========

View workflow runs:
  1. Go to Actions tab in GitHub repo
  2. Select "Test, Build & Push" workflow
  3. View runs with status (green ✓ or red ✗)

Each run shows:
  - Test results (unit tests, coverage, RAG eval)
  - Build log (Docker build output)
  - Push status (image tag pushed)
  - Execution time
  - Triggered by (push, PR, etc.)

Failed runs show full error traces for debugging.


DEPLOYMENT
==========

Once images are pushed to ghcr.io, deploy with:

Kubernetes:
  kubectl set image deployment/api-deployment \
    api=ghcr.io/your-org/my-monorepo/incident-triage-api:latest

Docker Compose:
  image: ghcr.io/your-org/my-monorepo/incident-triage-api:latest

Docker run:
  docker run -p 8000:8000 \
    ghcr.io/your-org/my-monorepo/incident-triage-api:latest


CUSTOMIZATION
=============

Edit `.github/workflows/test-build-push.yml` to:

1. Change Python version:
   python-version: '3.12'  →  '3.11' or '3.13'

2. Change coverage threshold:
   --cov-fail-under=85  →  --cov-fail-under=80

3. Change accuracy threshold:
   if overall_acc < 0.70  →  if overall_acc < 0.75

4. Add more test commands:
   pytest test/test_integration.py -v

5. Push to Docker Hub instead:
   Add DOCKER_USERNAME, DOCKER_PASSWORD secrets
   Update registry: docker.io/username/incident-triage-api

6. Add Slack notifications:
   Use actions/slack@v1 after build success/failure


BEST PRACTICES
==============

1. Always run quality gates locally before pushing
   ./check_quality_gates.ps1 (Windows)
   bash check_quality_gates.sh (Linux/Mac)

2. Keep main branch stable
   - Only merge if all CI checks pass
   - Protect main branch in GitHub settings

3. Monitor coverage trends
   - Check Codecov.io after each push
   - Address coverage regressions promptly

4. Keep RAG accuracy high
   - Add runbooks for new incident types
   - Improve prompt templates
   - Evaluate against golden dataset regularly

5. Tag releases
   - Use semantic versioning (v1.0.0, v1.1.0)
   - GitHub tags automatically trigger builds
   - Creates release-specific Docker image


SECURITY
========

Secrets management:
  ✓ ANTHROPIC_API_KEY: Only accessible to GitHub Actions
  ✓ GITHUB_TOKEN: Automatically rotated
  ✓ Never commit secrets to version control

Container security:
  - Base image: python:3.12-slim (minimal attack surface)
  - Multi-stage build: reduces final image size
  - Non-root user: runs as unprivileged user
  - Health checks: ensures container is responsive


METRICS & ALERTS
================

Monitor with:
  - GitHub Actions dashboard (success/failure)
  - Codecov.io (coverage trends)
  - Docker Hub / ghcr.io (image push history)
  - PR status checks (coverage + build)

Set up alerts via:
  - GitHub email notifications
  - Slack integration (optional)
  - Webhook notifications


FAQ
===

Q: How do I skip the workflow for a commit?
A: Add [skip ci] or [ci skip] to commit message

Q: Can I run the workflow manually?
A: Yes, from Actions tab → "Run workflow" button

Q: How long do workflows take?
A: ~5-10 minutes (depends on test suite size)

Q: Where are images stored?
A: GitHub Container Registry (ghcr.io)

Q: Can I use private images?
A: Yes, images inherit repo privacy settings

Q: How do I cache dependencies?
A: Caching is automatic in setup-python@v4
"""

# This is documentation for the CI/CD pipeline
