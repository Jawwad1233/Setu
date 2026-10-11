"""Development sweep of every supplied glossary example plus literal controls."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent

CONTROLS = [
    ("addy_question", "whats the addy", "address"),
    ("addy_question_punct", "What's the addy?", "address"),
    ("addy_request", "Can you send me your addy?", "address"),
    ("addy_location", "Drop the addy and I'll come over.", "address"),
    ("addy_name", "Her name is Addy.", None),
    ("fire_literal", "The building is on fire.", None),
    ("tea_literal", "Pour the tea.", None),
    ("tea_spill_literal", "She spilled the tea on the floor.", None),
    ("cooked_literal", "The chicken is cooked.", None),
    ("cook_literal", "I cooked dinner.", None),
    ("goat_literal", "The goat ate grass.", None),
    ("rn_literal", "My nurse is an RN.", None),
    ("cap_literal", "The bottle has no cap.", None),
    ("salty_literal", "The soup is too salty.", None),
    ("ship_literal", "The ship docked at the port.", None),
    ("dead_literal", "The plant is dead.", None),
    ("sick_literal", "I feel sick and have a fever.", None),
    ("lit_literal", "She lit the candle.", None),
    ("read_literal", "I read a book yesterday.", None),
    ("plug_literal", "The electrical plug is broken.", None),
    ("thirsty_literal", "I am thirsty. Please give me water.", None),
    ("cake_literal", "We baked a chocolate cake.", None),
    ("fit_literal", "These shoes fit me.", None),
    ("bet_literal", "He placed a bet on the race.", None),
    ("ghost_literal", "The ghost in the story frightened me.", None),
    ("cooked_variant", "I'm cooked for tomorrow's exam.", "trouble"),
    ("fire_variant", "This biryani is fire.", "excellent|amazing|good|delicious"),
    ("negation", "That song doesn't slap.", "not|n't"),
    ("ambiguous_number", "6-7", "uncertain"),
    ("ambiguous_number_41", "41", "uncertain"),
    ("ambiguous_term", "Jittleyang!", "uncertain"),
]


def cases():
    entries = json.loads((ROOT / "slang_glossary.json").read_text())["entries"]
    result = []
    for e in entries:
        text = " ".join(e["examples"]).strip()
        if not text:
            text = "My brother watches Skibidi Toilet." if e["term"] == "Skibidi Toilet" else f'What does "{e["term"]}" mean?'
        result.append({"id": e["id"], "term": e["term"], "source": text,
                       "origin": "provided example" if e["examples"] else "new example", "expected": "review"})
    result += [{"id": "control_" + key, "term": key, "source": text, "origin": "contrast control", "expected": expected}
               for key, text, expected in CONTROLS]
    return result


def normalize(out):
    from slang_context_worker import Interpreter
    from slang_context import payload_for
    interpreter = Interpreter()
    done = {r["id"] for r in map(json.loads, out.read_text().splitlines())} if out.exists() else set()
    all_cases = cases()
    with out.open("a") as f:
        for i, row in enumerate(all_cases, 1):
            if row["id"] in done:
                continue
            payload = payload_for(row["source"])
            # Do not inject the target entry when detection misses it: test the actual runtime retrieval.
            before = time.monotonic()
            row["context"] = interpreter.interpret(row["source"], payload["entries"])
            row["seconds"] = round(time.monotonic() - before, 2)
            f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
            if i % 10 == 0 or i == len(all_cases):
                print(f"Interpreted {i}/{len(all_cases)}", flush=True)


def translate(source, target):
    from gradio_client import Client
    client = Client("http://127.0.0.1:7860", verbose=False)
    params = client.view_api(return_format="dict", print_info=False)["named_endpoints"]["/run"]["parameters"]
    all_rows = [json.loads(line) for line in source.read_text().splitlines()]
    done = {r["id"] for r in map(json.loads, target.read_text().splitlines())} if target.exists() else set()
    rows = [r for r in all_rows if r["id"] not in done]
    with target.open("a") as f:
        for i in range(0, len(rows), 1):
            batch = rows[i:i+1]
            values = {"text": "\n".join(r["context"]["text"] for r in batch), "direction": "en-bn",
                      "beams": 5, "limit": 256, "slang_enabled": False, "clarification": "", "slang_mode": "Context"}
            result = client.predict(*[values[p["parameter_name"]] for p in params], api_name="/run")
            lines = result[0].splitlines()
            if len(lines) != len(batch):
                raise RuntimeError("Translation lines did not align; resume after checking batch.")
            stats = json.loads(result[1])
            for row, translated in zip(batch, lines, strict=True):
                row["translation"] = translated
                row["translation_stats"] = stats
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()
            print(f"Translated {min(i+1,len(rows))}/{len(rows)} pending cases", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["normalize", "translate"])
    parser.add_argument("--directory", type=Path, default=ROOT / "results" / "full-glossary")
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    if args.phase == "normalize":
        normalize(args.directory / "interpretations.jsonl")
    else:
        translate(args.directory / "interpretations.jsonl", args.directory / "translations.jsonl")
