from flask import Flask, request, jsonify
import subprocess
import os
import hashlib
from flask_caching import Cache
from pydub import AudioSegment

app = Flask(__name__)

# Configure caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/tts', methods=['POST'])
def generate_tts():
    data = request.json
    text = data.get('text')
    language = data.get('language')
    gender = data.get('gender')

    if not text or not language or not gender:
        return jsonify({'error': 'Text, language, and gender are required'}), 400

    # Generate a unique filename based on text content
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:10]  # Adjust hash length as needed
    out_path = f'/tmp/speech_{text_hash}.wav'

    cache_key = f"{language}_{gender}_{text_hash}"
    cached_path = cache.get(cache_key)

    if cached_path:
        return jsonify({'message': 'TTS retrieved from cache', 'out_path': cached_path}), 200

    try:
        # Run the TTS command to generate the audio file
        cmd = f'python inference.py --language "{language}" --gender "{gender}" --sample_text "{text}" --output_file {out_path}'
        subprocess.run(cmd, shell=True, check=True)

        if os.path.exists(out_path):
            # Convert audio to 8000 Hz mono format
            converted_path = convert_to_8000_mono(out_path)

            # Cache the converted file path
            cache.set(cache_key, converted_path)

            return jsonify({'message': 'TTS generated and converted successfully', 'out_path': converted_path}), 200
        else:
            return jsonify({'error': 'Failed to generate TTS'}), 500
    except subprocess.CalledProcessError as e:
        return jsonify({'error': str(e)}), 500

def convert_to_8000_mono(input_path):
    # Load the original audio file
    audio = AudioSegment.from_file(input_path)

    # Set parameters for conversion
    sample_rate = 8000
    channels = 1

    # Apply the conversion
    audio = audio.set_frame_rate(sample_rate).set_channels(channels)

    # Output path for converted file
    converted_path = f'/tmp/converted_{os.path.basename(input_path)}'

    # Export the converted audio file
    audio.export(converted_path, format='wav')

    return converted_path

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

