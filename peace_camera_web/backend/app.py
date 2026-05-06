import os
import base64
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import io
from dotenv import load_dotenv

# .env ファイルの読み込み
load_dotenv()

# Docker環境向け設定: frontendフォルダは /frontend にマウントされる
app = Flask(__name__, static_folder='/frontend/static', template_folder='/frontend/templates')
CORS(app)

# --- 設定 (.envから取得) ---
CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE', 'credentials.json')
TOKEN_FILE = os.getenv('TOKEN_FILE', 'token.json')
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', '1vK8N0Ea8SQqMEylsKhFOZsB75b0e1q13')
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'temp_photos')
SCOPES = ['https://www.googleapis.com/auth/drive.file']

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("token.json not found or invalid. Please generate it locally first.")
    return creds

@app.route('/')
def index():
    # index.html は /frontend 直下にある
    return send_from_directory('/frontend', 'index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    try:
        data = request.json
        image_data = data.get('image')
        if not image_data:
            return jsonify({'error': 'No image data'}), 400

        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        
        allow_display = data.get('allow_display', False)
        prefix = "[DISPLAY-OK] " if allow_display else ""
        filename = datetime.now().strftime(f"{prefix}guest_web_%Y%m%d_%H%M%S.png")
        
        creds = get_credentials()
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': filename,
            'parents': [DRIVE_FOLDER_ID]
        }
        
        fh = io.BytesIO(binary_data)
        media = MediaIoBaseUpload(fh, mimetype='image/png')
        
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')

        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        file_info = service.files().get(fileId=file_id, fields='webViewLink').execute()
        share_url = file_info.get('webViewLink')

        return jsonify({'url': share_url})

    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
