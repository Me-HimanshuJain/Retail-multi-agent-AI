# Setup

## Requirements

- Python 3.10+
- Docker Desktop
- 16 GB RAM minimum, 32 GB recommended

## Local Development

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
make start-infra
```
