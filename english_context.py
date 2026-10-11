"""High-confidence constructions whose clauses must not be dropped by the helper."""
import re

def rewrite(text):
    m=re.fullmatch(r'LMS(?P<rest>\s+(?:to|if|and)\b.+)',text.strip(),re.I)
    if m:return 'Like my post'+m['rest'], 'Expanded LMS while preserving the condition.'
    m=re.fullmatch(r"(?:I am|I'm|I’m) (?P<intensity>so |really |very )?(?:tired|sick) of your breadcrumbing[.!]?",text.strip(),re.I)
    if m:
        return 'I am '+('very ' if m['intensity'] else '')+'frustrated by your occasional attention without commitment.', 'Preserved frustration without adding a third person.'
    return None
