from flask import Flask, request, jsonify, session
import os
import uuid
from werkzeug.utils import secure_filename
import numpy as np
import requests
import json
import io
from flask_cors import CORS
from tensorflow.keras.models import load_model  # type: ignore
from tensorflow.keras.utils import load_img, img_to_array  # type: ignore
import firebase_admin
from firebase_admin import credentials, db
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*", "allow_headers": "*"}})

# Global variable to store detected device type
device_type_uni = ''

app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Configure upload folder
UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'temp_uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Allowed image file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Load the ML model at startup
MODEL_PATH = os.getenv('MODEL_PATH', 'model.keras')
model = load_model(MODEL_PATH)

# Firebase Setup
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH', 'serviceAccountKey.json'))
firebase_admin.initialize_app(cred, {
    'databaseURL': os.getenv('DATABASE_URL', 'https://uploads-b9310-default-rtdb.firebaseio.com/')
})

# Gemini API Configuration
API_KEY = os.getenv('API_KEY', 'AIzaSyCItld7H0lCR2Tlkw8Qi0MThydbB0-FkUc')
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
GEMINI_HEADERS = {'Content-Type': 'application/json'}

# E-Waste Database (Fallback if Gemini API Fails)
EWASTE_DATABASE = {
    "smartphone": {
        "type": "Smartphone/Mobile Device",
        "elements": "Lithium, Cobalt, Gold, Silver, Copper, Palladium, Rare Earth Elements",
        "environmental_harm": "Contains toxic materials like lead, mercury, and cadmium that can leach into soil and water.",
        "recycling_benefits": "Recycling reduces the need for mining rare earth metals and prevents toxic chemicals from entering ecosystems."
    },
    "laptop": {
        "type": "Laptop/Computer",
        "elements": "Aluminum, Copper, Gold, Silver, Lead, Mercury, Plastic, Glass, Lithium",
        "environmental_harm": "Computers contain flame retardants and heavy metals that are persistent pollutants.",
        "recycling_benefits": "Recycling 1 million laptops saves energy equivalent to electricity used by 3,657 homes in a year."
    }
}

# In-memory lists for event and blog data
events_data = []
blogs_data = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_gemini_response(device_type):
    """Get detailed e-waste recycling information from Gemini API."""
    prompt = f"""
    Provide detailed information about e-waste recycling for a {device_type}. 
    Format the response as a JSON object with these fields:
    - "type": The full name/category of the device
    - "elements": The key materials and elements found in this device (comma-separated values)
    - "environmental_harm": Environmental impacts if improperly disposed (max 50 words)
    - "recycling_benefits": Benefits of properly recycling this device (max 50 words)

    Return ONLY the JSON object with no additional text.
    """

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(GEMINI_URL, headers=GEMINI_HEADERS, json=payload, timeout=10)
        
        if response.status_code == 200:
            res_json = response.json()
            text = res_json['candidates'][0]['content']['parts'][0]['text']

            # Clean up response to get only JSON
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
                
            # Parse JSON response
            try:
                return json.loads(text.strip())
            except json.JSONDecodeError:
                return EWASTE_DATABASE.get(device_type, {})
        else:
            return EWASTE_DATABASE.get(device_type, {})
    
    except Exception as e:
        return EWASTE_DATABASE.get(device_type, {})

def predict_image_from_path(image_path):
    """Predict device type using ML model."""
    img = load_img(image_path, target_size=(128, 128))
    img = img_to_array(img) / 255.0
    img = np.expand_dims(img, axis=0)
    
    prediction = model.predict(img)[0][0]
    return "smartphone" if prediction > 0.5 else "laptop"



@app.route('/upload', methods=['POST', 'OPTIONS'])
def upload_image():
    global device_type_uni

    if request.method == 'OPTIONS':
        return '', 204

    if 'images' not in request.files:
        return jsonify({'error': 'No images part in the request'}), 400

    file = request.files['images']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        # Predict device type and update global variable
        device_type_uni = predict_image_from_path(filepath)

        # Get e-waste information
        device_info = get_gemini_response(device_type_uni)

        return jsonify({
            'success': True,
            'message': f'Image classified as {device_type_uni}',
            'device_type': device_type_uni,
            'device_info': device_info,
        }), 200

    return jsonify({'error': f'File type not allowed: {file.filename}'}), 400


@app.route('/', methods=['GET'])
def hello():
    return jsonify({'hellow':'check'})

@app.route('/analyze', methods=['GET'])
def analyze_ewaste():
    global device_type_uni

    if not device_type_uni:
        return jsonify({'error': 'No device type available. Please upload an image first.'}), 400

    device_info = get_gemini_response(device_type_uni)

    return jsonify(device_info), 200



@app.route('/create_event', methods=['POST'])
def create_event():
    data = request.get_json()
    title = data.get('title')
    description = data.get('description')
    date = data.get('date')
    location = data.get('location')
    image_url = data.get('imageUrl')
    register = data.get('register')

    ref = db.reference('/events')
    ref.push({
        title: {
            'title': title,
            'description': description,
            'date': date,
            'location': location,
            'imageUrl': image_url,
            'register': register
        }
    })

    return jsonify({
        'success': True,
        'message': 'Event created successfully',
        'event_data': data
    }), 200

@app.route('/get_events', methods=['GET'])
def get_events():
    return jsonify({'events': events_data}), 200

if __name__ == '__main__':
    app.run(port=5000)
