import {
    HandLandmarker,
    FilesetResolver
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3";

const video = document.getElementById("webcam");
const canvasElement = document.getElementById("output_canvas");
const canvasCtx = canvasElement.getContext("2d");
const statusMessage = document.getElementById("status-message");
const countdownElement = document.getElementById("countdown");
const flashElement = document.getElementById("flash");
const resultOverlay = document.getElementById("result-overlay");
const previewOverlay = document.getElementById("preview-overlay");
const previewImage = document.getElementById("preview-image");
const retakeButton = document.getElementById("retake-button");
const uploadButton = document.getElementById("upload-button");
const capturedImage = document.getElementById("captured-image");
const nextButton = document.getElementById("next-button");
const qrCanvas = document.getElementById("qr-code");
const startScreen = document.getElementById("start-screen");
const startButton = document.getElementById("start-button");
const langButtons = document.querySelectorAll(".lang-btn");
const displayPermission = document.getElementById("display-permission");
const displayMsg = document.getElementById("display-msg");

let appState = "START";
let currentLanguage = "ja";
let handLandmarker = undefined;
let lastVideoTime = -1;

const translations = {
    ja: {
        inst1: "カメラの前に立ってください", inst2: "ピースサインを1秒間キープ！", inst3: "QRコードで写真をゲット", inst4: "好きな場所に持ち運んで撮影OK！",
        waiting: "ピースをしてね！", uploading: "思い出を保存中...", scan: "スキャンして写真を保存！", thankyou: "良い旅を！",
        next: "完了", retake: "撮り直し", save: "写真を保存してQR表示", privacy: "* 写真はGoogle Driveへ保存され、自動的に削除されます。", display: "思い出の壁に飾ってもいいですか？"
    },
    en: {
        inst1: "Stand in front of the camera", inst2: "Hold peace sign for 1 sec!", inst3: "Get photo via QR code", inst4: "Feel free to move it anywhere!",
        waiting: "Show Peace Sign!", uploading: "Saving your memory...", scan: "Scan to get your photo!", thankyou: "Enjoy your trip!",
        next: "Done", retake: "Retake", save: "Save & Show QR", privacy: "* Photos are saved to Google Drive and deleted automatically.", display: "Can we display this on our Memory Wall?"
    },
    ko: {
        inst1: "카메라 앞에 서 주세요", inst2: "브이 사인을 1초간 유지!", inst3: "QR 코드로 사진 받기", inst4: "원하는 장소로 옮겨서 촬영 가능!",
        waiting: "브이 사인을 해주세요!", uploading: "추억을 저장 중...", scan: "스캔하여 사진을 저장하세요!", thankyou: "즐거운 여행 되세요!",
        next: "완료", retake: "다시 찍기", save: "저장 및 QR 표시", privacy: "* 사진은 Google Drive에 저장되며 자동으로 삭제됩니다.", display: "추억의 벽에 장식해도 될까요?"
    },
    zh: {
        inst1: "请站在相机前", inst2: "保持剪刀手姿势1秒！", inst3: "通过QR码获取照片", inst4: "您可以随处移動并拍摄！",
        waiting: "请做出剪刀手姿势！", uploading: "正在保存您的回忆...", scan: "扫描二维码保存照片！", thankyou: "祝您旅途愉快！",
        next: "完成", retake: "重拍", save: "保存并显示QR码", privacy: "* 照片将保存至Google Drive并自動删除。", display: "可以在我们的回忆墙上展示吗？"
    }
};

function setLanguage(lang) {
    currentLanguage = lang;
    const t = translations[lang] || translations.en;
    ["inst-1", "inst-2", "inst-3", "inst-4"].forEach((id, i) => {
        const el = document.getElementById(id);
        if (el) el.innerText = t[`inst${i+1}`];
    });
    if (displayMsg) displayMsg.innerText = t.display;
    if (statusMessage) statusMessage.innerText = (appState === "WAITING") ? t.waiting : (appState === "UPLOADING" ? t.uploading : "");
    if (retakeButton) retakeButton.innerText = t.retake;
    if (uploadButton) uploadButton.innerText = t.save;
    if (nextButton) nextButton.innerText = t.next;
    const thanksText = document.querySelector(".thank-you");
    if (thanksText) thanksText.innerText = t.thankyou;
}

function init() {
    resultOverlay.classList.add("hidden");
    previewOverlay.classList.add("hidden");
    startScreen.classList.remove("hidden");
    statusMessage.classList.add("hidden");
    
    startButton.addEventListener("click", () => {
        video.play().catch(e => console.log(e));
        startScreen.classList.add("hidden");
        statusMessage.classList.remove("hidden");
        appState = "WAITING";
        setLanguage(currentLanguage);
        predictWebcam();
    });

    retakeButton.addEventListener("click", () => {
        previewOverlay.classList.add("hidden");
        statusMessage.classList.remove("hidden");
        appState = "WAITING";
        predictWebcam();
    });

    nextButton.addEventListener("click", () => {
        resultOverlay.classList.add("hidden");
        startScreen.classList.remove("hidden");
        appState = "START";
    });

    uploadButton.addEventListener("click", async () => {
        previewOverlay.classList.add("hidden");
        appState = "UPLOADING";
        statusMessage.classList.remove("hidden");
        setLanguage(currentLanguage);
        try {
            const res = await fetch("/upload", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image: capturedImage.src, allow_display: displayPermission.checked })
            });
            const data = await res.json();
            if (data.url) {
                const qrTarget = window.QRCode || QRCode;
                qrTarget.toCanvas(qrCanvas, data.url, { width: 250 });
                appState = "PHOTO_TAKEN";
                resultOverlay.classList.remove("hidden");
                statusMessage.classList.add("hidden");
            }
        } catch (e) {
            alert(e);
            appState = "WAITING";
        }
    });

    langButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            langButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            setLanguage(btn.dataset.lang);
        });
    });

    setLanguage("ja");
    setupMediaPipe();
    setupCamera();
}

async function setupMediaPipe() {
    const vision = await FilesetResolver.forVisionTasks("https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3/wasm");
    handLandmarker = await HandLandmarker.createFromOptions(vision, {
        baseOptions: { modelAssetPath: `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`, delegate: "GPU" },
        runningMode: "VIDEO", numHands: 2
    });
}

function setupCamera() {
    navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 } }).then(s => video.srcObject = s);
}

function checkPeaceGesture(landmarks) {
    const indexOpen = landmarks[8].y < landmarks[6].y;
    const middleOpen = landmarks[12].y < landmarks[10].y;
    const ringClosed = landmarks[16].y > landmarks[14].y;
    const pinkyClosed = landmarks[20].y > landmarks[18].y;
    return indexOpen && middleOpen && ringClosed && pinkyClosed;
}

let peaceHoldStartTime = 0;
const PEACE_HOLD_TIME = 1000;

async function predictWebcam() {
    if (appState !== "WAITING" && appState !== "COUNTDOWN") return;
    if (video.videoWidth > 0 && lastVideoTime !== video.currentTime) {
        lastVideoTime = video.currentTime;
        const results = handLandmarker ? handLandmarker.detectForVideo(video, performance.now()) : null;
        canvasElement.width = video.videoWidth;
        canvasElement.height = video.videoHeight;
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        
        let peace = false;
        let targetHand = null;
        if (results && results.landmarks) {
            for (const l of results.landmarks) {
                if (checkPeaceGesture(l)) { 
                    peace = true; 
                    targetHand = l[0];
                    break; 
                }
            }
        }

        const now = Date.now();
        if (appState === "WAITING") {
            if (peace) {
                if (peaceHoldStartTime === 0) peaceHoldStartTime = now;
                else if (now - peaceHoldStartTime >= PEACE_HOLD_TIME) {
                    appState = "COUNTDOWN";
                    startCountdown();
                }
                if (targetHand) {
                    const progress = (now - peaceHoldStartTime) / PEACE_HOLD_TIME;
                    canvasCtx.beginPath();
                    canvasCtx.arc(targetHand.x * canvasElement.width, targetHand.y * canvasElement.height, 40, -Math.PI/2, -Math.PI/2 + (Math.PI*2*progress));
                    canvasCtx.strokeStyle = "#ffeb3b";
                    canvasCtx.lineWidth = 5;
                    canvasCtx.stroke();
                }
            } else {
                peaceHoldStartTime = 0;
            }
        }
    }
    requestAnimationFrame(predictWebcam);
}

function startCountdown() {
    let count = 3;
    countdownElement.innerText = count;
    statusMessage.classList.add("hidden");
    const timer = setInterval(() => {
        count--;
        if (count <= 0) {
            clearInterval(timer);
            takePhoto();
        } else {
            countdownElement.innerText = count;
        }
    }, 1000);
}

function takePhoto() {
    flashElement.classList.add("active");
    setTimeout(() => flashElement.classList.remove("active"), 100);
    countdownElement.innerText = "";
    const c = document.createElement("canvas");
    c.width = video.videoWidth; c.height = video.videoHeight;
    const ctx = c.getContext("2d");
    ctx.translate(c.width, 0); ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0);
    previewImage.src = c.toDataURL("image/png");
    capturedImage.src = previewImage.src;
    appState = "PREVIEW";
    previewOverlay.classList.remove("hidden");
}

init();
