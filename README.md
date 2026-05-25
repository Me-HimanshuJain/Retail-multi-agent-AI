# Retail Multi-Agent AI

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
git clone https://github.com/your-org/retail-multi-agent-ai.git
cd retail-multi-agent-ai
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
make start-infra
```

## Documentation

- [Getting started](docs/setup.md)
- [Architecture](docs/architecture.md)
- [System overview](docs/index.md)

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening pull requests.

## License

Licensed under the MIT License. See [LICENSE](LICENSE).
