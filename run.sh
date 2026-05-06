#!/bin/bash

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# 仮想環境が有効でない場合はアクティベート
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "Error: venv directory not found. Please create it first."
        exit 1
    fi
fi

# アプリを実行
python peace_camera.py
