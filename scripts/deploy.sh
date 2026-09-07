#!/usr/bin/env bash
set -euo pipefail

cd /opt/chexiu_bao

git pull origin main
source .venv/bin/activate
pip install -r requirements.txt -q
alembic upgrade head
sudo systemctl restart chexiu-bao

echo "部署完成"
