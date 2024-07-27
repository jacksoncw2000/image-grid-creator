from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime
from grid_images import grid_images
from utility.utils_general import str_to_bool, ensure_directory_exists

from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.logger.setLevel(logging.DEBUG)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ensure_directory_exists(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024  # for example, limit to 256MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/test', methods=['GET'])
def test_route():
    return jsonify({"message": "Test successful"}), 200

@app.route('/')
def home():
    return "Welcome to the Image Grid API"

@app.route('/api/generate-grid', methods=['POST'])
def generate_grid():
    app.logger.debug("Received request for generate_grid")
    try:
        if 'files[]' not in request.files:
            app.logger.error("No files part in the request")
            return jsonify({'error': 'No files part'}), 400
        
        files = request.files.getlist('files[]')
        if len(files) == 0:
            app.logger.error("No selected file")
            return jsonify({'error': 'No selected file'}), 400
        
        # Create a new directory for this batch of uploads
        batch_folder = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(str(datetime.now())))
        os.makedirs(batch_folder)
        app.logger.debug(f"Created batch folder: {batch_folder}")
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(batch_folder, filename))
        app.logger.debug(f"Saved {len(files)} files")
        
        # Get parameters from the request
        individual_image_size = int(request.form.get('individualImageSize', 1000))
        randomized_order = str_to_bool(request.form.get('randomizedOrder', 'true'))
        printer_paper_format = str_to_bool(request.form.get('printerPaperFormat', 'false'))
        app.logger.debug(f"Parameters: size={individual_image_size}, randomized={randomized_order}, printer_format={printer_paper_format}")
        
        # Generate the image grid
        outputs_directory = 'outputs'
        ensure_directory_exists(outputs_directory)
        base_directory_name = os.path.basename(batch_folder)
        
        grid_file_path = grid_images(batch_folder, base_directory_name, outputs_directory, 
                                           individual_image_size=individual_image_size, 
                                           randomized_order=randomized_order, 
                                           printer_paper_format=printer_paper_format)
        app.logger.debug(f"Grid generated: {grid_file_path}")
        
        if grid_file_path is None or not os.path.exists(grid_file_path):
            raise FileNotFoundError("Grid file not generated or not found")
        
        return send_file(grid_file_path, as_attachment=True, download_name='grid.png', mimetype='image/png')
    except Exception as e:
        app.logger.error(f"Error in generate_grid: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)