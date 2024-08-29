from flask import Flask, request, jsonify, send_from_directory
import os
import shutil

# Initialize the Flask application
app = Flask(__name__, static_url_path='/apk', static_folder='/var/www/ota_update_server/apk')

# Default version info
version_info = {
    "version": "1.0.0",
    "url": "http://43.226.218.98/apk/app-v1.0.0.apk",
    "release_notes": "Initial release."
}

# Define your routes below
@app.route('/api/latest-version', methods=['GET'])
def get_latest_version():
    """Endpoint to get the latest version information."""
    return jsonify(version_info)

@app.route('/api/update-version', methods=['POST'])
def update_version():
    """Endpoint to update the version information."""
    data = request.json
    if not data or 'version' not in data or 'url' not in data or 'release_notes' not in data:
        return jsonify({"error": "Invalid input"}), 400

    version_info['version'] = data['version']
    version_info['url'] = data['url']
    version_info['release_notes'] = data['release_notes']

    return jsonify({"message": "Version information updated successfully"}), 200

@app.route('/apk/<path:filename>', methods=['GET'])
def download_apk(filename):
    """Endpoint to download an APK file."""
    return send_from_directory('/var/www/ota_update_server/apk', filename)

@app.route('/api/upload-apk', methods=['POST'])
def upload_apk():
    """Endpoint to upload a new APK and update the latest version."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the new APK with a versioned filename
    version = request.form['version']
    versioned_filename = f"app-v{version}.apk"
    file_path = os.path.join(app.static_folder, versioned_filename)
    file.save(file_path)

    # Ensure the latest directory exists
    latest_dir = os.path.join(app.static_folder, 'latest')
    if not os.path.exists(latest_dir):
        os.makedirs(latest_dir)

    # Clean the latest directory (delete all existing files)
    for f in os.listdir(latest_dir):
        file_path_to_remove = os.path.join(latest_dir, f)
        if os.path.isfile(file_path_to_remove):
            os.unlink(file_path_to_remove)

    # Verify the file was saved correctly and has content
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        # Copy the file to the latest directory as app-debug.apk
        latest_apk_path = os.path.join(latest_dir, 'app-debug.apk')
        shutil.copyfile(file_path, latest_apk_path)
    else:
        print(f"Error: The file {file_path} was not saved correctly and cannot be copied.")

    # Update the version information
    version_info['version'] = version
    version_info['url'] = f"http://43.226.218.98/apk/{versioned_filename}"
    version_info['release_notes'] = request.form.get('release_notes', 'No release notes provided')

    return jsonify({"message": "APK uploaded and version information updated successfully"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
