from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from vosk import Model, KaldiRecognizer
import pyaudio
import json
import requests
from twilio.rest import Client
import re
from transformers import pipeline
import threading

app = Flask(__name__)
socketio = SocketIO(app)

# Set your IPinfo API token and Twilio credentials
OPENCAGE_API_KEY = "3a474e5ae20b4e66ba83572e373299e5"
TWILIO_ACCOUNT_SIDS = ["ACeef674ca1ae1535b91413508d353e3f5"]  # Add more if needed
TWILIO_AUTH_TOKENS = ["04cfb558cfbfac43687c98d3a4ba40a6"]  # Add more if needed
TWILIO_PHONE_NUMBERS = ["+19124173568"]  # Add more if needed
TO_PHONE_NUMBERS = ["+918630797603"]  # Add more phone numbers as needed

# Initialize Vosk Model and NLP Model
model_path = "C:\\Users\\diwak\\Downloads\\vosk-model-en-us-0.22\\vosk-model-en-us-0.22"  # Use a larger and more accurate model
model = Model(model_path)
recognizer = KaldiRecognizer(model, 16000)
nlp = pipeline("text-classification", model="j-hartmann/emotion-english-distilroberta-base", return_all_scores=True)

SECURITY_CODE = None

# Route to serve the main page
@app.route('/')
def home():
    return render_template('index.html')

# Endpoint for setting security code
@app.route('/set_security_code', methods=['POST'])
def set_security_code():
    data = request.get_json()
    global SECURITY_CODE
    SECURITY_CODE = data.get('code').strip().lower()  # Save the security code
    return jsonify({'message': 'Security code set successfully.'})

# Utility function to extract numbers from text
def extract_numbers(text):
    """Extract numbers from the recognized text."""
    numbers = re.findall(r'\b\d+\b', text)  # Match numeric sequences
    return numbers

# Endpoint to start listening
@app.route('/start_listening', methods=['POST'])
def start_listening():
    if SECURITY_CODE is None:
        return jsonify({'message': 'Security code not set!'}), 400

    # Run the voice recognition listener in a separate thread to avoid blocking
    def listen_for_help():
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
        stream.start_stream()

        print(f"Listening for 'help' followed by '{SECURITY_CODE}'...")

        while True:
            data = stream.read(4096, exception_on_overflow=False)
            if recognizer.AcceptWaveform(data):
                result = recognizer.Result()
                result_json = json.loads(result)
                text = result_json.get("text", "").lower()
                print(f"Heard: {text}")

                # Emit the text to the frontend via WebSocket
                socketio.emit('speech_update', {'text': text})

                # Extract and log numbers
                numbers = extract_numbers(text)
                if numbers:
                    print(f"Numbers detected: {numbers}")

                # Regex to match "help" followed by security code
                pattern = rf"(help\s+.*)+{SECURITY_CODE}"
                if re.search(pattern, text):
                    on_help_detected()
                    break  # Stop listening after activation

        # Cleanup
        stream.stop_stream()
        stream.close()
        audio.terminate()

    # Function to trigger actions upon help detection
    def on_help_detected():
        print("Alert! Help detected. Fetching location...")
        fetch_location_ipinfo()
        make_call()

    # Function to send SMS
    def send_sms(message_body):
        for i in range(len(TWILIO_ACCOUNT_SIDS)):
            client = Client(TWILIO_ACCOUNT_SIDS[i], TWILIO_AUTH_TOKENS[i])
            for number in TO_PHONE_NUMBERS:
                try:
                    message = client.messages.create(
                        body=message_body,
                        from_=TWILIO_PHONE_NUMBERS[i],
                        to=number
                    )
                    print(f"SMS sent to {number}: {message.sid}")
                except Exception as e:
                    print(f"Failed to send SMS to {number} using account {i+1}: {e}")

    # Function to make a call with a spoken message
    def make_call():
        for i in range(len(TWILIO_ACCOUNT_SIDS)):
            client = Client(TWILIO_ACCOUNT_SIDS[i], TWILIO_AUTH_TOKENS[i])
            for number in TO_PHONE_NUMBERS:
                try:
                    call = client.calls.create(
                        twiml="<Response><Say>I am in need of help. My location has been sent via message. Please help me. SOS.</Say></Response>",
                        from_=TWILIO_PHONE_NUMBERS[i],
                        to=number
                    )
                    print(f"Call initiated to {number} using account {i+1}: {call.sid}")
                except Exception as e:
                    print(f"Failed to call {number} using account {i+1}: {e}")

    # Function to fetch location using IPinfo API
    def fetch_location_ipinfo():
        url = f"https://ipinfo.io/json?token={OPENCAGE_API_KEY}"
        try:
            response = requests.get(url)
            data = response.json()
            location = data.get("loc").split(",")
            latitude = location[0]
            longitude = location[1]

            location_str = f"Latitude: {latitude}, Longitude: {longitude}"
            print(f"Location: {location_str}")

            maps_url = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"
            print(f"Google Maps link to location: {maps_url}")

            # Send SMS with location
            send_sms(f"Help detected! Location: {maps_url}")

        except Exception as e:
            print("Could not fetch location:", e)

    # Start the listener in a separate thread to keep the Flask app responsive
    thread = threading.Thread(target=listen_for_help)
    thread.start()

    return jsonify({'message': 'Listening for help command...'})

if __name__ == '__main__':
    socketio.run(app, debug=True)
