"""
QUICK START: GitHub Actions & Docker Setup
============================================

Follow these steps to set up CI/CD pipeline for your incident triage system.
"""

STEP 1: GITHUB SECRETS
======================

1. Go to: https://github.com/YOUR_ORG/my-monorepo/settings/secrets/actions

2. Create "ANTHROPIC_API_KEY" secret:
   - Click "New repository secret"
   - Name: ANTHROPIC_API_KEY
   - Value: sk-ant-your-key-from-console.anthropic.com
   - Click "Add secret"

3. Verify github.com token has:
   - Settings → Actions → General → Workflow permissions
   - Set to "Read and write permissions"
   - "Allow GitHub Actions to create and approve pull requests" (optional)


STEP 2: LOCAL TESTING
=====================

Before pushing changes, run quality gates locally:

WINDOWS:
  cd apps/api
  .\..\..\.venv\Scripts\Activate.ps1
  .\check_quality_gates.ps1

LINUX/macOS:
  cd apps/api
  source ../../../.venv/bin/activate
  bash check_quality_gates.sh

This ensures:
  ✓ Coverage >= 85%
  ✓ All unit tests pass
  ✓ RAG evaluation >= 70% accuracy


STEP 3: GIT WORKFLOW
====================

1. Create feature branch:
   git checkout -b feature/my-feature

2. Make changes and test locally:
   pytest test/test_clustering_unit.py -v
   ./check_quality_gates.ps1

3. Commit with clear message:
   git commit -m "feat: add new clustering endpoint"

4. Push to remote:
   git push origin feature/my-feature

5. Create Pull Request on GitHub
   - GitHub Actions will automatically:
     * Run all tests
     * Check coverage
     * Evaluate RAG accuracy
     * Build Docker image
   
   - PR will show status: ✓ Pass or ✗ Fail

6. If checks fail:
   - Fix issues locally
   - Run quality gates: ./check_quality_gates.ps1
   - Commit and push again

7. If checks pass:
   - Request review
   - Merge to main (merging to main triggers deployment)


STEP 4: DEPLOYMENT
==================

Image gets built and pushed when:
  - You push to develop branch → ghcr.io/.../incident-triage-api:develop
  - You push to main branch → ghcr.io/.../incident-triage-api:latest

Pull the image:
  docker login ghcr.io
  # Username: your-github-username
  # Password: (GitHub personal access token)
  
  docker pull ghcr.io/your-org/my-monorepo/incident-triage-api:latest


STEP 5: MONITORING
==================

View CI/CD status:
  1. Actions tab → "Test, Build & Push" workflow
  2. See latest run status (green ✓ or red ✗)
  3. Click to view detailed log

Key things to monitor:
  - Coverage trends on Codecov.io
  - Test failure reasons (click workflow)
  - Docker build logs (click build job)


TROUBLESHOOTING
===============

Problem: "ANTHROPIC_API_KEY not set"
Solution: Add secret to GitHub Settings → Secrets

Problem: Coverage fails "must be 85%"
Solution: pytest test/test_clustering_unit.py --cov=src
         Add more tests to increase coverage

Problem: "RAG accuracy below 70%"
Solution: Check RAG evaluation locally
         python test/test_rag_evaluation.py
         Improve runbooks or prompt templates

Problem: "Docker image push failed"
Solution: Check github.com token has "read and write" permissions

Problem: "Tests pass locally but fail in CI"
Solution: Check CI logs, ensure dependencies installed correctly


FILES CREATED
=============

✓ .github/workflows/test-build-push.yml
  - Main CI/CD pipeline configuration
  - Triggers on push/PR to main/develop
  - Runs tests, builds image, pushes to registry

✓ apps/api/Dockerfile
  - Multi-stage Docker build
  - Python 3.12 slim base image
  - Health checks enabled

✓ apps/api/.dockerignore
  - Excludes unnecessary files from Docker build
  - Reduces image size

✓ apps/api/check_quality_gates.ps1
  - PowerShell script for Windows developers
  - Run before pushing: .\check_quality_gates.ps1
  - Validates coverage and accuracy

✓ apps/api/check_quality_gates.sh
  - Bash script for Linux/macOS developers
  - Run before pushing: bash check_quality_gates.sh
  - Validates coverage and accuracy

✓ apps/api/CI_CD_README.md
  - Complete CI/CD pipeline documentation
  - Troubleshooting guide
  - Deployment instructions


QUALITY GATES EXPLAINED
=======================

Gate 1: Coverage >= 85%
  - Measures how much code is tested
  - Command: pytest --cov=src --cov-fail-under=85
  - Why: Ensures code quality and maintainability

Gate 2: RAG Accuracy >= 70%
  - Measures RAG reasoning performance
  - Evaluates against 20 golden incidents
  - Why: Ensures AI suggestions are reliable

Both gates must pass for:
  ✓ Tests to succeed
  ✓ Docker image to build
  ✓ Image to be pushed to registry


WHAT DEVELOPERS NEED TO KNOW
=============================

1. Run quality gates before pushing:
   .\check_quality_gates.ps1

2. GitHub Actions will auto-test on push:
   - View results in Actions tab
   - PR shows pass/fail status

3. Docker images automatically built and pushed:
   - ghcr.io/your-org/my-monorepo/incident-triage-api:latest (main)
   - ghcr.io/your-org/my-monorepo/incident-triage-api:develop (develop)

4. Keep main branch stable:
   - Only merge if all checks pass
   - Review status badges on repo

5. Monitor coverage and accuracy:
   - Codecov.io for coverage trends
   - GitHub Actions for test results


NEXT STEPS
==========

1. ✓ Done: GitHub Actions workflow created
2. ✓ Done: Quality gates configured
3. ✓ Done: Docker setup completed

4. Now: Add ANTHROPIC_API_KEY to GitHub Secrets
5. Now: Push code to test the workflow
6. Now: Monitor Actions tab for results
7. Now: Iterate and improve accuracy


STATUS BADGE
============

Add to README.md:

[![Test Status](https://github.com/YOUR_ORG/my-monorepo/actions/workflows/test-build-push.yml/badge.svg)](https://github.com/YOUR_ORG/my-monorepo/actions)

[![codecov](https://codecov.io/gh/YOUR_ORG/my-monorepo/branch/main/graph/badge.svg)](https://codecov.io/gh/YOUR_ORG/my-monorepo)

[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue)](https://github.com/YOUR_ORG/my-monorepo/packages)
"""

# Developer quick start guide
