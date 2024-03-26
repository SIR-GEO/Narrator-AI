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

function playAudio(arrayBuffer) {
    console.log("Attempting to play audio", arrayBuffer);
    const blob = new Blob([arrayBuffer], { type: 'audio/mp3' });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play().catch(e => console.error("Error playing audio:", e));
}

let selectedVoiceName = "Daniel Attenborough"; // Default voice name

function selectVoice() {
    selectedVoiceId = this.getAttribute('data-voice-id');
    selectedVoiceName = this.getAttribute('data-voice-name'); // Update the voice name
    document.querySelectorAll('.voice-btn').forEach(btn => btn.classList.remove('selected'));
    this.classList.add('selected');
}

// Add event listeners to voice selection buttons
document.querySelectorAll('.voice-btn').forEach(btn => {
    btn.addEventListener('click', selectVoice);
});

// Modify captureAndAnalyzeImage to include selectedVoiceId
function captureAndAnalyzeImage() {
    // Reset the feedback element's content
    const feedbackElement = document.getElementById('feedback');
    feedbackElement.textContent = '';
    
    const canvas = document.createElement('canvas');
    canvas.width = cameraFeedElement.videoWidth;
    canvas.height = cameraFeedElement.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(cameraFeedElement, 0, 0, canvas.width, canvas.height);
    const imageDataUrl = canvas.toDataURL('image/jpeg');
    const base64ImageContent = imageDataUrl.split(',')[1];

    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ image: base64ImageContent, voiceId: selectedVoiceId, voiceName: selectedVoiceName }));
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
                // Append each text chunk to the feedback div
                const feedbackElement = document.getElementById('feedback');
                feedbackElement.textContent += message.data;
            } else if (message.type === "text") {
                // Handle other text messages, if any
                document.getElementById('feedback').textContent = message.data;
            }
        } else {
            // If the message is not a string, it's the audio data
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
