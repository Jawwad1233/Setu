"""Bridge to the isolated Apple Silicon context interpreter."""
import json
import os
from pathlib import Path
import subprocess
import threading

ROOT = Path(__file__).resolve().parent
LOCK = threading.Lock()


def ready():
    return (ROOT / "context.lock.json").exists() and (ROOT / ".slang-venv/bin/python").exists()


def payload_for(text):
    from slang import detect_glossary, glossary_entries
    hits = detect_glossary(text)
    if any(e["term"] == "Twizzy" for e in hits) and not any(e["term"] == "Twin" for e in hits):
        hits.extend(e for e in glossary_entries() if e["term"] == "Twin")
    from bilingual import guidance
    # Curated examples are retrieval context, not held-out evaluation data.
    return {"text": text, "examples": guidance(text), "entries": [{"term": e["term"], "meaning": e["definition"]} for e in hits]}


def download_context():
    from huggingface_hub import HfApi, snapshot_download
    path = ROOT / "context.lock.json"
    lock = json.loads(path.read_text()) if path.exists() else {"model": "mlx-community/Qwen3-4B-Instruct-2507-4bit"}
    lock["revision"] = lock.get("revision") or HfApi().model_info(lock["model"]).sha
    snapshot_download(lock["model"], revision=lock["revision"],
                      allow_patterns=["*.json", "*.safetensors", "*.jinja", "*.txt"])
    path.write_text(json.dumps(lock, indent=2) + "\n")
    print("Local context model downloaded. Runtime dependencies are in requirements-context.lock.txt.")


def call_worker(payloads):
    if not ready():
        raise RuntimeError("Local slang interpreter is not installed; select Quick phrase rules in Settings.")
    with LOCK:
        env = dict(os.environ, HF_HUB_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
        run = subprocess.run([str(ROOT / ".slang-venv/bin/python"), str(ROOT / "slang_context_worker.py")],
                             input=json.dumps(payloads, ensure_ascii=False) + "\n",
                             capture_output=True, text=True, env=env,
                             timeout=max(90, 30 * len(payloads)), cwd=ROOT)
        if run.returncode:
            raise RuntimeError("The local slang interpreter could not run. Try Quick phrase rules in Settings.")
        try:
            results = json.loads(run.stdout.strip().splitlines()[-1])
            if not isinstance(results, list) or len(results) != len(payloads):
                raise ValueError("Invalid response")
            return results
        except (ValueError, IndexError):
            raise RuntimeError("The local slang interpreter returned an invalid response; no rewrite applied.") from None


def interpret_many(sentences):
    return call_worker([payload_for(s) for s in sentences])


def prepare_context(sentences, line_numbers=None):
    results = interpret_many(sentences)
    notes = []
    numbers = line_numbers if line_numbers is not None else range(1, len(results)+1)
    for i, result in zip(numbers, results, strict=True):
        notes.append(f'Line {i}: {result["status"]} — {result["reason"]}')
        if result["status"] == "rewritten":
            notes.append('Meaning translated: ' + result["text"])
        if result.get("possible_unexpanded_terms"):
            notes.append('Check these terms before trusting the translation: ' +
                         ", ".join(result["possible_unexpanded_terms"]))
    return [r["text"] for r in results], "\n".join(notes)
