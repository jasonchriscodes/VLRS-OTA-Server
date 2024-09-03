from flask import Flask, request, jsonify, send_from_directory
import os
import shutil
import json

# Initialize the Flask application
app = Flask(__name__, static_url_path='/apk', static_folder='/var/www/ota_update_server/apk')

# Path to the file where version info will be saved
version_info_file = '/var/www/ota_update_server/version_info.json'

# Function to get the latest APK version from the /latest directory
def get_latest_apk_version():
    latest_dir = os.path.join(app.static_folder, 'latest')
    if os.path.exists(latest_dir) and os.listdir(latest_dir):
        apk_files = [f for f in os.listdir(latest_dir) if os.path.isfile(os.path.join(latest_dir, f))]
        if apk_files:
            latest_apk = apk_files[0]  # Assuming only one APK file exists in the latest directory
            version = latest_apk.split('-v')[-1].split('.apk')[0]  # Extract version from filename
            return version, latest_apk
    return None, None

# Function to ensure version info is always up-to-date with the latest APK
def update_version_info():
    latest_version, latest_apk_name = get_latest_apk_version()
    if latest_version:
        version_info = {
            "version": latest_version,
            "url": f"http://43.226.218.98/apk/latest/{latest_apk_name}",
            "release_notes": "Auto detected version on server start."
        }
        # Save this information to the file so it persists across restarts
        with open(version_info_file, 'w') as f:
            json.dump(version_info, f)
    else:
        # If no APK is found, load existing version_info.json or fallback to default
        if os.path.exists(version_info_file):
            with open(version_info_file, 'r') as f:
                version_info = json.load(f)
        else:
            version_info = {
                "version": "1.0.0",
                "url": "http://43.226.218.98/apk/app-v1.0.0.apk",
                "release_notes": "Initial release."
            }
            with open(version_info_file, 'w') as f:
                json.dump(version_info, f)
    return version_info

# Ensure the version_info is updated on server startup
version_info = update_version_info()

@app.route('/api/latest-version', methods=['GET'])
def get_latest_version():
    """Endpoint to get the latest version information."""
    if version_info:
        return jsonify(version_info)
    else:
        return jsonify({"error": "No version information available"}), 404


@app.route('/api/update-version', methods=['POST'])
def update_version():
    """Endpoint to update the version information."""
    data = request.json
    if not data or 'version' not in data or 'url' not in data or 'release_notes' not in data:
        return jsonify({"error": "Invalid input"}), 400

    version_info['version'] = data['version']
    version_info['url'] = data['url']
    version_info['release_notes'] = data['release_notes']

    # Save the updated version info to the file
    with open(version_info_file, 'w') as f:
        json.dump(version_info, f)

    return jsonify({"message": "Version information updated successfully"}), 200

# Function to get the current APK version from the /current directory
def get_current_apk_version():
    current_dir = os.path.join(app.static_folder, 'current')
    if os.path.exists(current_dir) and os.listdir(current_dir):
        apk_files = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]
        if apk_files:
            current_apk = apk_files[0]  # Assuming only one APK file exists in the current directory
            version = current_apk.split('-v')[-1].split('.apk')[0]  # Extract version from filename
            return version, current_apk
    return None, None

# New API endpoint to get the current version information
@app.route('/api/current-version', methods=['GET'])
def get_current_version():
    """Endpoint to get the current version information."""
    current_version, current_apk_name = get_current_apk_version()
    if current_version:
        current_version_info = {
            "version": current_version,
            "url": f"http://43.226.218.98/apk/current/{current_apk_name}",
            "release_notes": "Auto detected current version."
        }
    else:
        current_version_info = {
            "version": "1.0.0",
            "url": "http://43.226.218.98/apk/current/app-v1.0.0.apk",
            "release_notes": "Initial release."
        }
    return jsonify(current_version_info)

@app.route('/api/update-current-folder', methods=['POST'])
def update_current_folder():
    """
    Endpoint to update the 'current' folder with the contents of the 'latest' folder.
    """
    current_dir = os.path.join(app.static_folder, 'current')
    latest_dir = os.path.join(app.static_folder, 'latest')

    # Clean the current directory (delete all existing files)
    if os.path.exists(current_dir):
        for f in os.listdir(current_dir):
            file_path_to_remove = os.path.join(current_dir, f)
            if os.path.isfile(file_path_to_remove):
                os.unlink(file_path_to_remove)
    else:
        os.makedirs(current_dir)

    # Copy the contents of the latest directory to the current directory
    for f in os.listdir(latest_dir):
        latest_file_path = os.path.join(latest_dir, f)
        current_file_path = os.path.join(current_dir, f)
        if os.path.isfile(latest_file_path):
            shutil.copyfile(latest_file_path, current_file_path)

    return jsonify({"message": "Current folder updated successfully"}), 200

@app.route('/apk/<path:filename>', methods=['GET'])
def download_apk(filename):
    """Endpoint to download an APK file."""
    return send_from_directory('/var/www/ota_update_server/apk', filename)

@app.route('/api/download-latest-apk', methods=['GET'])
def download_latest_apk():
    """
    Endpoint to download the latest APK file from the /latest directory.
    """
    latest_version, latest_apk_name = get_latest_apk_version()
    if latest_apk_name:
        try:
            return send_from_directory(
                directory=os.path.join(app.static_folder, 'latest'),
                filename=latest_apk_name,
                as_attachment=True
            )
        except Exception as e:
            return jsonify({"error": f"Failed to download the APK: {str(e)}"}), 500
    else:
        return jsonify({"error": "No APK found in the latest directory"}), 404


@app.route('/api/upload-apk', methods=['POST'])
def upload_apk():
    """Endpoint to upload a new APK and update the latest version."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

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

    # Save the uploaded APK to the latest directory with the versioned filename
    latest_apk_path = os.path.join(latest_dir, versioned_filename)
    shutil.copyfile(file_path, latest_apk_path)

    # Update the version information
    version_info['version'] = version
    version_info['url'] = f"http://43.226.218.98/apk/latest/{versioned_filename}"
    version_info['release_notes'] = request.form.get('release_notes', 'No release notes provided')

    # Save the updated version info to the file
    with open(version_info_file, 'w') as f:
        json.dump(version_info, f)

    return jsonify({"message": "APK uploaded and version information updated successfully"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
