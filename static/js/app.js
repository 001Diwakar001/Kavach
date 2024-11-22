// Function to set the security code
function setSecurityCode() {
    const code = document.getElementById("security-code").value;
    fetch('/set_security_code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById("message-box").innerText = data.message;
        document.getElementById("message-box").style.display = "block";
    })
    .catch(error => {
        console.error("Error setting security code:", error);
        document.getElementById("message-box").innerText = "Failed to set security code.";
        document.getElementById("message-box").style.display = "block";
    });
}

// Function to start listening for the help command
function startListening() {
    fetch('/start_listening', { method: 'POST' })
    .then(response => response.json())
    .then(data => {
        document.getElementById("message-box").innerText = data.message;
        document.getElementById("message-box").style.display = "block";
    })
    .catch(error => {
        console.error("Error starting listener:", error);
        document.getElementById("message-box").innerText = "Failed to start listener.";
        document.getElementById("message-box").style.display = "block";
    });
}

// Establish a WebSocket connection to listen for updates from the server
const socket = io.connect('http://127.0.0.1:5000');

// Listen for speech updates and update the UI
socket.on('speech_update', function(data) {
    console.log("Speech Update: ", data.text);

    // Dynamically update the UI to show recognized speech
    const speechDisplay = document.getElementById("speech-display");
    if (speechDisplay) {
        speechDisplay.innerText = `Recognized Speech: ${data.text}`;
        speechDisplay.style.display = "block";
    }
});
