"""Checks saved corrections separately from new model-generated sentences."""
import json
from pathlib import Path
from gradio_client import Client
from bilingual import memory_entries, bengali_entries, recall

OUT=Path('results/bilingual-upgrade');OUT.mkdir(parents=True,exist_ok=True)
EN=[
('These boots are cool asl.','জুতা|বুট'),
('LMS to join the competition.','লাইক|পছন্দ'),
('She was faded at the party.','নেশা|মাতাল'),
('We prefer FFA games.','প্রত্যেক|প্রতিটি|সবার|সবাই|আলাদা|একে অপর'),
('My new waterslide is fire!','ওয়াটার|জল.*স্লাইড|পানির.*স্লাইড'),
('Riya texts me every Friday.','মেসেজ|বার্তা'),
('My electrical plug is broken.','প্লাগ'),
('This bottle needs a cap.','ঢাকনা'),
('You slayed that dance recital.','অনুষ্ঠান|নাচ'),
('Did you see the tackle? That was sick.','ট্যাকল'),
('Send me your addy, please.','ঠিকানা'),
('That song does not slap.','না|নয়'),
('He has a plug for rare records.','রেকর্ড'),
('She has so much rizz.','আকর্ষণ|মন|প্রেম'),
('Do not spill tea on my laptop.','চা'),
('Her name is Addy and she wears a cap.','অ্যাডি'),
('I am so tired of your breadcrumbing.','আশা|মনোযোগ|প্রতিশ্রুতি'),
('I am wearing a hat, not a bottle cap.','টুপি'),
]
BN_EXTRA=[
('আমার মামা আজ বাসায় আসবেন।','uncle'),
('আমি খুব অস্থির বোধ করছি, ঘুমাতে পারছি না।','restless|anxious|uneasy'),
('এই প্যারা পড়ো।','paragraph'),
('এই সমীকরণটা খুব জটিল।','complex|complicated|difficult'),
('পাথরটা খুব কঠিন।','hard|solid'),
('মাথা নষ্ট হয়ে যাচ্ছে, এত কাজের চাপ!','overwhelm|stress|mind|crazy|exhaust'),
('সে আমার শালা, আমার স্ত্রীর ভাই।','brother'),
('এই গানটা জোস না।','not|isn.t'),
('mama, gaan ta joss!','song'),
('eto pera nish na','stress|worry'),
('amar mama ashbe','uncle'),
('ei ongko ta jotil','complicated|difficult|complex'),
]
entries=bengali_entries()
markers=['awesome|excellent|great|cool','awesome|excellent|great|amazing','excellent|great|impressive|amazing','amazing|great|excellent','tea','stress|worry','mind|amazing|incredible|unbeliev','pointless|useless|idle|meaningless|nonsense','fantastic|great|awesome','impressive|excellent|great','bastard|jerk|asshole|rascal|scoundrel','exaggerat|boast|brag|liar']
cases=[{'id':e['id'],'source':e['source'],'direction':'en-bn','group':'saved correction','expected':e['translation']} for e in memory_entries()]
cases += [{'id':'new_en_'+str(i),'source':s,'direction':'en-bn','group':'new English wording','marker':m} for i,(s,m) in enumerate(EN)]
cases += [{'id':e['id'],'source':e['examples'][0],'direction':'bn-en','group':'Bengali example','marker':m} for e,m in zip(entries,markers,strict=True)]
cases += [{'id':'bn_control_'+str(i),'source':s,'direction':'bn-en','group':'Bengali contrast or Banglish','marker':m} for i,(s,m) in enumerate(BN_EXTRA)]
for c in cases:
 if c['group']!='saved correction':assert recall(c['source'],c['direction']) is None
(OUT/'cases.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2)+'\n')
client=Client('http://127.0.0.1:7860',verbose=False)
params=client.view_api(return_format='dict',print_info=False)['named_endpoints']['/run']['parameters']
path=OUT/'actual.jsonl';done={r['id'] for r in map(json.loads,path.read_text().splitlines())} if path.exists() else set()
with path.open('a') as f:
 for group in ['saved correction','new English wording','Bengali example','Bengali contrast or Banglish']:
  pending=[c for c in cases if c['group']==group and c['id'] not in done]
  for i in range(0,len(pending),8):
   batch=pending[i:i+8];values={'text':'\n'.join(c['source'] for c in batch),'direction':batch[0]['direction'],'beams':5,'limit':128,'slang_enabled':True,'clarification':'','slang_mode':'Context'}
   result=client.predict(*[values[p['parameter_name']] for p in params],api_name='/run')
   lines=result[0].splitlines();assert len(lines)==len(batch),(len(lines),len(batch))
   detail=json.loads(result[1])
   for c,target in zip(batch,lines,strict=True):
    c['translation']=target;c['batch_stats']=detail;c['interpretation']=result[2]
    f.write(json.dumps(c,ensure_ascii=False)+'\n')
   f.flush();print(f'{group}: {min(i+8,len(pending))}/{len(pending)}',flush=True)
