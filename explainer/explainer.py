import os
import re
import sys
import time
import json
import glob
import asyncio
import functools
import requests
from pathlib import Path
from pptx import Presentation

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
DEFAULT_CONCURRENCY = max(1, int(os.getenv("GEMINI_CONCURRENCY", "4")))
DEFAULT_MAX_RETRIES = max(1, int(os.getenv("GEMINI_MAX_RETRIES", "4")))
DEFAULT_BACKOFF_SECONDS = float(os.getenv("GEMINI_BACKOFF_SECONDS", "1.0"))
SLEEP_INTERVAL = 10  

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_FOLDER = BASE_DIR / "uploads"
OUTPUT_FOLDER = BASE_DIR / "outputs"

UPLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)


def clean_text(text: str):
    if not text:
        return ""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_slide_text(slide):
    parts = []
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False):
            raw = getattr(shape, "text", "")
            cleaned = clean_text(raw)
            if cleaned:
                parts.append(cleaned)
    return "\n".join(parts).strip()


def extract_slides_from_pptx(pptx_path):
    prs = Presentation(str(pptx_path))
    slides = []
    for i, slide in enumerate(prs.slides, start=1):
        text = extract_slide_text(slide)
        if not text:
            continue
        slides.append({"slide_number": i, "text": text})
    return slides


def build_prompt(slide_number,slide_text):
    return f"Explain this slide simply for a beginner software developer:\n\nSlide {slide_number}:\n{slide_text}".strip()


class GeminiExplainer:
    def __init__(self, model_name: str = DEFAULT_MODEL):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing GEMINI_API_KEY")
        self.model_name = model_name
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

    async def explain_slide(self,slide_number,slide_text):
        prompt = build_prompt(slide_number, slide_text)
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        headers = {"Content-Type": "application/json"}

        loop = asyncio.get_running_loop()
        func = functools.partial(requests.post, self.url, json=payload, headers=headers)
        response = await loop.run_in_executor(None, func)
        response.raise_for_status()
        
        response_data = response.json()
        return response_data['candidates'][0]['content']['parts'][0]['text']


async def explain_with_retry(explainer, slide, max_retries, backoff_seconds):
    slide_number = slide["slide_number"]
    slide_text = slide["text"]
    last_error = ""
    for attempt in range(max_retries):
        try:
            explanation = await explainer.explain_slide(slide_number, slide_text)
            return {
                "slide_number": slide_number,
                "text": slide_text,
                "explanation": explanation,
                "error": None
            }
        except Exception as e:
            last_error = str(e)
            if attempt == max_retries - 1:
                return {
                    "slide_number": slide_number,
                    "text": slide_text,
                    "explanation": "",
                    "error": last_error
                }
            
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                sleep_time = 30 * (attempt + 1)
                print(f"[{time.strftime('%X')}] Rate limit (429) hit on slide {slide_number}. Sleeping for {sleep_time}s...")
                await asyncio.sleep(sleep_time)
            else:
                await asyncio.sleep(backoff_seconds * (2 ** attempt))


async def process_presentation(pptx_path, explainer):
    slides = extract_slides_from_pptx(pptx_path)
    semaphore = asyncio.Semaphore(DEFAULT_CONCURRENCY)
    async def worker(slide):
        async with semaphore:
            return await explain_with_retry(
                explainer,
                slide,
                DEFAULT_MAX_RETRIES,
                DEFAULT_BACKOFF_SECONDS
            )
    return await asyncio.gather(*(worker(s) for s in slides))


async def main_loop():
    print(f"[{time.strftime('%X')}] Explainer started in API mode. Monitoring uploads...")
    explainer = GeminiExplainer()

    while True:
        try:
            pptx_files = glob.glob(str(UPLOAD_FOLDER / "*.pptx"))
            for file_path_str in pptx_files:
                file_path = Path(file_path_str)
                output_json_path = OUTPUT_FOLDER / f"{file_path.stem}.json"
                
                if not output_json_path.exists():
                    print(f"[{time.strftime('%X')}] DEBUG START: Processing new file: {file_path.name}")
                    
                    results = await process_presentation(file_path, explainer)
                    output_json_path.write_text(
                        json.dumps(results, ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )
                    
                    print(f"[{time.strftime('%X')}] DEBUG END: Finished processing. Saved to: {output_json_path.name}")
                    
                    try:
                        file_path.unlink()
                        print(f"[{time.strftime('%X')}] DEBUG CLEANUP: Successfully deleted processed file: {file_path.name}")
                    except Exception as delete_error:
                        print(f"Warning: Could not delete original file {file_path.name}: {delete_error}", file=sys.stderr)
                    
        except Exception as e:
            print(f"Error in main loop: {e}", file=sys.stderr)
            
        await asyncio.sleep(SLEEP_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main_loop())