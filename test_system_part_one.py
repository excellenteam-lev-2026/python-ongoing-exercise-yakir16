from __future__ import annotations
import json
import os
import subprocess
import sys
import shutil
from pathlib import Path
import pytest

def test_system_pipeline_creates_json(tmp_path):
    repo_demo_pptx = Path("demo.pptx").resolve()
    script_path = Path("gemini_request.py").resolve()
    assert repo_demo_pptx.exists(), "The file 'demo.pptx' must exist in the root repository."
    assert script_path.exists(), "The script 'gemini_request.py' must exist."
    shutil.copy(repo_demo_pptx, tmp_path / "demo.pptx")
    shutil.copy(script_path, tmp_path / "gemini_request.py")
    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        result = subprocess.run(
            [sys.executable, "gemini_request.py", "demo.pptx"],
            capture_output=True,
            text=True,
            env=os.environ
        )
        assert result.returncode == 0, f"Script execution failed.\nStdout: {result.stdout}\nStderr: {result.stderr}"
        output_json = Path("demo.json")
        assert output_json.exists(), "The expected output JSON file 'demo.json' was not created using relative paths."
        data = json.loads(output_json.read_text(encoding="utf-8"))
        assert isinstance(data, list), "Output JSON must be a list."
        assert len(data) > 0, "No slides were processed."
        first_slide = data[0]
        assert "slide_number" in first_slide
        assert "text" in first_slide
        assert "explanation" in first_slide
        assert first_slide["error"] is None
        assert len(first_slide["explanation"].strip()) > 0, "The explanation field returned empty from the live API."
    finally:
        os.chdir(old_cwd)