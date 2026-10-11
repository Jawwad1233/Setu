"""Narrow, inspectable Bangladeshi phrase rules; unknown contexts retain the source."""
import re

ROMAN = {
 'mama':'মামা','mamu':'মামা','mamma':'মামা','gaan':'গান','gan':'গান','ta':'টা',
 'joss':'জোস','josh':'জোস','osthir':'অস্থির','ostheer':'অস্থির','jotil':'জটিল','jatil':'জটিল',
 'eto':'এত','pera':'প্যারা','pyara':'প্যারা','nish':'নিস','nishna':'নিস না','nis':'নিস','na':'না',
 'nai':'নাই','nei':'নেই','amar':'আমার','tomar':'তোমার','tor':'তোর','ashbe':'আসবে','asbe':'আসবে',
 'ei':'এই','oi':'ওই','ongko':'অঙ্ক','onko':'অঙ্ক','ank':'অঙ্ক','bhalo':'ভালো','khub':'খুব',
 'purai':'পুরাই','ekdom':'একদম','notun':'নতুন','bike':'বাইক','chobi':'ছবি','khela':'খেলা',
 'bhai':'ভাই','dost':'বন্ধু','ektu':'একটু','cha':'চা','den':'দেন','dao':'দাও','koro':'করো',
 'matha':'মাথা','noshto':'নষ্ট','nosto':'নষ্ট','alga':'আলগা','alap':'আলাপ','jhakkas':'ঝাক্কাস',
 'kothin':'কঠিন','shala':'শালা','chapabaj':'চাপাবাজ','sheirokom':'সেইরকম','seirokom':'সেইরকম',
}

def transliterate_known(text):
    tokens=re.findall(r"[A-Za-z]+",text)
    if not tokens or any(t.lower() not in ROMAN for t in tokens):return None
    result=re.sub(r'[A-Za-z]+',lambda m:ROMAN[m[0].lower()],text)
    return re.sub(r'(\S+) টা(?=\s|[,.!?]|$)',r'\1টা',result)

def normalize(text):
    romanized=not any('\u0980'<=c<='\u09ff' for c in text)
    if romanized:
        converted=transliterate_known(text)
        if converted is None:return None, ['Banglish spelling not covered by the phrase rules.']
        text=converted
    original=text; notes=[]
    # Paragraphs and stress have different meanings; decide from explicit context.
    if re.search(r'প্যারা',text) and re.search(r'পড়|পড়|লেখা|বই|অনুচ্ছেদ',text):
        text=text.replace('প্যারা','অনুচ্ছেদ')
    else:
        text=re.sub(r'প্যারা (?:নিস|নিও|নেন|নাও) না', 'দুশ্চিন্তা করো না',text)
        text=re.sub(r'প্যারা (?:দিস|দিও|দেন|দাও) না', 'বিরক্ত করো না',text)
        text=re.sub(r'(?:কোনো |কোন |কোনও )?প্যারা (?:নাই|নেই)', 'কোনো সমস্যা নেই',text)
        text=re.sub(r'প্যারা খাচ্ছি', 'মানসিক চাপে আছি',text)
    # An addressed stranger/friend differs from a possessive family relationship.
    text=re.sub(r'^(মামা|মামু)\s*[,，]', 'ভাই,',text)
    text=re.sub(r'(আমার|তোমার|তোর|ওর|তার|তাঁর|আপনার|আমাদের|তোমাদের|তাদের) মামা',r'\1 মায়ের ভাই',text)
    text=text.replace('একটু চা দেন','আমাকে একটু চা দিন')
    text=text.replace('আলগা আলাপ','অর্থহীন কথা').replace('চাপাবাজি','বাড়িয়ে মিথ্যা কথা বলা').replace('চাপাবাজ','মিথ্যা বড়াই করে এমন মানুষ')
    if re.search(r'মিথ্যা|অসভ্য|ফালতু|বিরক্ত',text):
        text=re.sub(r'^শালা\s*[,，]', 'বদমাশ,',text)
    # Evaluate praise only for explicit objects/performances, not equations or anxious people.
    positive=bool(re.search(r'গান|খেলা|বাইক|ছবি|জুতা|জুত[োা]|পোশাক|পারফরম্যান্স|ভিডিও|সিনেমা|খাবার|বিরিয়ানি|বিরিয়ানি',text))
    literal=bool(re.search(r'সমীকরণ|অঙ্ক|গণিত|পাথর|পরীক্ষা|সমস্যা|ঘুম|উদ্বেগ|অসুস্থ|দুশ্চিন্তা|অপেক্ষা',text))
    comparison=bool(re.search(r'যেমন|মতো|চেয়েছিলে|চেয়েছিলে|ঠিক সেই',text))
    if positive and not literal:
        text=re.sub(r'জোস|জোশ|ঝাক্কাস|অস্থির|জটিল|কঠিন', 'দারুণ',text)
        if not comparison:text=re.sub(r'সেইরকম|সেই রকম|সেইরাম','দারুণ',text)
    # These unambiguous approval words need no claim about physical temperature.
    text=re.sub(r'জোস|জোশ|ঝাক্কাস','দারুণ',text)
    if 'মাথা নষ্ট' in text or 'মাথানষ্ট' in text:
        if re.search(r'চাপ|কাজ|চিন্তা',text):text=re.sub(r'মাথা ?নষ্ট হয়ে যাচ্ছে','মানসিকভাবে অতিষ্ঠ হয়ে যাচ্ছি',text)
        elif re.search(r'গোল|দারুণ|অসাধারণ|অবিশ্বাস্য',text):text=re.sub(r'মাথা ?নষ্ট','অবিশ্বাস্য',text)
    if text!=original:notes.append('Bengali context rules: '+text)
    else:notes.append('No unambiguous slang rule applied; kept the Bengali wording.')
    if romanized:notes.insert(0,'Used the supported Banglish spelling map.')
    return text,notes


def repair_english(original, prepared, translation):
    """Repair specific dictionary senses lost by the base model, without changing unrelated clauses."""
    source=original+' '+prepared
    notes=[]
    if 'মায়ের ভাই' in prepared:
        updated=re.sub(r"mother['’]s brother",'maternal uncle',translation,flags=re.I)
        if updated!=translation:notes.append('Preserved the maternal-uncle relationship.')
        translation=updated
    if re.search(r'প্যারা',source) and re.search(r'পড়|পড়|অনুচ্ছেদ',source):
        translation=re.sub(r'\barticle\b','paragraph',translation,flags=re.I)
        notes.append('Reading context: paragraph.')
    if re.search(r'^শালা\s*[,，]',original) and re.search(r'মিথ্যা|অসভ্য|ফালতু|বিরক্ত',original):
        if not re.search(r'bastard|rascal|scoundrel|jerk|asshole',translation,re.I):
            translation='You bastard, '+translation[0].lower()+translation[1:] if translation else translation
            notes.append('Preserved the explicit insult rather than dropping it.')
    if re.search(r'অঙ্ক',prepared) and re.search(r'জটিল',prepared):
        translation=re.sub(r'\bnumber\b','math problem',translation,flags=re.I)
    if re.match(r'^(?:মামা|মামু|mama|mamu)\s*[,，]',original,re.I):
        translation=re.sub(r'^Brother\b','Mate',translation,flags=re.I)
    return translation,notes
