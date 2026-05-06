import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import numpy as np

# Pose Landmarkerの接続関係（描画用）
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32)
]

# Pose Landmarkerのセットアップ
base_options = python.BaseOptions(model_asset_path='pose_landmarker.task')
options = vision.PoseLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_poses=1
)
detector = vision.PoseLandmarker.create_from_options(options)

# カメラ初期化（リトライ機能付き）
def initialize_camera():
    print("Initializing camera...")
    for index in range(2):  # 0と1を試す
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Successfully opened camera at index {index}")
                return cap
            cap.release()
    return None

cap = initialize_camera()

if cap is None:
    print("Error: Could not open any camera.")
    exit()

cv2.namedWindow('Pose Estimation', cv2.WINDOW_NORMAL)
start_time = time.time()

def draw_pose_landmarks(image, detection_result):
    if not detection_result.pose_landmarks:
        return image
    
    annotated_image = np.copy(image)
    height, width, _ = annotated_image.shape

    for pose_landmarks in detection_result.pose_landmarks:
        # 接続線を描画
        for connection in POSE_CONNECTIONS:
            start_idx = connection[0]
            end_idx = connection[1]
            
            start_point = pose_landmarks[start_idx]
            end_point = pose_landmarks[end_idx]
            
            # 座標に変換（視認性のために一定以上の信頼度がある場合のみ描画することも可能だが、ここでは全て描画）
            start_x = int(start_point.x * width)
            start_y = int(start_point.y * height)
            end_x = int(end_point.x * width)
            end_y = int(end_point.y * height)
            
            cv2.line(annotated_image, (start_x, start_y), (end_x, end_y), (255, 255, 0), 2)

        # 関節（ランドマーク）を描画
        for landmark in pose_landmarks:
            x = int(landmark.x * width)
            y = int(landmark.y * height)
            cv2.circle(annotated_image, (x, y), 5, (0, 0, 255), -1)
            
    return annotated_image

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    timestamp_ms = int((time.time() - start_time) * 1000)
    detection_result = detector.detect_for_video(mp_image, timestamp_ms)

    frame = draw_pose_landmarks(frame, detection_result)

    cv2.imshow('Pose Estimation', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
