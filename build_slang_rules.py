"""Build inspectable context rules. Source glossary entries remain separate."""
import json
from pathlib import Path

rules = []


def add(key, expression, pattern, replacement, meaning, mode="search"):
    rules.append(dict(id=key, direction="en-bn", expression=expression, pattern=pattern,
                      replacement=replacement, meaning=meaning, mode=mode,
                      review_status="development rule; Bangladeshi phrasing needs bilingual review"))


add("music_slaps", "slaps", r"(?P<subject>(?:this|that|the) (?:song|track|beat|album)) (?:really |absolutely )?slaps(?P<ending>[.!]*)",
    r"\g<subject> is really good\g<ending>", "is really good (praise for music)", "fullmatch")

# Clear lexical forms; ordinary homonyms and short ambiguous acronyms are excluded.
for term, plain in {
    "amirite": "am I right", "amped": "excited", "boujee": "luxurious", "bussin": "excellent",
    "cheugy": "outdated", "cray cray": "crazy", "delulu": "unrealistic", "finna": "going to",
    "frfr": "honestly", "ngl": "to be honest", "icymi": "in case you missed it",
    "iykyk": "if you know, you know", "omw": "on my way", "omg": "oh my goodness",
    "oml": "oh my goodness", "periodt": "and that is final", "smh": "I am shaking my head in disapproval",
    "smol": "tiny and cute", "totes": "totally", "stoked": "very excited", "swole": "muscular",
    "sus": "suspicious", "rizz": "romantic charm", "rizzler": "a person who is good at flirting",
    "finsta": "private Instagram account", "fyp": "personalized video feed", "guap": "a lot of money",
    "menty b": "mental breakdown", "highlighter kid": "child wearing neon clothes",
    "sneaky link": "secret romantic relationship", "glow-up": "improvement in appearance",
    "clapback": "witty response to criticism", "big yikes": "that is very embarrassing",
    "caught in 4k": "caught with clear evidence", "high key": "really",
    "on fleek": "perfect", "hella skrilla": "a lot of money",
}.items():
    import re
    pattern = r"(?<!\w)" + re.escape(term) + (r"['’]?" if term == "bussin" else "") + r"(?!\w)"
    add(term.replace(" ", "_").replace("-", "_"), term, pattern, plain, plain)

# Only these grammatical contexts permit common homonyms to be rewritten.
boundary = r"(?<![\w])"
end_clause = r"(?=[.!?,;:]|$)"
add("fire_praise", "fire", boundary + r"(?P<subject>(?:this|that|the|your|his|her) (?:song|album|track|beat|movie|outfit|performance|waterslide|food|pizza|biryani|meal)) (?P<verb>is|was) (?:really |so |absolutely )?fire" + end_clause,
    r"\g<subject> \g<verb> excellent", "excellent, praising entertainment or style")
add("lit_event", "lit", boundary + r"(?P<subject>(?:this|that|the) (?:party|concert|movie|show|event)) (?P<verb>is|was) (?:really |so )?lit" + end_clause,
    r"\g<subject> \g<verb> exciting", "exciting, about an event")
add("mid_review", "mid", boundary + r"(?P<subject>(?:this|that|the) (?:song|movie|show|album|game|food)) (?P<verb>is|was) (?:really |so )?mid" + end_clause,
    r"\g<subject> \g<verb> mediocre", "mediocre, a review")
for verb, gloss in [("spill", "share"), ("spilling", "sharing"), ("spilled", "shared")]:
    add("spill_tea_" + verb, "spill the tea", r"(?<!\w)" + verb + r" the tea (?=about\b)",
        gloss + " the gossip ", "share gossip about someone")
add("spill_tea_request", "spill the tea", r"(?:please )?spill the tea[.!]*",
    "Tell me the gossip.", "request to share gossip", "fullmatch")
add("cooked_person", "cooked", r"(?P<person>I['’]m|I am|we['’]re|we are|you['’]re|you are|he['’]s|he is|she['’]s|she is|they['’]re|they are) (?:so |totally )?cooked(?: (?P<context>for (?:tomorrow['’]s |the |my )?(?:exam|test|interview)))?[.!]*",
    r"\g<person> in serious trouble \g<context>", "in serious trouble; personal statement", "fullmatch")
add("ghosting", "ghosting", r"(?<!\w)(?P<subject>he|she|they|you) (?P<verb>is|are|was|were) ghosting (?P<object>me|him|her|us|them|you)(?!\w)",
    r"\g<subject> \g<verb> ignoring \g<object> without explanation", "cutting off communication")
add("ghosted", "ghosted", r"(?<!\w)(?P<subject>he|she|they|you|I) ghosted (?P<object>me|him|her|us|them|you)(?!\w)",
    r"\g<subject> stopped communicating with \g<object> without explanation", "stopped communicating")
add("ghosting_contraction", "ghosting", r"(?<!\w)(?P<subject>he|she)['’]s ghosting (?P<object>me|him|her|us|them|you)(?!\w)",
    r"\g<subject> is ignoring \g<object> without explanation", "cutting off communication")
add("ghosting_plural_contraction", "ghosting", r"(?<!\w)(?P<subject>they|you)['’]re ghosting (?P<object>me|him|her|us|them|you)(?!\w)",
    r"\g<subject> are ignoring \g<object> without explanation", "cutting off communication")
add("left_on_read", "left on read", r"(?<!\w)left (?P<object>me|you|him|her|us|them) on read(?!\w)",
    r"read the messages from \g<object> but did not reply", "read messages without replying")
add("salty_loss", "salty", r"(?<!\w)(?P<person>he|she|they|I) (?P<verb>is|was|are|were|am) (?:so |really )?salty (?=after losing\b|about (?:losing|the loss)\b)",
    r"\g<person> \g<verb> upset ", "upset about losing")
add("goat_person", "GOAT", r"(?P<subject>my (?:coach|teacher|friend)|he|she|you) (?P<verb>is|are) the GOAT[.!]*",
    r"\g<subject> \g<verb> the greatest of all time.", "greatest of all time, praising a person", "fullmatch")
add("bet_reply", "bet", r"bet[.!]*", "Okay!", "agreement as a standalone reply", "fullmatch")
add("say_less_reply", "say less", r"say less[.!]*", "I understand, no more explanation needed.", "agreement as a standalone reply", "fullmatch")
add("no_cap", "no cap", r"(?P<boundary>^|[,;.!]\s*)no cap(?=[.!]*$)", r"\g<boundary>I am being honest", "standalone statement of sincerity")
add("addy_request", "addy", r"(?<!\w)(?P<verb>send|share|text) (?P<object>me|us) (?:the|your) addy(?!\w)",
    r"\g<verb> \g<object> the address", "address in a request")
add("addy_question", "addy", r"(?<!\w)(?:what['’]?s|what is) (?P<owner>the|your|his|her|their) addy(?!\w)",
    r"what is \g<owner> address", "address in a question")
add("addy_drop", "addy", r"(?<!\w)(?:drop|send|share|text) (?P<owner>the|your) addy(?!\w)",
    r"send \g<owner> address", "address in a request")
add("rn_context", "rn", r"(?<!\w)(?P<state>busy|tired|free|here|there|leaving|working|studying|sleeping) rn(?!\w)",
    r"\g<state> right now", "right now after an activity or state")
for term, plain in {"fr": "I agree", "gg": "Good game", "wya": "Where are you", "wyd": "What are you doing",
                    "yaas": "Yes", "lmao": "That is very funny", "rotflmao": "That is extremely funny",
                    "lol": "That is funny", "lfg": "Let's go!", "poggers": "Amazing!"}.items():
    add(term + "_reply", term, term + r"[.!?]*", plain, plain, "fullmatch")
add("intensifier_af", "AF", r"(?<!\w)(?P<adjective>cold|hot|tired|happy|sad|angry|cool|funny|boring|expensive) af(?!\w)",
    r"extremely \g<adjective>", "strong informal emphasis; profanity softened")
add("intensifier_asl", "ASL", r"(?<!\w)(?P<adjective>cold|hot|tired|happy|sad|angry|cool|funny|boring|expensive) asl(?!\w)",
    r"extremely \g<adjective>", "very strong emphasis in this adjective context")

Path(__file__).with_name("slang_rules.json").write_text(json.dumps(rules, ensure_ascii=False, indent=2) + "\n")
print(f"Built {len(rules)} automatic rules.")
