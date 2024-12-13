const cameraFeedElement = document.getElementById('camera-feed');
let ws;
let currentStream = null;
let currentDeviceIndex = 0;
let allCameras = [];
let politenessLevel = 5;

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
    const constraints = {
        video: {
            deviceId: deviceId,
            width: { ideal: 640 },
            height: { ideal: 480 }
        }
    };

    navigator.mediaDevices.getUserMedia(constraints)
        .then(stream => {
            currentStream = stream;
            cameraFeedElement.srcObject = stream;
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

let audioQueue = [];
let isPlaying = false;

function playAudio(arrayBuffer) {
    console.log("Attempting to play audio", arrayBuffer);
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
        const audio = new Audio(url);
        audio.play().then(() => {
            audio.addEventListener('ended', playNextAudio);
        }).catch(e => {
            console.error("Error playing audio:", e);
            isPlaying = false;
            playNextAudio();
        });
    } else {
        isPlaying = false;
    }
}

let selectedVoiceName = "Daniel Attenborough";

function selectVoice() {
    selectedVoiceId = this.getAttribute('data-voice-id');
    selectedVoiceName = this.getAttribute('data-voice-name');
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

let selectedVoiceId;



function captureAndAnalyseImage() {
    if (!selectedVoiceId) {
        const feedbackElement = document.getElementById('feedback');
        feedbackElement.textContent = 'Please select a voice before narrating.';
        feedbackElement.classList.add('error');
        return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = cameraFeedElement.videoWidth;
    canvas.height = cameraFeedElement.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(cameraFeedElement, 0, 0, canvas.width, canvas.height);
    const imageDataUrl = canvas.toDataURL('image/jpeg');

    pictureCount++;
    document.getElementById('picture-counter').textContent = `Pictures taken: ${pictureCount}`;

    const capturedImagesContainer = document.getElementById('captured-images');
    const imgWrapper = document.createElement('div'); // Create a wrapper div for the image
    imgWrapper.classList.add('image-wrapper'); // Add class for styling
    imgWrapper.setAttribute('data-picture-number', `Picture ${pictureCount}`); // Set the picture number

    const imgElement = document.createElement('img');
    imgElement.src = imageDataUrl;
    imgWrapper.appendChild(imgElement); // Append the image to the wrapper
    capturedImagesContainer.appendChild(imgWrapper); // Append the wrapper to the container

    // Scroll to the latest image
    capturedImagesContainer.scrollLeft = capturedImagesContainer.scrollWidth;

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ 
            image: imageDataUrl.split(',')[1], 
            voiceId: selectedVoiceId, 
            voiceName: selectedVoiceName, 
            pictureCount: pictureCount,
            politenessLevel: politenessLevel 
        }));
    } else {
        console.error("WebSocket is not open.");
    }
}

// Initialise WebSocket connection and event handlers
function initWebSocket() {
    console.log(`wss://${window.location.host}/narrate`);
    ws = new WebSocket(`wss://${window.location.host}/narrate`);
    ws.binaryType = 'arraybuffer'; // Important for audio data

    ws.onopen = () => {
        console.log("WebSocket connection opened.");
        // Now safe to send messages
    };

    ws.onmessage = (event) => {
        if (typeof event.data === "string") {
            const message = JSON.parse(event.data);
            if (message.type === "text_chunk") {
                let feedbackElement = document.getElementById('feedback');
                let p = document.querySelector(`p[data-picture-count="${message.pictureCount}"]`);
                if (!p) {
                    p = document.createElement('p');
                    const timestamp = new Date().toLocaleTimeString();
                    p.setAttribute('data-picture-count', message.pictureCount);
                    p.innerHTML = `<strong>[${timestamp}] [Picture ${message.pictureCount}] [${message.voiceName}]</strong> `;
                    feedbackElement.appendChild(p);
                }
                p.innerHTML += `${message.data}`;
                feedbackElement.scrollTop = feedbackElement.scrollHeight;
            }
        } else {
            playAudio(event.data);
        }
    };

    ws.onerror = (error) => {
        console.error("WebSocket error:", error);
    };

    ws.onclose = () => {
        console.log("WebSocket connection closed.");
    };
}

// Add event listener to the start button for capturing and analysing the image
document.getElementById('start-btn').addEventListener('click', captureAndAnalyseImage);

// Initialise WebSocket connection
initWebSocket();

let continuousNarrationInterval; // Holds the interval ID for continuous narration

document.getElementById('continuous-narrate-toggle').addEventListener('change', function() {
    if (this.checked) {
        if (!selectedVoiceId) {
            document.getElementById('feedback').textContent = 'Please select a voice before narrating.';
            document.getElementById('feedback').classList.add('error');
            this.checked = false;
            return;
        }
        captureAndAnalyseImage(); // Send the first image immediately
        if (!continuousNarrationInterval) {
            continuousNarrationInterval = setInterval(captureAndAnalyseImage, 5000); // 5-second delay for subsequent images
        }
    } else {
        if (continuousNarrationInterval) {
            clearInterval(continuousNarrationInterval);
            continuousNarrationInterval = null;
        }
    }
});

// Existing code for adding event listener to the start button
document.getElementById('start-btn').addEventListener('click', captureAndAnalyseImage);

// Initialise WebSocket connection
initWebSocket();

let pictureCount = 0;

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
