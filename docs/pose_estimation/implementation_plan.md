# 実装計画：リアルタイム姿勢推定 (Pose Estimation)

## 概要
MediaPipe の Pose Landmarker を利用して、ウェブカメラからの映像に対してリアルタイムで姿勢推定を行い、骨格をオーバーレイ表示するプログラムを実装します。

## 変更内容
1. **新規ファイル `pose_test.py`**:
   - `test.py` で確立した堅牢なカメラ初期化（リトライ機能）を流用。
   - `PoseLandmarker` を `vision.RunningMode.VIDEO` モードで動作させる。
   - 検出された33個のランドマークとその接続線を描画。
2. **モデルファイル**:
   - ディレクトリ内の `pose_landmarker.task` を使用。

## 検証計画
- `pose_test.py` を実行し、人体の骨格が正しく追従することを確認。
- 低遅延で動作することを確認。
