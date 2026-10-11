"""Curated examples and guarded lexical repairs; these are not trained model weights."""
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parent

def key(text):
    # Do not erase punctuation, negation, numbers, or names to force a match.
    return ' '.join(unicodedata.normalize('NFC', text).replace('’', "'").split())

def memory_entries():
    return json.loads((ROOT / 'translation_memory.json').read_text())['entries']

def recall(text, direction):
    return next((e for e in memory_entries() if e['direction'] == direction and key(e['source']) == key(text)), None)

def bengali_entries():
    return json.loads((ROOT / 'bengali_glossary.json').read_text())['entries']

def detect_bengali(text):
    boundary = r'\w\u0980-\u09ff'
    return [e for e in bengali_entries() if any(re.search(r'(?<!['+boundary+r'])'+re.escape(a)+r'(?!['+boundary+r'])', text, re.I) for a in e['aliases'])]

def guidance(text):
    from slang import detect_glossary
    ids = {e['id'] for e in detect_glossary(text)}
    hints = json.loads((ROOT / 'interpretation_hints.json').read_text())
    return [{'term':e['term'], 'sense_note':hints[e['id']]} for e in detect_glossary(text) if e['id'] in hints]


def repair_translation(source, prepared, translated):
    """Only repair known lexical confusions when the English source establishes the sense."""
    rules = [
        (r'\bwater\s?slide\b', 'জলাবদ্ধতা', 'ওয়াটার স্লাইড'),
        (r'\bwater\s?slide\b', 'জলোচ্ছ্বাস', 'ওয়াটার স্লাইড'),
        (r'\b(?:electrical|electric) plug\b', 'খুঁটি', 'প্লাগ'),
        (r'\bbottle\b.*\b(?:cap|lid)\b', 'বোতলের টুপি', 'বোতলের ঢাকনা'),
        (r'\bdance (?:recital|show)\b', 'আবৃত্তি', 'অনুষ্ঠান'),
        (r'\b(?:texted|texts|text message)\b', 'চিঠি', 'মেসেজ'),
        (r'\b(?:that|the) tackle\b', 'হাতল', 'ট্যাকল'),
    ]
    notes = []
    if re.search(r'\bbottle\b.*\b(?:cap|lid)\b', source+' '+prepared, re.I) and not re.search(r'\b(?:hat|wear|wears|wearing|wore)\b',source,re.I):
        if 'টুপি' in translated:
            translated=translated.replace('টুপি','ঢাকনা');notes.append('Bottle cap: টুপি → ঢাকনা')
    for pattern, wrong, right in rules:
        # Skip ambiguous sentences that explicitly mention both the intended and literal concepts.
        conflicts={'জলাবদ্ধতা':r'\b(?:waterlogging|flood)\b','জলোচ্ছ্বাস':r'\b(?:surge|flood)\b',
                   'খুঁটি':r'\bpole\b','চিঠি':r'\bletter\b','হাতল':r'\bhandle\b','আবৃত্তি':r'\bpoetry\b'}
        if wrong in conflicts and re.search(conflicts[wrong],source,re.I):continue
        if re.search(pattern, source+' '+prepared, re.I) and wrong in translated:
            translated = translated.replace(wrong, right)
            notes.append(wrong+' → '+right)
    return translated, notes
