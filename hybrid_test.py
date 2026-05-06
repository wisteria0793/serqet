import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import numpy as np
import psutil
import os

# --- 設定（ここを変更して負荷を検証） ---
MAX_POSES = 2  # 同時に検知する最大人数
MAX_HANDS = 4  # 同時に検知する最大の手の数（1人2本として計算）

# --- 定数定義 ---
POSE_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8),
    (9, 10), (11, 12), (11, 13), (13, 15), (15, 17), (15, 19), (15, 21), (17, 19),
    (12, 14), (14, 16), (16, 18), (16, 20), (16, 22), (18, 20),
    (11, 23), (12, 24), (23, 24), (23, 25), (24, 26), (25, 27), (26, 28),
    (27, 29), (28, 30), (29, 31), (30, 32), (27, 31), (28, 32)
]

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17)
]

# --- 初期化 ---
base_options_pose = python.BaseOptions(model_asset_path='pose_landmarker.task')
options_pose = vision.PoseLandmarkerOptions(
    base_options=base_options_pose,
    running_mode=vision.RunningMode.VIDEO,
    num_poses=MAX_POSES
)
pose_detector = vision.PoseLandmarker.create_from_options(options_pose)

base_options_hand = python.BaseOptions(model_asset_path='hand_landmarker.task')
options_hand = vision.HandLandmarkerOptions(
    base_options=base_options_hand,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=MAX_HANDS
)
hand_detector = vision.HandLandmarker.create_from_options(options_hand)

def initialize_camera():
    for index in range(2):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Camera opened at index {index}")
                return cap
            cap.release()
    return None

cap = initialize_camera()
if cap is None:
    exit()

cv2.namedWindow('Hybrid Performance Monitor', cv2.WINDOW_NORMAL)
start_time = time.time()
process = psutil.Process(os.getpid())

# FPS計測用
fps_avg_frame_count = 10
frame_timestamps = []

# --- 判定ロジック ---
def check_gestures(hand_landmarks):
    # 人差し指(8,6), 中指(12,10), 薬指(16,14), 小指(20,18)
    index_open = hand_landmarks[8].y < hand_landmarks[6].y
    middle_open = hand_landmarks[12].y < hand_landmarks[10].y
    ring_closed = hand_landmarks[16].y > hand_landmarks[14].y
    pinky_closed = hand_landmarks[20].y > hand_landmarks[18].y
    
    if index_open and middle_open and ring_closed and pinky_closed:
        # V字の開き具合を確認
        dist = abs(hand_landmarks[8].x - hand_landmarks[12].x)
        if dist > 0.04:
            return "Peace!"
    return None

def draw_results(image, pose_result, hand_result):
    annotated_image = np.copy(image)
    h, w, _ = annotated_image.shape

    if pose_result.pose_landmarks:
        for landmarks in pose_result.pose_landmarks:
            for connection in POSE_CONNECTIONS:
                p1, p2 = landmarks[connection[0]], landmarks[connection[1]]
                cv2.line(annotated_image, (int(p1.x*w), int(p1.y*h)), (int(p2.x*w), int(p2.y*h)), (255, 150, 0), 2)
    
    if hand_result.hand_landmarks:
        for landmarks in hand_result.hand_landmarks:
            # ピース判定
            gesture = check_gestures(landmarks)
            if gesture:
                wrist = landmarks[0]
                cv2.putText(annotated_image, gesture, (int(wrist.x*w), int(wrist.y*h)-30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 255, 255), 3)

            for connection in HAND_CONNECTIONS:
                p1, p2 = landmarks[connection[0]], landmarks[connection[1]]
                cv2.line(annotated_image, (int(p1.x*w), int(p1.y*h)), (int(p2.x*w), int(p2.y*h)), (0, 255, 0), 2)
    
    return annotated_image

while cap.isOpened():
    loop_start = time.time()
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int((time.time() - start_time) * 1000)

    # 推論実行
    pose_result = pose_detector.detect_for_video(mp_image, timestamp_ms)
    hand_result = hand_detector.detect_for_video(mp_image, timestamp_ms)

    # 描画
    frame = draw_results(frame, pose_result, hand_result)

    # --- パフォーマンス情報の表示 ---
    # FPS計算
    frame_timestamps.append(time.time())
    if len(frame_timestamps) > fps_avg_frame_count:
        frame_timestamps.pop(0)
    fps = len(frame_timestamps) / (frame_timestamps[-1] - frame_timestamps[0]) if len(frame_timestamps) > 1 else 0

    # CPU使用率 (このプロセスの使用率)
    cpu_usage = process.cpu_percent() / psutil.cpu_count()

    # オーバーレイ表示
    cv2.rectangle(frame, (0, 0), (300, 130), (0, 0, 0), -1)
    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"CPU Usage: {cpu_usage:.1f}%", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(frame, f"Max Poses: {MAX_POSES}", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    cv2.putText(frame, f"Max Hands: {MAX_HANDS}", (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    cv2.imshow('Hybrid Performance Monitor', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
pose_detector.close()
hand_detector.close()
