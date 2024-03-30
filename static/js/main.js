const cameraFeedElement = document.getElementById('camera-feed');
let ws; // WebSocket connection

// Initialize camera feed
if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(function(stream) {
            cameraFeedElement.srcObject = stream;
            cameraFeedElement.play();
        })
        .catch(function(error) {
            console.error("Webcam access denied:", error);
        });
}

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
            playNextAudio(); // Attempt to play the next in queue if current fails
        });
    } else {
        isPlaying = false;
    }
}

let selectedVoiceName = "Daniel Attenborough"; // Default voice name

function selectVoice() {
    selectedVoiceId = this.getAttribute('data-voice-id');
    selectedVoiceName = this.getAttribute('data-voice-name');
    document.querySelectorAll('.voice-btn').forEach(btn => btn.classList.remove('selected'));
    this.classList.add('selected');
    document.getElementById('feedback').classList.remove('error'); // Remove error class
    // document.getElementById('feedback').textContent = ''; // Clear any previous error message
}

// Add event listeners to voice selection buttons
document.querySelectorAll('.voice-btn').forEach(btn => {
    btn.addEventListener('click', selectVoice);
});

let selectedVoiceId; // Declare selectedVoiceId globally



// Modify captureAndAnalyzeImage to include selectedVoiceId
function captureAndAnalyzeImage() {
    if (!selectedVoiceId) {
        const feedbackElement = document.getElementById('feedback');
        feedbackElement.textContent = 'Please select a voice before narrating.';
        feedbackElement.classList.add('error'); // Add this line
        return;
    }
    pictureCount++;
    document.getElementById('picture-counter').textContent = `Pictures taken: ${pictureCount}`;
    // Reset the feedback element's content
    const feedbackElement = document.getElementById('feedback');
    // feedbackElement.textContent = '';
    
    const canvas = document.createElement('canvas');
    canvas.width = cameraFeedElement.videoWidth;
    canvas.height = cameraFeedElement.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(cameraFeedElement, 0, 0, canvas.width, canvas.height);
    const imageDataUrl = canvas.toDataURL('image/jpeg');
    const base64ImageContent = imageDataUrl.split(',')[1];

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ image: base64ImageContent, voiceId: selectedVoiceId, voiceName: selectedVoiceName, pictureCount: pictureCount }));
    } else {
        console.error("WebSocket is not open.");
    }
}

// Initialize WebSocket connection and event handlers
function initWebSocket() {
    console.log(`ws://${window.location.host}/narrate`);
    ws = new WebSocket(`ws://${window.location.host}/narrate`);
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
                    p.textContent = `[${timestamp}] [Picture ${message.pictureCount}] [${message.voiceName}] `;
                    feedbackElement.appendChild(p);
                }
                p.textContent += message.data;
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

// Add event listener to the start button for capturing and analyzing the image
document.getElementById('start-btn').addEventListener('click', captureAndAnalyzeImage);

// Initialize WebSocket connection
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
        captureAndAnalyzeImage(); // Send the first image immediately
        if (!continuousNarrationInterval) {
            continuousNarrationInterval = setInterval(captureAndAnalyzeImage, 5000); // 5-second delay for subsequent images
        }
    } else {
        if (continuousNarrationInterval) {
            clearInterval(continuousNarrationInterval);
            continuousNarrationInterval = null;
        }
    }
});

// Existing code for adding event listener to the start button
document.getElementById('start-btn').addEventListener('click', captureAndAnalyzeImage);

// Initialize WebSocket connection
initWebSocket();

let pictureCount = 0;
