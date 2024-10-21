from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import azure.cognitiveservices.speech as speechsdk
import threading
import queue
import os
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Azure credentials
speech_key = os.environ.get('AZURE_SPEECH_KEY', 'd7f1bae7919b41479575a01b73316bb6')
service_region = os.environ.get('AZURE_SPEECH_REGION', 'australiaeast')
endpoint = os.environ.get('AZURE_SPEECH_ENDPOINT', 'https://australiaeast.api.cognitive.microsoft.com/')

# ... (keep the target_languages and speech_recognition_languages dictionaries as they are)
target_languages = {
    'Arabic': 'ar',
    'Bengali': 'bn',
    'Chinese (Simplified)': 'zh-Hans',
    'Chinese (Traditional)': 'zh-Hant',
    'English': 'en',
    'French': 'fr',
    'German': 'de',
    'Gujarati': 'gu',
    'Hindi': 'hi',
    'Italian': 'it',
    'Japanese': 'ja',
    'Kannada': 'kn',
    'Korean': 'ko',
    'Malayalam': 'ml',
    'Marathi': 'mr',
    'Nepali': 'ne',
    'Persian': 'fa',
    'Portuguese': 'pt',
    'Punjabi': 'pa',
    'Russian': 'ru',
    "Sinhala ": "si",
    'Spanish': 'es',
    'Tamil': 'ta',
    'Telugu': 'te',
    'Thai': 'th',
    'Turkish': 'tr',
    'Urdu': 'ur',
    'Vietnamese': 'vi'
}

# Language-specific codes for speech recognition
speech_recognition_languages = {
    'Arabic': 'ar-SA',
    'Bengali': 'bn-IN',
    'Chinese (Simplified)': 'zh-CN',
    'Chinese (Traditional)': 'zh-TW',
    'English': 'en-US',
    'French': 'fr-FR',
    'German': 'de-DE',
    'Gujarati': 'gu-IN',
    'Hindi': 'hi-IN',
    'Italian': 'it-IT',
    'Japanese': 'ja-JP',
    'Kannada': 'kn-IN',
    'Korean': 'ko-KR',
    'Malayalam': 'ml-IN',
   'Marathi': 'mr-IN',
    "Sinhala ": "si",
    'Nepali': 'ne-NP',
    'Persian': 'fa-IR',
    'Portuguese': 'pt-BR',
    'Punjabi': 'pa-IN',
    'Russian': 'ru-RU',
    'Spanish': 'es-ES',
    'Tamil': 'ta-IN',
    'Telugu': 'te-IN',
    'Thai': 'th-TH',
    'Turkish': 'tr-TR',
    'Urdu': 'ur-PK',
    'Vietnamese': 'vi-VN'
}

translation_history = []
current_partial_text = ""
is_recording = False
result_queue = queue.Queue()
@app.route('/')
def index():
    return jsonify({
        "message": "Speech Translation API is working fine!",
        "target_languages": sorted(target_languages.keys()),
        "speech_recognition_languages": sorted(speech_recognition_languages.keys())
    })

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "message": "Speech Translation API is working fine!"})

@app.route('/')
def index():
    return jsonify({
        "target_languages": sorted(target_languages.keys()),
        "speech_recognition_languages": sorted(speech_recognition_languages.keys())
    })
@app.route('/')
def welcome():
    return jsonify({
        "message": "Welcome to the Real-Time Speech Translator API!",
        "version": "1.0",
        "endpoints": {
            "start_recording": "/api/start_recording",
            "stop_recording": "/api/stop_recording",
            "get_translation": "/api/get_translation",
            "clear_history": "/api/clear_history"
        },
        "instructions": "To use this API, make POST requests to start and stop recording, and GET requests to retrieve translations. Ensure you have the necessary permissions and API key to access these endpoints."
    })
@app.route('/start_recording', methods=['POST'])
def start_recording():
    global is_recording
    if not is_recording:
        is_recording = True
        source_lang = request.json['source_lang']
        target_lang = request.json['target_lang']
        threading.Thread(target=start_translation, args=(source_lang, target_lang)).start()
        return jsonify({"status": "started"})
    return jsonify({"status": "already_recording"})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global is_recording
    is_recording = False
    return jsonify({"status": "stopped"})

@app.route('/get_translation')
def get_translation():
    global current_partial_text
    try:
        result = result_queue.get_nowait()
        translation_history.append(result)
        current_partial_text = ""
    except queue.Empty:
        result = None
    
    return jsonify({
        "history": translation_history,
        "partial": current_partial_text
    })

@app.route('/clear_history', methods=['POST'])
def clear_history():
    global translation_history, current_partial_text
    translation_history = []
    current_partial_text = ""
    return jsonify({"status": "cleared"})

def start_translation(source_lang, target_lang):
    global current_partial_text, is_recording

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    translation_config = speechsdk.translation.SpeechTranslationConfig(
        subscription=speech_key,
        region=service_region
    )
    translation_config.speech_recognition_language = speech_recognition_languages[source_lang]
    translation_config.add_target_language(target_languages[target_lang])

    translator = speechsdk.translation.TranslationRecognizer(
        translation_config=translation_config,
        audio_config=audio_config
    )

    def handle_result(event):
        global current_partial_text
        if event.result.reason == speechsdk.ResultReason.TranslatedSpeech:
            translations = event.result.translations
            translated_text = translations.get(target_languages[target_lang], "Translation not available")
            if translated_text.strip():
                result_queue.put(translated_text)

    def handle_intermediate_result(event):
        global current_partial_text
        if event.result.reason == speechsdk.ResultReason.TranslatingSpeech:
            translations = event.result.translations
            translated_text = translations.get(target_languages[target_lang], "")
            if translated_text.strip():
                current_partial_text = translated_text

    translator.recognized.connect(handle_result)
    translator.recognizing.connect(handle_intermediate_result)

    translator.start_continuous_recognition()

    while is_recording:
        pass

    translator.stop_continuous_recognition()

# Uncomment if running locally
# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=8000, debug=True)
