from __future__ import annotations
import os
import uuid
import json
import glob
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def parse_file_info(filename,suffix):
    parts = filename.split("_")
    if len(parts) < 3:
        return filename, "", ""
    uid = parts[-1]
    timestamp = parts[-2]
    orig_filename = "_".join(parts[:-2]) + suffix
    return orig_filename, timestamp, uid


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    uid = str(uuid.uuid4())
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    orig_path = Path(file.filename)
    new_filename = f"{orig_path.stem}_{timestamp}_{uid}{orig_path.suffix}"
    file.save(UPLOAD_FOLDER / new_filename)

    return jsonify({"uid": uid}), 200


@app.route("/status/<uid>", methods=["GET"])
@app.route("/status", methods=["GET"]) 
def get_status(uid=None):
    if not uid:
        uid = request.args.get("uid")
    if not uid:
        return jsonify({"status": "not found", "error": "Missing UID"}), 404
    out_matches = glob.glob(str(OUTPUT_FOLDER / f"*_{uid}.json"))
    if out_matches:
        out_path = Path(out_matches[0])
        orig_filename, timestamp, _ = parse_file_info(out_path.stem, ".pptx")
        try:
            explanation_data = json.loads(out_path.read_text(encoding="utf-8"))
        except Exception:
            explanation_data = None
        return jsonify({
            "status": "done",
            "filename": orig_filename,
            "timestamp": timestamp,
            "explanation": explanation_data
        }), 200
        
    up_matches = glob.glob(str(UPLOAD_FOLDER / f"*_{uid}.pptx"))
    if up_matches:
        up_path = Path(up_matches[0])
        orig_filename, timestamp, _ = parse_file_info(up_path.stem, up_path.suffix)
        return jsonify({
            "status": "pending",
            "filename": orig_filename,
            "timestamp": timestamp,
            "explanation": None
        }), 200
        
    return jsonify({
        "status": "not found",
        "filename": None,
        "timestamp": None,
        "explanation": None
    }), 404


if __name__ == "__main__":
    app.run(port=5000, debug=True)
