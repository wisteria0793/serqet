# 動作確認手順 (Walkthrough)

## 1. サービスの起動確認
- [ ] `systemctl status peace_camera` が `active (running)` であること。
- [ ] `/var/www/peace_camera/serqet/peace_camera_vps/peace_camera.sock` が作成されていること。

## 2. Webアクセス確認
- [ ] `https://peace-camera.hakodate-tomoe.com` にアクセスし、UIが表示されること。
- [ ] ブラウザの鍵アイコンが表示され、SSLが有効であること。

## 3. アプリケーション機能確認
- [ ] ブラウザでカメラの使用を許可し、映像が表示されること。
- [ ] 写真を撮影し、「送信」または「保存」ボタンを押した際にエラーが出ないこと。
- [ ] Google Drive の指定フォルダに画像が保存されていること。
