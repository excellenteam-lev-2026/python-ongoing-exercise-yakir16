from pptx import Presentation
import os
import time
import json
import pytest
import subprocess
import sys
import shutil
from pathlib import Path
from client import GeminiExplainerClient

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"

@pytest.fixture(scope="module")
def run_server_and_explainer():
    api_script = BASE_DIR / "api" / "app.py"
    api_process = subprocess.Popen([sys.executable, str(api_script)])
    explainer_script = BASE_DIR / "explainer" / "explainer.py"
    env = os.environ.copy()
    if "GEMINI_API_KEY" not in env:
        pytest.fail("GEMINI_API_KEY environment variable is missing! Required for End-to-End test.")
    explainer_process = subprocess.Popen([sys.executable, str(explainer_script)], env=env)
    time.sleep(3)
    yield
    api_process.terminate()
    explainer_process.terminate()
    api_process.wait()
    explainer_process.wait()

@pytest.fixture
def sample_pptx(tmp_path):
    repo_demo_pptx = BASE_DIR / "demo.pptx"
    assert repo_demo_pptx.exists(), "The file 'demo.pptx' must exist in the root repository."
    demo_pptx = tmp_path / "demo.pptx"
    shutil.copy(repo_demo_pptx, demo_pptx)
    return demo_pptx

@pytest.fixture
def client():
    return GeminiExplainerClient("http://127.0.0.1:5000")

def test_upload_method_returns_valid_uid(run_server_and_explainer, client, sample_pptx):
    uid = client.upload(sample_pptx)
    assert isinstance(uid, str) and len(uid) > 0, "Upload did not return a valid UID string."
    for f in UPLOADS_DIR.glob(f"*_{uid}.pptx"):
        f.unlink(missing_ok=True)

def test_upload_creates_file_with_timestamp_and_uid_in_filename(run_server_and_explainer, client, sample_pptx):
    uid = client.upload(sample_pptx)
    uploaded_files = list(UPLOADS_DIR.glob(f"*_{uid}.pptx"))
    assert len(uploaded_files) == 1, f"Expected exactly 1 file in uploads folder matching pattern *_ {uid}.pptx"    
    filename = uploaded_files[0].name
    assert uid in filename, "The uploaded filename does not contain the generated UID."
    for f in uploaded_files:
        f.unlink(missing_ok=True)

def test_status_returns_pending_immediately_after_upload(run_server_and_explainer, client, sample_pptx):
    uid = client.upload(sample_pptx)
    status_obj = client.status(uid)
    assert status_obj.status in ["pending", "done"], f"Initial status should be 'pending' or 'done', got '{status_obj.status}'"
    for f in UPLOADS_DIR.glob(f"*_{uid}.pptx"):
        f.unlink(missing_ok=True)


def test_client_raises_error_when_uid_not_found(run_server_and_explainer, client):
    with pytest.raises(Exception):
        client.status("non-existent-uid-fake-12345")

def test_explainer_only_processes_new_files(run_server_and_explainer):
    fake_uid = "already-processed-uid-12345"
    fake_timestamp = "20260101120000"
    fake_output_path = OUTPUTS_DIR / f"testfile_{fake_timestamp}_{fake_uid}.json"
    dummy_data = [{"slide_number": 1, "text": "dummy", "explanation": "this should not change"}]
    OUTPUTS_DIR.mkdir(exist_ok=True)
    fake_output_path.write_text(json.dumps(dummy_data), encoding="utf-8")
    fake_upload_path = UPLOADS_DIR / f"testfile_{fake_timestamp}_{fake_uid}.pptx"
    UPLOADS_DIR.mkdir(exist_ok=True)
    fake_upload_path.write_text("fake pptx content")
    time.sleep(3)
    assert fake_output_path.exists(), "The output file was unexpectedly deleted!"
    current_content = json.loads(fake_output_path.read_text(encoding="utf-8"))
    assert current_content == dummy_data, "The Explainer re-processed or modified an already existing output file!"
    fake_output_path.unlink(missing_ok=True)
    fake_upload_path.unlink(missing_ok=True)

def test_system_pipeline_processes_end_to_end_successfully(run_server_and_explainer, client, sample_pptx):
    prs = Presentation(str(sample_pptx))
    num_slides = len(prs.slides)
    dynamic_timeout = 60 + (num_slides * 15)
    print(f"\n[Test Info] Detected {num_slides} slides. Setting dynamic timeout to {dynamic_timeout} seconds.")
    uid = client.upload(sample_pptx)
    is_processed = False
    status_obj = None
    for _ in range(dynamic_timeout):
        status_obj = client.status(uid)
        if status_obj.is_done():
            is_processed = True
            break
        time.sleep(1)
        
    assert is_processed, f"The Explainer did not process the file within the {dynamic_timeout}-second timeout."
    data = status_obj.explanation
    assert isinstance(data, list), "Explanation data should be a list representing the slides."
    assert len(data) > 0, "No slides explanations were found in the response."
    first_slide = data[0]
    assert "slide_number" in first_slide, "Missing 'slide_number' key in explanation data."
    assert "text" in first_slide, "Missing 'text' key in explanation data."
    assert "explanation" in first_slide, "Missing 'explanation' key in explanation data."
    assert first_slide.get("error") is None, f"Encountered internal processing error: {first_slide.get('error')}"
    actual_explanation = first_slide["explanation"]
    assert isinstance(actual_explanation, str), "The explanation field is not a string."
    assert len(actual_explanation) > 10, f"The explanation returned from Gemini is unexpectedly short: '{actual_explanation}'"