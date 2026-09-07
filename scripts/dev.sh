#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt -q

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "已创建 .env，请按需修改 DATABASE_URL"
fi

alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
