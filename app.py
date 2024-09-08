from flask import Flask, request, jsonify, send_from_directory
import os
import shutil
import json
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__, static_url_path='/apk', static_folder='/var/www/ota_update_server/apk')

# Path to the version info file
version_info_file = '/var/www/ota_update_server/version_info.json'

# Configure logging
log_directory = '/var/log/flask_app'
os.makedirs(log_directory, exist_ok=True)  # Ensure the log directory exists

log_file = os.path.join(log_directory, 'app.log')
handler = RotatingFileHandler(log_file, maxBytes=100000, backupCount=3)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
handler.setLevel(logging.DEBUG)

# Add handler to Flask's logger
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)

def get_latest_apk_version():
    """Function to retrieve the latest APK version from the 'latest' directory."""
    latest_dir = os.path.join(app.static_folder, 'latest')
    if os.path.exists(latest_dir) and os.listdir(latest_dir):
        apk_files = [f for f in os.listdir(latest_dir) if os.path.isfile(os.path.join(latest_dir, f))]
        if apk_files:
            latest_apk = apk_files[0]
            version = latest_apk.split('-v')[-1].split('.apk')[0]  # Extract version from filename
            return version, latest_apk
    return None, None

def update_version_info():
    """Update the version info by detecting the latest APK on the server."""
    latest_version, latest_apk_name = get_latest_apk_version()
    if latest_version:
        version_info = {
            "version": latest_version,
            "url": f"http://43.226.218.98/apk/latest/{latest_apk_name}",
            "release_notes": "Auto detected version on server start."
        }
        with open(version_info_file, 'w') as f:
            json.dump(version_info, f)
    else:
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

# Ensure version info is updated on server startup
version_info = update_version_info()

@app.route('/api/latest-version', methods=['GET'])
def get_latest_version():
    """Endpoint to get the latest version information."""
    if version_info:
        return jsonify(version_info)
    else:
        return jsonify({"error": "No version information available"}), 404

@app.route('/apk/<path:filename>', methods=['GET'])
def download_apk(filename):
    """Endpoint to download an APK file."""
    return send_from_directory('/var/www/ota_update_server/apk', filename)

@app.route('/api/download-latest-apk', methods=['GET'])
def download_latest_apk():
    """Endpoint to download the latest APK from the 'latest' directory."""
    latest_version, latest_apk_name = get_latest_apk_version()
    if latest_apk_name:
        try:
            directory_path = os.path.join(app.static_folder, 'latest')
            response = send_from_directory(directory_path, latest_apk_name, as_attachment=True)
            response.headers["Content-Disposition"] = f"attachment; filename={latest_apk_name}"
            return response
        except Exception as e:
            return jsonify({"error": f"Error while serving the file: {str(e)}"}), 500
    else:
        return jsonify({"error": "No APK found in the latest directory"}), 404

@app.route('/api/current-version/<uuid>', methods=['GET'])
def get_current_version_for_uuid(uuid):
    """Endpoint to get the current version information for a specific uuid."""
    current_dir = os.path.join(app.static_folder, 'current', uuid)
    latest_dir = os.path.join(app.static_folder, 'latest')

    # Log the path being checked
    print(f"Checking for APK in directory: {current_dir}")

    # Check if the 'current' directory exists and has files
    if os.path.exists(current_dir) and os.listdir(current_dir):
        print(f"Directory exists: {current_dir}")
        apk_files = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]

        # Log the found APK files
        print(f"APK files found: {apk_files}")

        # Ensure at least one APK is available in the current directory
        if apk_files:
            current_apk = apk_files[0]  # Assuming only one APK per device
            version = current_apk.split('-v')[-1].split('.apk')[0]  # Extract version from APK filename
            
            # Log the detected version
            print(f"Detected APK: {current_apk}, Version: {version}")
            
            # Return version information for the specific 'uuid'
            current_version_info = {
                "version": version,
                "url": f"http://43.226.218.98/apk/current/{uuid}/{current_apk}",
                "release_notes": "Auto detected current version for the device."
            }
            return jsonify(current_version_info)
        else:
            print(f"No APK found in directory: {current_dir}")
            return jsonify({"error": "No APK found for the current device."}), 404
    else:
        # If directory does not exist, create it and copy APK from latest
        print(f"Directory not found: {current_dir}. Creating new directory and copying latest APK.")

        # Create the current uuid directory
        os.makedirs(current_dir, exist_ok=True)

        # Copy the APK from the 'latest' directory
        latest_apk_files = [f for f in os.listdir(latest_dir) if os.path.isfile(os.path.join(latest_dir, f))]
        if latest_apk_files:
            latest_apk = latest_apk_files[0]  # Assume there's only one latest APK in 'latest'
            shutil.copyfile(os.path.join(latest_dir, latest_apk), os.path.join(current_dir, latest_apk))
            
            # Extract the version from the copied APK
            version = latest_apk.split('-v')[-1].split('.apk')[0]
            
            # Log the action and return the version information
            print(f"Copied {latest_apk} to {current_dir}. Detected version: {version}")
            current_version_info = {
                "version": version,
                "url": f"http://43.226.218.98/apk/current/{uuid}/{latest_apk}",
                "release_notes": "Auto detected current version for the device."
            }
            return jsonify(current_version_info)
        else:
            print(f"No APK found in latest directory.")
            return jsonify({"error": "No APK found to copy."}), 404

@app.route('/api/update-current-folder/<uuid>', methods=['POST'])
def update_current_folder_for_uuid(uuid):
    """Endpoint to update the 'current' folder for a specific uuid with the contents of the 'latest' folder."""
    current_dir = os.path.join(app.static_folder, 'current', uuid)
    latest_dir = os.path.join(app.static_folder, 'latest')

    # Clean the current directory (delete all existing files)
    if os.path.exists(current_dir):
        for f in os.listdir(current_dir):
            file_path_to_remove = os.path.join(current_dir, f)
            if os.path.isfile(file_path_to_remove):
                os.unlink(file_path_to_remove)
    else:
        os.makedirs(current_dir)

    # Copy the contents of the latest directory to the current directory for this specific uuid
    for f in os.listdir(latest_dir):
        latest_file_path = os.path.join(latest_dir, f)
        current_file_path = os.path.join(current_dir, f)
        if os.path.isfile(latest_file_path):
            shutil.copyfile(latest_file_path, current_file_path)

    return jsonify({"message": f"Current folder updated successfully for uuid: {uuid}"}), 200

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
    app.run(host='0.0.0.0', port=5000, debug=True)
