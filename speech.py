"""On-device MMS speech synthesis for translated English and Bengali."""
import json
from pathlib import Path
import re
import threading

MODELS = {"en-bn": "facebook/mms-tts-ben", "bn-en": "facebook/mms-tts-eng"}


class Speech:
    def __init__(self):
        self.loaded = {}
        self.lock = threading.Lock()

    def synthesize(self, text, direction):
        import numpy as np
        import torch
        from transformers import AutoTokenizer, VitsModel

        if direction not in MODELS:
            raise ValueError("Translate a sentence before listening.")
        text = text.strip()
        if not text:
            raise ValueError("Translate a sentence before listening.")
        if len(text) > 1500:
            raise ValueError("For audio, translate a shorter passage (up to 1,500 translated characters).")
        # Keep synthesis segments short without silently dropping text.
        chunks = []
        for sentence in re.split(r"(?<=[.!?।])\s*|\n+", text):
            chunk = ""
            for word in sentence.split():
                if len(word) > 240:
                    raise ValueError("A word is too long to read aloud.")
                if len(chunk) + len(word) + 1 > 240:
                    chunks.append(chunk)
                    chunk = ""
                chunk = (chunk + " " + word).strip()
            if chunk:
                chunks.append(chunk)
        if not chunks:
            raise ValueError("No readable text found.")

        with self.lock:
            model_id = MODELS[direction]
            if model_id not in self.loaded:
                lock_path = Path(__file__).resolve().parent / "speech.lock.json"
                if not lock_path.exists():
                    raise ValueError("Speech models are missing. Run 'python main.py download-speech'.")
                revision = json.loads(lock_path.read_text())[model_id]
                options = dict(revision=revision, local_files_only=True)
                tokenizer = AutoTokenizer.from_pretrained(model_id, **options)
                # These small voice models use the CPU, leaving GPU memory for translation.
                model = VitsModel.from_pretrained(model_id, **options, use_safetensors=True).eval()
                self.loaded[model_id] = (tokenizer, model)
            tokenizer, model = self.loaded[model_id]
            rate = model.config.sampling_rate
            pieces = []
            for chunk in chunks:
                inputs = tokenizer(chunk, return_tensors="pt")
                if inputs["input_ids"].numel() < 2:
                    raise ValueError("This passage contains no text supported by the selected voice.")
                with torch.inference_mode():
                    wave = model(**inputs).waveform[0].cpu().numpy().astype(np.float32)
                if not wave.size or not np.isfinite(wave).all():
                    raise RuntimeError("Speech generation produced invalid audio. Try a shorter sentence.")
                if pieces:
                    pieces.append(np.zeros(int(rate * 0.2), dtype=np.float32))
                pieces.append(wave)
            return rate, np.clip(np.concatenate(pieces), -1, 1)


def download_speech():
    from huggingface_hub import HfApi, snapshot_download
    path = Path(__file__).resolve().parent / "speech.lock.json"
    revisions = json.loads(path.read_text()) if path.exists() else {}
    for model in MODELS.values():
        revision = revisions.get(model) or HfApi().model_info(model).sha
        snapshot_download(model, revision=revision, allow_patterns=["*.json", "*.safetensors"])
        revisions[model] = revision
    path.write_text(json.dumps(revisions, indent=2) + "\n")
    print("Bengali and English speech models ready.")
