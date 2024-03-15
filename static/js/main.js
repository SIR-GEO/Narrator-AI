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

// Function to capture the current frame and send it for analysis
function captureAndAnalyzeImage() {
    const canvas = document.createElement('canvas');
    canvas.width = cameraFeedElement.videoWidth;
    canvas.height = cameraFeedElement.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(cameraFeedElement, 0, 0, canvas.width, canvas.height);
    const imageDataUrl = canvas.toDataURL('image/jpeg');
    const base64ImageContent = imageDataUrl.split(',')[1];

    // Ensure WebSocket is open before sending
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ image: base64ImageContent }));
    } else {
        console.error("WebSocket is not open.");
    }
}

// Initialize WebSocket connection and event handlers
function initWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/narrate`);
    ws.binaryType = 'arraybuffer'; // Important for audio data

    ws.onopen = () => {
        console.log("WebSocket connection opened.");
        // Now safe to send messages
    };

    ws.onmessage = (event) => {
        console.log("WebSocket message received", event.data);
        if (typeof event.data !== "string") {
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

// Add a button for capturing and analyzing the image
const analyzeButton = document.createElement('button');
analyzeButton.textContent = 'Analyze Image';
analyzeButton.onclick = captureAndAnalyzeImage;
document.body.appendChild(analyzeButton);