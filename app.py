from flask import Flask, request, jsonify, send_from_directory
import os
import shutil
import json

app = Flask(__name__, static_url_path='/apk', static_folder='/var/www/ota_update_server/apk')

version_info_file = '/var/www/ota_update_server/version_info.json'

def get_latest_apk_version():
    latest_dir = os.path.join(app.static_folder, 'latest')
    if os.path.exists(latest_dir) and os.listdir(latest_dir):
        apk_files = [f for f in os.listdir(latest_dir) if os.path.isfile(os.path.join(latest_dir, f))]
        if apk_files:
            latest_apk = apk_files[0]
            version = latest_apk.split('-v')[-1].split('.apk')[0]
            return version, latest_apk
    return None, None

def update_version_info():
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

version_info = update_version_info()

@app.route('/api/latest-version', methods=['GET'])
def get_latest_version():
    if version_info:
        return jsonify(version_info)
    else:
        return jsonify({"error": "No version information available"}), 404
    
@app.route('/api/download-latest-apk', methods=['GET'])
def download_latest_apk():
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
    """Endpoint to get the current version information for a specific aid."""
    current_dir = os.path.join(app.static_folder, 'current', aid)
    if os.path.exists(current_dir) and os.listdir(current_dir):
        apk_files = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]
        if apk_files:
            current_apk = apk_files[0]
            version = current_apk.split('-v')[-1].split('.apk')[0]
            current_version_info = {
                "version": version,
                "url": f"http://43.226.218.98/apk/current/{aid}/{current_apk}",
                "release_notes": "Auto detected current version for the device."
            }
            return jsonify(current_version_info)
    return jsonify({
        "version": "1.0.0",
        "url": f"http://43.226.218.98/apk/current/{aid}/app-v1.0.0.apk",
        "release_notes": "Initial release for the device."
    })

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

# Other existing routes remain unchanged...

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
