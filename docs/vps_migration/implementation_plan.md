# 実装計画: Peace Camera VPS 移植

## 1. 構成概要
- **Webサーバ**: Nginx (リバースプロキシ)
- **アプリケーションサーバ**: Gunicorn (WSGI)
- **フレームワーク**: Flask (Python 3.10)
- **自動起動**: Systemd

## 2. Nginx 設定 (既設)
`/etc/nginx/sites-available/peace_camera` に設定済み。Certbot により SSL 設定が追加されている。

## 3. Gunicorn & Systemd 設定
`/etc/systemd/system/peace_camera.service` を作成し、バックグラウンド実行を管理する。

### Systemd ユニットファイル内容例
```ini
[Unit]
Description=Gunicorn instance to serve Peace Camera
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/www/peace_camera/serqet/peace_camera_vps
Environment="PATH=/var/www/peace_camera/serqet/peace_camera_vps/venv/bin"
ExecStart=/var/www/peace_camera/serqet/peace_camera_vps/venv/bin/gunicorn --workers 3 --bind unix:peace_camera.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
```

## 4. Google Drive 認証
ローカル環境で作成した `token.json` と、環境変数を定義した `.env` を `WorkingDirectory` に配置する必要がある。
