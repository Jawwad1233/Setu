"""Import the supplied glossary without treating its definitions as verified facts."""
import argparse
import hashlib
import json
from pathlib import Path
import re

SPECIAL = {
    "Boomer/Okay Boomer": ["boomer", "okay boomer", "ok boomer"],
    "Clock/clocking": ["clock", "clocked", "clocking"],
    "Core (Cottagecore, Barbiecore, etc.)": ["cottagecore", "barbiecore"],
    "Dead/Dying/Ded": ["dead", "dying", "ded"],
    "Egirl/Eboy": ["egirl", "eboy", "e-girl", "e-boy"],
    "Slim thick/thicc": ["slim thick", "slim thicc", "thicc"],
    "Slap": ["slap", "slaps"], "Ghost": ["ghost", "ghosted", "ghosting"],
    "Bussin’": ["bussin", "bussin'"], "Tweakin’": ["tweakin", "tweakin'"],
    "Cap": ["cap", "no cap", "capping"], "Dox": ["dox", "doxed", "doxxed", "doxxing"],
    "Slay": ["slay", "slayed", "slaying"], "Yeet": ["yeet", "yeeted"],
    "Glow-up": ["glow-up", "glow up"], "GOAT": ["goat", "goated"],
    "Left on read": ["left on read", "left me on read", "left you on read", "left her on read", "left him on read"],
    "Tea": ["tea", "spill the tea"], "Shade": ["shade", "throw shade", "throwing shade"],
    "Curve": ["curve", "curved", "curving"], "Drag": ["drag", "dragged", "dragging"],
    "Flex": ["flex", "flexing", "flexed"], "Pulling": ["pulling", "pull", "pulled"],
    "Pwn": ["pwn", "pwned", "pwning"], "Swerve": ["swerve", "swerved", "swerving"],
    "Ship": ["ship", "shipped", "shipping"], "Smash": ["smash", "smashed", "smashing"],
    "Stan": ["stan", "stanned", "stanning"],
    "Read": ["read", "reading"], "Ops": ["ops", "opps"],
    "Wig snatched": ["wig snatched", "wig was snatched", "wig is snatched"],
}


def parse(text):
    entries, current = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or re.fullmatch(r"[A-Z](?:-[A-Z])?|Numerical Slang", line):
            continue
        if " – " in line and len(line.split(" – ", 1)[0]) < 70:
            term, definition = line.split(" – ", 1)
            current = {"id": re.sub(r"[^a-z0-9]+", "_", term.lower()).strip("_"),
                       "term": term, "definition": definition.strip(), "examples": [],
                       "aliases": SPECIAL.get(term, [term.replace("’", "'")]),
                       "review_status": "user-supplied; meaning and Bangladeshi translation unverified"}
            entries.append(current)
        elif current:
            current["examples"].append(line)
        else:
            raise ValueError(f"Unassigned source text: {line}")
    if len({e["id"] for e in entries}) != len(entries):
        raise ValueError("Duplicate entry IDs")
    return entries


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    content = args.source.read_bytes()
    entries = parse(content.decode())
    result = {"source": "User-provided English slang glossary", "source_sha256": hashlib.sha256(content).hexdigest(),
              "imported_on": "2026-09-26", "entries": entries}
    Path(__file__).with_name("slang_glossary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"Imported {len(entries)} entries with {sum(len(e['examples']) for e in entries)} example lines.")
