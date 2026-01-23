if (!navigator.mediaDevices) {
    navigator.mediaDevices = {};
}

if (!navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia = function(constraints) {
        const getUserMedia = navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia;
        if (!getUserMedia) {
            return Promise.reject(new Error('getUserMedia is not supported in this browser'));
        }
        return new Promise((resolve, reject) => {
            getUserMedia.call(navigator, constraints, resolve, reject);
        });
    };
}

function getMobileConstraints(deviceId) {
    const constraints = {
        video: {
            deviceId: deviceId ? { exact: deviceId } : undefined,
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: { ideal: "environment" }
        }
    };
    if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
        constraints.video.width = { max: 1280 };
        constraints.video.height = { max: 720 };
    }
    return constraints;
}

const cameraFeedElement = document.getElementById('camera-feed');
let ws;
let currentStream = null;
let currentDeviceIndex = 0;
let allCameras = [];
let politenessLevel = 5;
let pictureCount = 0;
let audioQueue = [];
let isPlaying = false;
let selectedVoiceName = null;
let selectedVoiceLabel = null;
let selectedVoiceId;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 2000;
let serverStatus = 'offline';
let serverReady = false;
let pendingCapture = false;

function stopCurrentVideoStream() {
    if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
    }
}

function getCameras() {
    navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            allCameras = devices.filter(device => device.kind === 'videoinput');
            if (allCameras.length > 0) {
                switchCamera();
            }
        })
        .catch(error => console.error("Could not get cameras:", error));
}

function switchCamera() {
    stopCurrentVideoStream();
    if (allCameras.length === 0) {
        return;
    }
    currentDeviceIndex = (currentDeviceIndex + 1) % allCameras.length;
    const deviceId = allCameras[currentDeviceIndex].deviceId;
    const constraints = getMobileConstraints(deviceId);

    navigator.mediaDevices.getUserMedia(constraints)
        .then(stream => {
            currentStream = stream;
            try {
                cameraFeedElement.srcObject = stream;
            } catch (error) {
                const videoURL = window.URL || window.webkitURL;
                cameraFeedElement.src = videoURL.createObjectURL(stream);
            }
        })
        .catch(error => console.error("Could not switch camera:", error));
}

getCameras();

document.getElementById('toggle-camera-btn').addEventListener('click', switchCamera);

function playAudio(arrayBuffer) {
    const blob = new Blob([arrayBuffer], { type: 'audio/mp3' });
    audioQueue.push(blob);
    if (!isPlaying) {
        playNextAudio();
    }
}

function playNextAudio() {
    if (audioQueue.length > 0) {
        isPlaying = true;
        const url = URL.createObjectURL(audioQueue.shift());
        const audio = new Audio();
        audio.setAttribute('playsinline', '');
        audio.setAttribute('webkit-playsinline', '');
        audio.src = url;
        audio.onerror = () => {
            hideLoadingPopup();
            isPlaying = false;
            playNextAudio();
        };
        audio.onplaying = () => {
            hideLoadingPopup();
        };
        audio.onended = () => {
            URL.revokeObjectURL(url);
            playNextAudio();
        };
        const playPromise = audio.play();
        if (playPromise !== undefined) {
            playPromise.catch(() => {
                isPlaying = false;
                playNextAudio();
            });
        }
    } else {
        isPlaying = false;
    }
}

function selectVoice() {
    selectedVoiceName = this.getAttribute('data-voice-name');
    selectedVoiceLabel = this.getAttribute('data-voice-label') || selectedVoiceName;
    selectedVoiceId = selectedVoiceName;
    document.querySelectorAll('.voice-btn').forEach(btn => btn.classList.remove('selected'));
    this.classList.add('selected');

    const feedbackElement = document.getElementById('feedback');
    if (feedbackElement.textContent === 'Please select a voice before narrating.') {
        feedbackElement.textContent = '';
    }
    feedbackElement.classList.remove('error');

    const voiceSelection = document.getElementById('voice-selection');
    if (voiceSelection) {
        voiceSelection.classList.remove('needs-attention');
    }
}

document.querySelectorAll('.voice-btn').forEach(btn => {
    btn.addEventListener('click', selectVoice);
});

function showLoadingPopup(message = "Generating narration (turn up volume)...", detail = "") {
    const popup = document.getElementById('loading-popup');
    const messageEl = document.getElementById('loading-message');
    const detailEl = document.getElementById('loading-detail');
    if (messageEl) messageEl.textContent = message;
    if (detailEl) detailEl.textContent = detail;
    popup.style.display = 'flex';
}

function hideLoadingPopup() {
    document.getElementById('loading-popup').style.display = 'none';
}

function updateLoadingMessage(message, detail = "") {
    const messageEl = document.getElementById('loading-message');
    const detailEl = document.getElementById('loading-detail');
    if (messageEl) messageEl.textContent = message;
    if (detailEl) detailEl.textContent = detail;
}

function captureAndAnalyseImage() {
    if (!selectedVoiceId) {
        const feedbackElement = document.getElementById('feedback');
        feedbackElement.textContent = 'Please select a voice before narrating.';
        feedbackElement.classList.add('error');
        feedbackElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

        const voiceSelection = document.getElementById('voice-selection');
        if (voiceSelection) {
            voiceSelection.classList.add('needs-attention');
            voiceSelection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
    }

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        pendingCapture = true;
        initWebSocket();
        updateServerStatus('connecting');
        showLoadingPopup("Connecting to server...", "Warming up the GPU if needed");
        return;
    }

    showLoadingPopup("Analysing image...", "Generating description with AI");

    const canvas = document.createElement('canvas');
    canvas.width = cameraFeedElement.videoWidth;
    canvas.height = cameraFeedElement.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(cameraFeedElement, 0, 0, canvas.width, canvas.height);
    const imageDataUrl = canvas.toDataURL('image/jpeg');

    pictureCount++;
    document.getElementById('picture-counter').textContent = `Pictures taken: ${pictureCount}`;

    const capturedImagesContainer = document.getElementById('captured-images');
    const imgWrapper = document.createElement('div');
    imgWrapper.classList.add('image-wrapper');
    imgWrapper.setAttribute('data-picture-number', `Picture ${pictureCount}`);

    const imgElement = document.createElement('img');
    imgElement.src = imageDataUrl;
    imgWrapper.appendChild(imgElement);
    capturedImagesContainer.appendChild(imgWrapper);

    capturedImagesContainer.scrollLeft = capturedImagesContainer.scrollWidth;

    ws.send(JSON.stringify({
        image: imageDataUrl.split(',')[1],
        voiceId: selectedVoiceId,
        voiceName: selectedVoiceName,
        voiceLabel: selectedVoiceLabel,
        pictureCount: pictureCount,
        politenessLevel: politenessLevel
    }));
}

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/narrate`;

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Intentional close for reconnection");
    }

    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
        reconnectAttempts = 0;
        updateServerStatus('online');
        if (pendingCapture) {
            pendingCapture = false;
            captureAndAnalyseImage();
        }
    };

    ws.onmessage = (event) => {
        if (typeof event.data === "string") {
            try {
                const message = JSON.parse(event.data);
                if (message.type === "text_chunk") {
                    let feedbackElement = document.getElementById('feedback');
                    let p = document.querySelector(`p[data-picture-count="${message.pictureCount}"]`);
                    if (!p) {
                        p = document.createElement('p');
                        const timestamp = new Date().toLocaleTimeString();
                        p.setAttribute('data-picture-count', message.pictureCount);
                        const voiceLabel = message.voiceLabel || message.voiceName;
                        p.innerHTML = `<strong>[${timestamp}] [Picture ${message.pictureCount}] [${voiceLabel}]</strong> `;
                        feedbackElement.appendChild(p);
                    }
                    p.innerHTML += `${message.data}`;
                    feedbackElement.scrollTop = feedbackElement.scrollHeight;
                } else if (message.type === "error") {
                    hideLoadingPopup();
                    const feedbackElement = document.getElementById('feedback');
                    const p = document.createElement('p');
                    p.innerHTML = `<strong>Error: ${message.data}</strong>`;
                    p.classList.add('error');
                    feedbackElement.appendChild(p);
                } else if (message.type === "status") {
                    updateLoadingMessage(message.message, message.detail || "");
                } else if (message.type === "voice_status") {
                    updateVoiceStatusIndicators(message.data);
                } else if (message.type === "server_ready") {
                    serverReady = message.ready === true;
                    updateReadyState();
                }
            } catch (error) {
                console.error("Error parsing message:", error);
            }
        } else {
            playAudio(event.data);
        }
    };

    ws.onerror = () => {
        updateServerStatus('connecting');
        handleConnectionError();
    };

    ws.onclose = () => {
        updateServerStatus('offline');
        handleConnectionError();
    };
}

function handleConnectionError() {
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        const delay = RECONNECT_DELAY * Math.pow(2, reconnectAttempts - 1);
        updateServerStatus('connecting');
        setTimeout(initWebSocket, delay);
    } else {
        updateServerStatus('offline');
    }
}

function updateVoiceStatusIndicators(statuses) {
    if (!statuses) {
        return;
    }
    document.querySelectorAll('.voice-btn').forEach(btn => {
        const voiceName = btn.getAttribute('data-voice-name');
        const dot = btn.querySelector('.voice-status-dot');
        if (!dot) {
            return;
        }
        const status = statuses[voiceName] || 'unknown';
        dot.setAttribute('data-status', status);
    });
}

function updateServerStatus(status) {
    serverStatus = status;
    const dot = document.querySelector('.server-status-dot');
    const label = document.querySelector('.server-status-label');
    if (!dot || !label) {
        return;
    }
    dot.setAttribute('data-status', status);
    if (status === 'online') {
        label.textContent = 'Server: Online';
    } else if (status === 'connecting') {
        label.textContent = 'Server: Connecting...';
    } else {
        label.textContent = 'Server: Offline';
    }
}

function updateReadyState() {
    const startButton = document.getElementById('start-btn');
    if (!startButton) {
        return;
    }
    startButton.disabled = false;
    startButton.textContent = 'Press here, once you have selected a voice below';
}

// Add event listener to the start button for capturing and analysing the image
const startButton = document.getElementById('start-btn');
startButton.disabled = false;
startButton.textContent = 'Press here, once you have selected a voice below';
startButton.addEventListener('click', captureAndAnalyseImage);

// Initialise WebSocket connection
initWebSocket();

document.getElementById('politeness-slider').addEventListener('input', function() {
    politenessLevel = parseInt(this.value);
    const valueDisplay = document.getElementById('politeness-value');
    valueDisplay.textContent = this.value;
    valueDisplay.setAttribute('data-level', this.value);
});

