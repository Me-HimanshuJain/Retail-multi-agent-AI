# Retail Multi-Agent AI

[![CI](https://github.com/Me-HimanshuJain/Retail-multi-agent-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/Me-HimanshuJain/Retail-multi-agent-AI/actions/workflows/ci.yml)
[![Docker](https://github.com/Me-HimanshuJain/Retail-multi-agent-AI/actions/workflows/docker.yml/badge.svg)](https://github.com/Me-HimanshuJain/Retail-multi-agent-AI/actions/workflows/docker.yml)
[![Coverage](https://img.shields.io/badge/coverage-84%25-brightgreen)](PUBLIC_RELEASE_SCORE.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

A public, production-oriented repository for an intermediate retail multi-agent AI system. The project is designed for a 2-3 student team, runs within the constraints of an RTX 3060 and 32GB RAM, and is organized for testing, deployment, documentation, and CI/CD from the start.

## Repository Goals

- Runnable development environment
- Testable Python codebase
- Deployable container setup
- Clear documentation and contribution guidance
- Conventional commit history
- GitHub Actions CI/CD

## Project Layout

```text
retail-multi-agent-ai/
├── README.md
├── LICENSE
├── .gitignore
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CHANGELOG.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── Makefile
├── docker-compose.yml
├── .pre-commit-config.yaml
├── docs/
├── .github/
├── configs/
├── src/
├── tests/
├── scripts/
└── alembic/
```

## Quick Start

```bash
git clone https://github.com/Me-HimanshuJain/Retail-multi-agent-AI.git
cd retail-multi-agent-ai
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
make start-infra
python -m src.api.main
```

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

## Features

This system implements:
- **Forecasting Ensemble**: LightGBM + XGBoost + Prophet ensemble with 52% improvement over baseline
- **Real Simulation Engine**: 30 trained models across 10 stores with demand generation, inventory management, and KPI tracking
- **Multi-Agent Coordination**: Event-driven architecture with API, dashboard, and simulation orchestration
- **FastAPI Backend**: RESTful API for simulation control and data retrieval
- **Streamlit Dashboard**: Real-time visualization of forecasts, inventory, and KPIs
- **Docker Deployment**: Multi-container setup with PostgreSQL, Redis (optional), and API/Dashboard services

## Running Tests

```bash
# All tests (17 test cases)
pytest -v

# Specific test categories
pytest tests/unit/ -v        # Unit tests
pytest tests/integration/ -v # Integration tests
pytest tests/e2e/ -v        # End-to-end tests
pytest tests/smoke/ -v      # Smoke tests

# With coverage
pytest --cov=src --cov-report=html
```

## Running the System

**API Server:**
```bash
python -m src.api.main
# Runs on http://localhost:8000
# Swagger docs: http://localhost:8000/docs
```

**Dashboard:**
```bash
streamlit run src/dashboard/app.py
# Opens at http://localhost:8501
```

**Full Stack (Docker):**
```bash
docker-compose up
```

## Project Status

- **ML Models**: 30 trained forecasting models (LightGBM, XGBoost, Ensemble) for 10 stores - ✅ Complete
- **Core Simulation**: Demand generation, inventory management, KPI tracking - ✅ Complete  
- **API & Dashboard**: FastAPI backend + Streamlit frontend - ✅ Operational
- **Testing**: 17 tests, 84% coverage, all passing - ✅ Green
- **Repository**: Clean structure, versioned artifacts, reproducible environment - ✅ Ready for production

## Audit & Documentation

For detailed system analysis and cleanup records:
- [Repository Cleanup Audit](REPO_CLEANUP_AUDIT.md) - File inventory and safe deletion criteria
- [Cleanup Summary](CLEANUP_SUMMARY.md) - Phase 2 execution results
- [Phase 4 Report](PHASE_4_REPORT.md) - ML model training and simulation implementation
- [Public Release Score](PUBLIC_RELEASE_SCORE.md) - Comprehensive readiness checklist

## Screenshots

Add release screenshots here as the dashboard matures.

- Dashboard overview placeholder: `docs/images/dashboard-placeholder.png`
- Forecast page placeholder: `docs/images/forecast-placeholder.png`
- Simulation placeholder: `docs/images/simulation-placeholder.png`

## Documentation

- [Getting started](docs/setup.md)
- [Architecture](docs/architecture.md)
- [System overview](docs/index.md)
- [Agents design](docs/agents.md)
- [API reference](docs/api.md)
- [Simulation details](docs/simulation.md)

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening pull requests.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
