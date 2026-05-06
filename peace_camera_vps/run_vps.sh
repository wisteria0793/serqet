#!/bin/bash

# Peace Camera VPS 起動スクリプト
# Dockerを使わずにメモリ最小限で動作させます

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 仮想環境のセットアップ
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# ライブラリのインストール
echo "Installing dependencies..."
pip install -r requirements.txt

# .env からポート番号を取得 (デフォルト5000)
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
PORT=${PORT:-5000}

# 既存のプロセスがあれば停止
PID=$(lsof -t -i:$PORT)
if [ ! -z "$PID" ]; then
    echo "Stopping existing process on port $PORT (PID: $PID)..."
    kill $PID
    sleep 2
fi

# サーバー起動
echo "Starting Peace Camera on http://0.0.0.0:$PORT"
gunicorn --workers 2 --bind 0.0.0.0:$PORT app:app
