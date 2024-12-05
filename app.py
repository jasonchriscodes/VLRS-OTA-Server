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

@app.route('/api/view-registration-guide', methods=['GET'])
def view_registration_guide():
    """Endpoint to view the registration guide PDF."""
    pdf_directory = '/var/www/ota_update_server/pdf'
    pdf_filename = 'how_to_register_device.pdf'

    if os.path.exists(os.path.join(pdf_directory, pdf_filename)):
        try:
            return send_from_directory(pdf_directory, pdf_filename, as_attachment=False)
        except Exception as e:
            app.logger.error(f"Error while serving the PDF: {str(e)}")
            return jsonify({"error": f"Error while serving the file: {str(e)}"}), 500
    else:
        app.logger.error(f"PDF file {pdf_filename} not found in directory {pdf_directory}.")
        return jsonify({"error": "PDF file not found"}), 404


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

@app.route('/api/current-version/<aid>', methods=['GET'])
def get_current_version_for_aid(aid):
    """Endpoint to get the current version information for a specific AID."""
    current_dir = os.path.join(app.static_folder, 'current', aid)
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
            
            # Return version information for the specific 'aid'
            current_version_info = {
                "version": version,
                "url": f"http://43.226.218.98/apk/current/{aid}/{current_apk}",
                "release_notes": "Auto detected current version for the device."
            }
            return jsonify(current_version_info)
        else:
            print(f"No APK found in directory: {current_dir}")
            return jsonify({"error": "No APK found for the current device."}), 404
    else:
        # If directory does not exist, create it and copy APK from latest
        print(f"Directory not found: {current_dir}. Creating new directory and copying latest APK.")

        # Create the current aid directory
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
                "url": f"http://43.226.218.98/apk/current/{aid}/{latest_apk}",
                "release_notes": "Auto detected current version for the device."
            }
            return jsonify(current_version_info)
        else:
            print(f"No APK found in latest directory.")
            return jsonify({"error": "No APK found to copy."}), 404

@app.route('/api/update-current-folder/<aid>', methods=['POST'])
def update_current_folder_for_aid(aid):
    """Endpoint to update the 'current' folder for a specific aid with the contents of the 'latest' folder."""
    current_dir = os.path.join(app.static_folder, 'current', aid)
    latest_dir = os.path.join(app.static_folder, 'latest')

    # Clean the current directory (delete all existing files)
    if os.path.exists(current_dir):
        for f in os.listdir(current_dir):
            file_path_to_remove = os.path.join(current_dir, f)
            if os.path.isfile(file_path_to_remove):
                os.unlink(file_path_to_remove)
    else:
        os.makedirs(current_dir)

    # Copy the contents of the latest directory to the current directory for this specific aid
    for f in os.listdir(latest_dir):
        latest_file_path = os.path.join(latest_dir, f)
        current_file_path = os.path.join(current_dir, f)
        if os.path.isfile(latest_file_path):
            shutil.copyfile(latest_file_path, current_file_path)

    return jsonify({"message": f"Current folder updated successfully for aid: {aid}"}), 200

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

@app.route('/api/upload-config', methods=['POST'])
def upload_config():
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        # Log the received data
        app.logger.debug(f"Received config upload: {json.dumps(data, indent=4)}")

        # Extract required fields
        company_name = data.get("companyName")
        password = data.get("password")
        token_config_data = data.get("tokenConfigData")
        bus_config = data.get("busConfig")

        # Verify all required fields are present
        if not all([company_name, password, token_config_data, bus_config]):
            return jsonify({"error": "Missing required fields"}), 400

        # Prepare the directory and file path
        config_dir = "/var/www/ota_update_server/config"
        os.makedirs(config_dir, exist_ok=True)

        config_file_path = os.path.join(config_dir, f"{token_config_data}.json")

        # Save data to JSON file
        with open(config_file_path, "w") as config_file:
            json.dump({
                "companyName": company_name,
                "password": password,
                "tokenConfigData": token_config_data,
                "busConfig": bus_config
            }, config_file, indent=4)

        return jsonify({"message": "Config file uploaded successfully"}), 200

    except Exception as e:
        app.logger.error(f"Error uploading config: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config-files', methods=['GET'])
def get_config_files():
    """Fetch all config files."""
    config_folder = '/var/www/ota_update_server/config'
    config_files = []

    for filename in os.listdir(config_folder):
        if filename.endswith('.json'):
            with open(os.path.join(config_folder, filename), 'r') as file:
                try:
                    config_data = json.load(file)
                    app.logger.debug(f"Loaded Config Data: {json.dumps(config_data, indent=4)}")
                    config_files.append(config_data)
                except json.JSONDecodeError as e:
                    app.logger.error(f"Error decoding JSON in file {filename}: {e}")

    app.logger.debug(f"Returning config files: {json.dumps(config_files, indent=4)}")
    return jsonify(config_files), 200

@app.route('/api/download-route-generation-apk', methods=['GET'])
def download_route_generation_apk():
    """Endpoint to download the route-generation-release APK from the 'route-generation' folder."""
    apk_directory = '/var/www/ota_update_server/route-generation'
    apk_filename = 'route-generation-release.apk'
    
    if os.path.exists(os.path.join(apk_directory, apk_filename)):
        try:
            response = send_from_directory(apk_directory, apk_filename, as_attachment=True)
            response.headers["Content-Disposition"] = f"attachment; filename={apk_filename}"
            return response
        except Exception as e:
            app.logger.error(f"Error while serving the route-generation APK: {str(e)}")
            return jsonify({"error": f"Error while serving the file: {str(e)}"}), 500
    else:
        app.logger.error("route-generation-release APK not found.")
        return jsonify({"error": "route-generation-release APK not found"}), 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)