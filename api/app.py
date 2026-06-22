import sys
import json
from pathlib import Path
from flask import Flask, request, jsonify


BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from db.database import SessionLocal, User, Upload

app = Flask(__name__)

UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"
UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    email = request.form.get("email")
    with SessionLocal() as db:
        user = None
        if email:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(email=email)
                db.add(user)
                db.flush()
        new_upload = Upload(filename=file.filename, user_id=user.id if user else None)
       
        db.add(new_upload)
        db.flush()
        file.save(new_upload.get_upload_path())
        uid_to_return = new_upload.uid
        db.commit() 
    return jsonify({"uid": uid_to_return}), 200


@app.route("/status", methods=["GET"])
@app.route("/status/<uid>", methods=["GET"])
def get_status(uid=None):
    if not uid:
        uid = request.args.get("uid")
    email = request.args.get("email")
    filename = request.args.get("filename")
    with SessionLocal() as db:
        upload_record = None
        if uid:
            upload_record = db.query(Upload).filter(Upload.uid == uid).first()
        elif email and filename:
            upload_record = db.query(Upload).join(User).filter(
                User.email == email, 
                Upload.filename == filename
            ).order_by(Upload.upload_time.desc()).first() 
        else:
            return jsonify({"error": "Provide either UID, or email and filename"}), 400
        if not upload_record:
            return jsonify({"status": "not found", "error": "Upload not found"}), 404
        response_data = {
            "uid": upload_record.uid,
            "status": upload_record.status,
            "filename": upload_record.filename,
            "upload_time": upload_record.upload_time.isoformat(),
            "finish_time": upload_record.finish_time.isoformat() if upload_record.finish_time else None,
            "error_message": upload_record.error_message
        }
        if upload_record.status == "done" and upload_record.get_output_path().exists():
            try:
                response_data["explanation"] = json.loads(upload_record.get_output_path().read_text(encoding="utf-8"))
            except Exception:
                response_data["explanation"] = None
        else:
            response_data["explanation"] = None
    return jsonify(response_data), 200

if __name__ == "__main__":
    app.run(port=5000, debug=True)