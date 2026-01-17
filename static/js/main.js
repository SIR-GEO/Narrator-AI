// Add browser compatibility checks at the start of the file
if (!navigator.mediaDevices) {
    navigator.mediaDevices = {};
}

// Polyfill getUserMedia
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

// Add mobile-specific camera constraints
function getMobileConstraints(deviceId) {
    const constraints = {
        video: {
            deviceId: deviceId ? { exact: deviceId } : undefined,
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: { ideal: "environment" }  // Prefer back camera on mobile
        }
    };

    // Add iOS-specific constraints
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
const RECONNECT_DELAY = 2000; // 2 seconds
let serverStatus = 'offline';
let serverReady = false;

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
                switchCamera(); // Initialize the first camera
            }
        })
        .catch(error => console.error("Could not get cameras:", error));
}

function switchCamera() {
    stopCurrentVideoStream();
    currentDeviceIndex = (currentDeviceIndex + 1) % allCameras.length;
    const deviceId = allCameras[currentDeviceIndex].deviceId;
    const constraints = getMobileConstraints(deviceId);

    navigator.mediaDevices.getUserMedia(constraints)
        .then(stream => {
            currentStream = stream;
            try {
                cameraFeedElement.srcObject = stream;
            } catch (error) {
                // Fallback for older browsers
                const videoURL = window.URL || window.webkitURL;
                cameraFeedElement.src = videoURL.createObjectURL(stream);
            }
        })
        .catch(error => {
            console.error("Could not switch camera:", error);
            console.error("Error name: ", error.name);
            console.error("Error message: ", error.message);
            handleCameraError(error);
        });
}

function handleCameraError(error) {
    if (error.name === 'NotAllowedError') {
        alert('Camera access was denied. Please allow camera access for this site.');
    } else if (error.name === 'NotFoundError') {
        alert('No camera found. Please ensure a camera is properly connected or integrated.');
    } else if (error.name === 'NotReadableError') {
        alert('Camera is currently being used by another application. Please close that application and try again.');
    } else if (error.name === 'OverconstrainedError') {
        alert('No camera matches the requested constraints. Trying default settings...');
        fallbackToDefaultCamera();
    } else {
        alert('An unknown error occurred when trying to access the camera.');
    }
}

function fallbackToDefaultCamera() {
    const constraints = {
        video: true // Use default settings
    };
    navigator.mediaDevices.getUserMedia(constraints)
        .then(stream => {
            currentStream = stream;
            cameraFeedElement.srcObject = stream;
        })
        .catch(error => {
            console.error("Could not access default camera:", error);
        });
}

getCameras();

document.getElementById('toggle-camera-btn').addEventListener('click', switchCamera);

function playAudio(arrayBuffer) {
    console.log("Attempting to play audio", arrayBuffer);
    const blob = new Blob([arrayBuffer], { type: 'audio/mp3' });
    audioQueue.push(blob);
    if (!isPlaying) {
        hideLoadingPopup();
        playNextAudio();
    }
}

function playNextAudio() {
    if (audioQueue.length > 0) {
        isPlaying = true;
        const url = URL.createObjectURL(audioQueue.shift());
        const audio = new Audio();
        
        // iOS requires user interaction before playing audio
        audio.setAttribute('playsinline', '');
        audio.setAttribute('webkit-playsinline', '');
        
        audio.src = url;
        
        // Add error handling for audio playback
        audio.onerror = (e) => {
            console.error("Audio playback error:", e);
            isPlaying = false;
            playNextAudio();
        };

        // Ensure proper cleanup
        audio.onended = () => {
            URL.revokeObjectURL(url);
            audio.onended = null;
            audio.onerror = null;
            playNextAudio();
        };

        // Handle iOS audio playback
        const playPromise = audio.play();
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                console.error("Audio playback failed:", error);
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
    selectedVoiceId = selectedVoiceName; // Use voice name as ID for XTTS
    document.querySelectorAll('.voice-btn').forEach(btn => btn.classList.remove('selected'));
    this.classList.add('selected');

    // Check if the current feedback is the voice selection warning before clearing
    const feedbackElement = document.getElementById('feedback');
    if (feedbackElement.textContent === 'Please select a voice before narrating.') {
        feedbackElement.textContent = ''; // Clear the warning message
    }
    feedbackElement.classList.remove('error'); // Remove the error class if present
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

function scrollToVoiceSelection() {
    document.getElementById('voice-selection').scrollIntoView({ behavior: 'smooth' });
}

function captureAndAnalyseImage() {
    if (!selectedVoiceId) {
        const feedbackElement = document.getElementById('feedback');
        feedbackElement.textContent = 'Please select a voice before narrating.';
        feedbackElement.classList.add('error');
        scrollToVoiceSelection();
        return;
    }

    if (!ws || ws.readyState !== WebSocket.OPEN) {
        console.log("WebSocket is not connected. Attempting to reconnect...");
        initWebSocket();
        updateServerStatus('connecting');
        const feedbackElement = document.getElementById('feedback');
        const p = document.createElement('p');
        p.innerHTML = '<strong>Connecting to server...</strong>';
        feedbackElement.appendChild(p);
        return;
    }

    showLoadingPopup("Analysing image...", "Generating description with AI");

    try {
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
    } catch (error) {
        console.error("Error capturing/sending image:", error);
        const feedbackElement = document.getElementById('feedback');
        const p = document.createElement('p');
        p.innerHTML = '<strong>Error:</strong> Failed to capture or send image.';
        feedbackElement.appendChild(p);
        hideLoadingPopup();
    }
}

function initWebSocket() {
    // Determine the correct WebSocket protocol based on the page protocol
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/narrate`;
    
    console.log(`Connecting to WebSocket at: ${wsUrl}`);
    
    // Close existing connection if any
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Intentional close for reconnection");
    }

    ws = new WebSocket(wsUrl);
    ws.binaryType = 'arraybuffer';

    ws.onopen = () => {
        console.log("WebSocket connection opened successfully");
        reconnectAttempts = 0; // Reset reconnection attempts on successful connection
        updateServerStatus('online');
        
        // Show connection status to user
        const feedbackElement = document.getElementById('feedback');
        const p = document.createElement('p');
        // p.innerHTML = '<strong>Connected to server</strong>';
        feedbackElement.appendChild(p);
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
                    // Handle status updates from backend
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

    ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        updateServerStatus('connecting');
        handleConnectionError();
    };

    ws.onclose = (event) => {
        console.log("WebSocket connection closed.", event.code, event.reason);
        updateServerStatus('offline');
        handleConnectionError();
    };
}

function handleConnectionError() {
    if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        const delay = RECONNECT_DELAY * Math.pow(2, reconnectAttempts - 1); // Exponential backoff
        console.log(`Attempting to reconnect (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS}) in ${delay/1000} seconds...`);
        updateServerStatus('connecting');
        
        // Show reconnection status to user
        const feedbackElement = document.getElementById('feedback');
        const p = document.createElement('p');
        p.innerHTML = `<strong>Connection lost. Reconnecting... (Attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})</strong>`;
        feedbackElement.appendChild(p);
        
        setTimeout(initWebSocket, delay);
    } else {
        console.log("Max reconnection attempts reached");
        updateServerStatus('offline');
        const feedbackElement = document.getElementById('feedback');
        const p = document.createElement('p');
        p.innerHTML = '<strong>Could not connect to server. Please refresh the page to try again.</strong>';
        p.classList.add('error');
        feedbackElement.appendChild(p);
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
        if (status === 'ready') {
            dot.title = 'Ready';
        } else if (status === 'partial') {
            dot.title = 'Samples available (slower on first use)';
        } else if (status === 'missing') {
            dot.title = 'No samples found';
        } else {
            dot.title = 'Status unknown';
        }
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
    if (serverReady) {
        startButton.disabled = false;
        startButton.textContent = 'Press here, once you have selected a voice below';
    } else {
        startButton.disabled = true;
        startButton.textContent = 'Warming up...';
    }
}

// Add event listener to the start button for capturing and analysing the image
const startButton = document.getElementById('start-btn');
startButton.disabled = true;
startButton.textContent = 'Warming up...';
startButton.addEventListener('click', captureAndAnalyseImage);

// Initialize WebSocket connection
initWebSocket();

document.getElementById('politeness-slider').addEventListener('input', function() {
    politenessLevel = parseInt(this.value);
    const valueDisplay = document.getElementById('politeness-value');
    valueDisplay.textContent = this.value;
    valueDisplay.setAttribute('data-level', this.value);
});

document.addEventListener('DOMContentLoaded', function() {
    const valueDisplay = document.getElementById('politeness-value');
    valueDisplay.setAttribute('data-level', '5');
});
