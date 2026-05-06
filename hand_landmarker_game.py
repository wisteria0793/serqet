import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import random
import math
import time
import numpy as np

# Hand Landmarkerのセットアップ
base_options = python.BaseOptions(model_asset_path='hand_landmarker.task')
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=2
)
detector = vision.HandLandmarker.create_from_options(options)

# スコアの初期化
score = 0

# ランダムに赤い丸を表示するための初期位置
circle_x = random.randint(100, 500)
circle_y = random.randint(100, 400)
circle_radius = 20

# カメラからの映像をキャプチャ
def initialize_camera():
    for index in range(2):  # 0と1を試す
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            # テスト読み込み
            ret, frame = cap.read()
            if ret:
                print(f"Successfully opened camera at index {index}")
                return cap
            cap.release()
    return None

cap = initialize_camera()

if cap is None:
    print("Error: Could not open any camera. Please check your connection or permissions.")
    exit()

# OpenCVのウィンドウを作成
cv2.namedWindow('Hand Game', cv2.WINDOW_NORMAL)
is_fullscreen = False

# ゲームの制限時間（秒）
game_duration = 30
start_time = time.time()

def is_hand_touching_circle(hand_x, hand_y, circle_x, circle_y, circle_radius):
    distance = math.sqrt((hand_x - circle_x) ** 2 + (hand_y - circle_y) ** 2)
    return distance < circle_radius

def generate_new_circle_position(frame_width, frame_height, circle_radius, exclude_area):
    while True:
        new_x = random.randint(circle_radius, frame_width - circle_radius)
        new_y = random.randint(circle_radius, frame_height - circle_radius)
        if not (exclude_area[0] <= new_x <= exclude_area[2] and exclude_area[1] <= new_y <= exclude_area[3]):
            return new_x, new_y

def draw_landmarks_on_image(rgb_image, detection_result):
    hand_landmarks_list = detection_result.hand_landmarks
    annotated_image = np.copy(rgb_image)

    # ランドマークを描画
    for hand_landmarks in hand_landmarks_list:
        for landmark in hand_landmarks:
            x = int(landmark.x * annotated_image.shape[1])
            y = int(landmark.y * annotated_image.shape[0])
            cv2.circle(annotated_image, (x, y), 5, (0, 255, 0), -1)
    
    return annotated_image

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("Failed to grab frame.")
        break

    # 画像を水平方向に反転
    frame = cv2.flip(frame, 1)

    # 画像をRGBに変換（Mediapipe Task用）
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # 現在のタイムスタンプを取得（ミリ秒）
    timestamp_ms = int((time.time() - start_time) * 1000)

    # 手のランドマークの検出 (VIDEOモード用)
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    # 検出結果の描画
    frame = draw_landmarks_on_image(frame, detection_result)

    # スコアとタイマー表示領域の背景を描画
    cv2.rectangle(frame, (0, 0), (200, 100), (0, 0, 0), -1)

    # 検出結果がある場合、右手の位置を取得
    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            # ランドマークの座標を取得（8番目のランドマーク=人差し指の先端）
            # mediapipe.tasks では 8番が INDEX_FINGER_TIP
            index_finger_tip = hand_landmarks[8]
            hand_x = int(index_finger_tip.x * frame.shape[1])
            hand_y = int(index_finger_tip.y * frame.shape[0])

            if is_hand_touching_circle(hand_x, hand_y, circle_x, circle_y, circle_radius):
                score += 1
                # 新しい位置に赤い丸を再配置
                circle_x, circle_y = generate_new_circle_position(frame.shape[1], frame.shape[0], circle_radius, (0, 0, 200, 100))

    # 赤い丸を描画
    cv2.circle(frame, (circle_x, circle_y), circle_radius, (0, 0, 255), -1)

    # スコアを表示
    cv2.putText(frame, f'Score: {score}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # 残り時間を計算
    elapsed_time = time.time() - start_time
    remaining_time = max(0, game_duration - int(elapsed_time))
    cv2.putText(frame, f'Time: {remaining_time}', (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

    # ゲーム終了条件
    if remaining_time <= 0:
        break

    # 画像を表示
    cv2.imshow('Hand Game', frame)

    # キー入力をチェック
    key = cv2.waitKey(10) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('f'):
        is_fullscreen = not is_fullscreen
        if is_fullscreen:
            cv2.setWindowProperty('Hand Game', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        else:
            cv2.setWindowProperty('Hand Game', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)

# リソースの解放
cap.release()
cv2.destroyAllWindows()

# ゲーム終了メッセージ
print(f'Game Over! Your score is {score}')

