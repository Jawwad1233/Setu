"""Small, explicit phrase rules; this module does not claim general slang understanding."""
import json
from pathlib import Path
import re


def normalize_slang(text, direction):
    rules = json.loads(Path(__file__).with_name("slang_rules.json").read_text())
    candidate = " ".join(text.split())
    matches = []
    for rule in rules:
        if rule["direction"] != direction:
            continue
        # Match a whole utterance, not a keyword elsewhere in an unrelated sentence.
        if rule.get("mode", "fullmatch") == "fullmatch":
            match = re.fullmatch(rule["pattern"], candidate, flags=re.IGNORECASE)
            found = [match] if match else []
        else:
            found = list(re.finditer(rule["pattern"], candidate, flags=re.IGNORECASE))
        for match in found:
            matches.append((match.start(), match.end(), match.expand(rule["replacement"]), rule))
    # Prefer longer phrases, and never rewrite generated replacement text a second time.
    selected = []
    for item in sorted(matches, key=lambda m: (-(m[1] - m[0]), m[0])):
        if not any(item[0] < other[1] and other[0] < item[1] for other in selected):
            selected.append(item)
    if not selected:
        return text, None
    normalized = candidate
    for start, end, replacement, _ in sorted(selected, reverse=True):
        normalized = normalized[:start] + replacement + normalized[end:]
    normalized = " ".join(normalized.split())
    details = [{"rule": rule["id"], "expression": rule["expression"], "meaning": rule["meaning"]}
               for _, _, _, rule in sorted(selected)]
    return normalized, {**details[0], "original": text, "normalized": normalized, "matches": details}


def glossary_entries():
    return json.loads(Path(__file__).with_name("slang_glossary.json").read_text())["entries"]


def detect_glossary(text):
    candidate = text.replace("’", "'")
    hits = []
    for entry in glossary_entries():
        for alias in sorted(entry["aliases"], key=len, reverse=True):
            if re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", candidate, re.IGNORECASE):
                hits.append(entry)
                break
    return hits


def glossary_rows(sentences, direction):
    if direction == "bn-en":
        from bilingual import detect_bengali
        return [[i, e["term"], e["definition"], e["review_status"]]
                for i, sentence in enumerate(sentences, 1) for e in detect_bengali(sentence)]
    return [[i, entry["term"], entry["definition"], "Reference only; context and meaning need review"]
            for i, sentence in enumerate(sentences, 1) for entry in detect_glossary(sentence)]


def prepare_sentences(sentences, direction, enabled, clarification=""):
    if clarification.strip():
        if direction != "en-bn" or not enabled:
            raise ValueError("Clear the English clarification, or enable slang support with English → Bangla.")
        clarified = [line.strip() for line in clarification.splitlines() if line.strip()]
        if len(clarified) != len(sentences):
            raise ValueError("Provide one clarified English sentence for every input line, in the same order.")
        return clarified, "Using your clarified English wording. Check that it preserves the intended meaning."
    prepared, notes = [], []
    for i, sentence in enumerate(sentences, 1):
        normalized, note = normalize_slang(sentence, direction) if enabled else (sentence, None)
        prepared.append(normalized)
        if note:
            senses = "; ".join(f'“{n["expression"]}” → {n["meaning"]}' for n in note["matches"])
            notes.append(f'Line {i}: {senses}. Translated as: {note["normalized"]}')
        if enabled and direction == "en-bn":
            detected = detect_glossary(sentence)
            if detected:
                notes.append(f'Line {i}: glossary candidates: ' + ", ".join(e["term"] for e in detected) +
                             ". Detection alone does not establish slang usage. Review definitions below.")
    if not enabled:
        explanation = "Slang support is off. Translating the original text."
    elif notes:
        explanation = "\n".join(notes)
    else:
        explanation = "No supported slang pattern matched. Translating the original text."
    return prepared, explanation
