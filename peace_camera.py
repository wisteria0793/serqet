import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import numpy as np
import psutil
import os
from datetime import datetime
import qrcode
from PIL import Image
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- 設定 ---
MAX_POSES = 2
MAX_HANDS = 4
PHOTO_DIR = "photos"
PEACE_CONFINGER_TIME = 1.0
DISPLAY_MESSAGE_DURATION = 15.0  # QRコード読み取りのために長くする
QR_CODE_SIZE = 300               # ゲストが読み取りやすいように大きく

# Google Drive 設定
CLIENT_SECRET_FILE = 'credentials.json'
TOKEN_FILE = 'token.json'
DRIVE_FOLDER_ID = "1vK8N0Ea8SQqMEylsKhFOZsB75b0e1q13"
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# 保存用フォルダの作成
if not os.path.exists(PHOTO_DIR):
    os.makedirs(PHOTO_DIR)

# --- アプリの状態定義 ---
STATE_WAITING = "WAITING"
STATE_COUNTDOWN = "COUNTDOWN"
STATE_FLASH = "FLASH"
STATE_UPLOADING = "UPLOADING"    # アップロード中の状態を追加
STATE_PHOTO_TAKEN = "PHOTO_TAKEN"

app_state = STATE_WAITING
countdown_start_time = 0
countdown_duration = 3
photo_taken_time = 0
peace_hold_start_time = 0
last_photo_frame = None
qr_code_image = None
share_url = ""

# --- Google Drive 連携関数 ---
def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def upload_to_drive(file_path):
    try:
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [DRIVE_FOLDER_ID]
        }
        media = MediaFileUpload(file_path, mimetype='image/png')
        
        # ファイルのアップロード
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')

        # 共有設定: リンクを知っている全員が閲覧可能にする
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        # 共有リンクの取得 (Web表示用のリンク)
        file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
        return file_info.get('webViewLink')
    except Exception as e:
        print(f"Upload error: {e}")
        return None

# --- UI/ロジック初期化 ---
base_options_hand = python.BaseOptions(model_asset_path='hand_landmarker.task')
options_hand = vision.HandLandmarkerOptions(
    base_options=base_options_hand,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=MAX_HANDS
)
hand_detector = vision.HandLandmarker.create_from_options(options_hand)

def generate_qr_code(url, size):
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    return cv2.resize(img_cv, (size, size))

def initialize_camera():
    for index in range(2):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            return cap
    return None

cap = initialize_camera()
if cap is None: exit()

cv2.namedWindow('Peace Camera Guest Mode', cv2.WINDOW_NORMAL)
start_time = time.time()

def check_gestures(hand_landmarks):
    # 簡易ピース判定
    index_open = hand_landmarks[8].y < hand_landmarks[6].y
    middle_open = hand_landmarks[12].y < hand_landmarks[10].y
    ring_closed = hand_landmarks[16].y > hand_landmarks[14].y
    pinky_closed = hand_landmarks[20].y > hand_landmarks[18].y
    if index_open and middle_open and ring_closed and pinky_closed:
        return "Peace!"
    return None

while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    frame = cv2.flip(frame, 1)
    h, w, _ = frame.shape
    clean_frame = np.copy(frame)
    
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int((time.time() - start_time) * 1000)

    hand_result = hand_detector.detect_for_video(mp_image, timestamp_ms)

    peace_detected = False
    target_hand_pos = None
    if hand_result.hand_landmarks:
        for landmarks in hand_result.hand_landmarks:
            if check_gestures(landmarks) == "Peace!":
                peace_detected = True
                target_hand_pos = (int(landmarks[0].x * w), int(landmarks[0].y * h))
                break

    current_time = time.time()
    if app_state == STATE_WAITING:
        if peace_detected:
            if peace_hold_start_time == 0: peace_hold_start_time = current_time
            elif current_time - peace_hold_start_time >= PEACE_CONFINGER_TIME:
                app_state = STATE_COUNTDOWN
                countdown_start_time = current_time
                peace_hold_start_time = 0
        else: peace_hold_start_time = 0
    
    elif app_state == STATE_COUNTDOWN:
        elapsed = current_time - countdown_start_time
        if countdown_duration - int(elapsed) <= 0:
            app_state = STATE_FLASH
            photo_taken_time = current_time
    
    elif app_state == STATE_FLASH:
        filename = datetime.now().strftime("guest_photo_%Y%m%d_%H%M%S.png")
        filepath = os.path.join(PHOTO_DIR, filename)
        cv2.imwrite(filepath, clean_frame)
        
        # 保存完了、アップロードへ移行
        last_photo_frame = cv2.resize(clean_frame, (w // 3, h // 3))
        app_state = STATE_UPLOADING
        # アップロード処理 (UIスレッドで動くため一瞬フリーズしますが、完了後に遷移)
        share_url = upload_to_drive(filepath)
        
        if share_url:
            qr_code_image = generate_qr_code(share_url, QR_CODE_SIZE)
            app_state = STATE_PHOTO_TAKEN
            photo_taken_time = time.time()
        else:
            # エラー時は待機に戻る
            app_state = STATE_WAITING

    elif app_state == STATE_PHOTO_TAKEN:
        # 自動遷移を無効化（キー入力で制御するため）
        pass

    # --- UI描画 ---
    if app_state == STATE_WAITING:
        if peace_hold_start_time > 0 and target_hand_pos:
            progress = (current_time - peace_hold_start_time) / PEACE_CONFINGER_TIME
            cv2.ellipse(frame, target_hand_pos, (40, 40), -90, 0, int(progress * 360), (0, 255, 255), 4)
        cv2.putText(frame, "PEACE TO START", (w // 2 - 120, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    elif app_state == STATE_COUNTDOWN:
        remaining = countdown_duration - int(current_time - countdown_start_time)
        cv2.putText(frame, str(remaining), (w // 2 - 40, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 5.0, (255, 255, 255), 10)

    elif app_state == STATE_FLASH:
        frame[:] = 255

    elif app_state == STATE_UPLOADING:
        # アップロード中の表示
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
        cv2.putText(frame, "GENERATING QR CODE...", (w // 2 - 180, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

    elif app_state == STATE_PHOTO_TAKEN:
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        if last_photo_frame is not None:
            ph, pw = last_photo_frame.shape[:2]
            cv2.rectangle(frame, (50-5, h//2-ph//2-5), (50+pw+5, h//2+ph//2+5), (255, 255, 255), 2)
            frame[h//2-ph//2 : h//2+ph//2, 50 : 50+pw] = last_photo_frame

        if qr_code_image is not None:
            qr_x = w - QR_CODE_SIZE - 100
            qr_y = h // 2 - QR_CODE_SIZE // 2
            cv2.rectangle(frame, (qr_x-5, qr_y-5), (qr_x+QR_CODE_SIZE+5, qr_y+QR_CODE_SIZE+5), (255, 255, 255), -1)
            frame[qr_y : qr_y+QR_CODE_SIZE, qr_x : qr_x+QR_CODE_SIZE] = qr_code_image
            cv2.putText(frame, "SCAN TO GET PHOTO!", (qr_x-30, qr_y-20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        cv2.putText(frame, "THANK YOU!", (w // 2 - 100, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        # タイマーバーの代わりに終了指示を表示
        cv2.putText(frame, "PRESS ENTER TO NEXT", (w // 2 - 150, h - 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

    cv2.imshow('Peace Camera Guest Mode', frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'): break
    if key == 13 or key == 10: # Enter key (13 is CR, 10 is LF)
        if app_state == STATE_PHOTO_TAKEN:
            app_state = STATE_WAITING

cap.release()
cv2.destroyAllWindows()
hand_detector.close()
