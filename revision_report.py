"""Keep retrieval checks separate from model inference and human language review."""
import html
import json
import re
from pathlib import Path

out=Path('results/bilingual-upgrade')
rows=[json.loads(l) for l in (out/'actual.jsonl').read_text().splitlines()]
baseline={r['id']:r['translation'] for r in map(json.loads,Path('results/full-glossary-final/translations.jsonl').read_text().splitlines())}
review_path=out/'review-notes.json'
notes=json.loads(review_path.read_text()) if review_path.exists() else {}
for r in rows:
    r['check']=(r['translation']==r['expected']) if r['group']=='saved correction' else bool(re.search(r['marker'],r['translation'],re.I))
    r['review']=notes.get(r['id'],'Native-speaker review pending; automatic checks do not prove semantic accuracy.')
saved=[r for r in rows if r['group']=='saved correction'];fresh=[r for r in rows if r['group']!='saved correction']
summary={'total_cases':len(rows),'saved_corrections_checked':len(saved),'saved_matches':sum(r['check'] for r in saved),'fresh_cases':len(fresh),'fresh_marker_checks_passed':sum(r['check'] for r in fresh),'failed_markers':[r['id'] for r in fresh if not r['check']], 'manual_review_notes':notes,'methodology':'Saved corrections are exact phrasebook retrieval, not model accuracy. Fresh wording checks are development cases and may have influenced rules. Word markers are partial checks only. No model fine-tuning occurred. Bengali meanings need native and regional review.'}
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
e=html.escape
cards=[]
for r in rows:
    before=baseline.get(r['id'],'No earlier baseline for this new sentence.')
    label='Saved correction matched' if r['group']=='saved correction' and r['check'] else 'Marker check passed' if r['check'] else 'Needs attention'
    cards.append(f'''<article data-search="{e((r['source']+' '+r['group']+' '+label).lower(),quote=True)}"><header><h2>{e(r['id'])}</h2><span>{e(r['group'])} · {label}</span></header><div class="grid"><section><label>Input</label><p>{e(r['source'])}</p></section><section><label>Earlier result</label><p>{e(before)}</p></section><section><label>Current result</label><p>{e(r['translation'])}</p></section></div><small>{e(r['review'])}</small></article>''')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Setu bilingual corrections</title><style>
body{font:16px/1.6 system-ui,sans-serif;max-width:1250px;margin:auto;padding:28px;color:#193d32;background:#f5f4ef}article{background:white;border:1px solid #dce4da;border-radius:16px;padding:20px;margin:14px 0}header{display:flex;gap:20px;justify-content:space-between;align-items:center}h2{font-size:18px}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}label,small,header span{font-size:12px;color:#627367}input{font:inherit;padding:12px;width:min(650px,90%);border:1px solid #b9cbbb;border-radius:8px;position:sticky;top:12px;background:white}@media(max-width:700px){.grid{grid-template-columns:1fr}header{display:block}body{padding:16px}}</style><h1>সেতু · Bilingual correction review</h1>'''
page+=f'<p><strong>{len(saved)} saved corrections checked; {sum(r["check"] for r in saved)} matched.</strong> These are phrasebook lookups, not an accuracy score.</p><p><strong>{len(fresh)} fresh wording cases; {sum(r["check"] for r in fresh)} passed the limited word-marker checks.</strong> Read each result: these development checks are not independent bilingual validation.</p>'
page+='<p>The app uses full IndicTrans2 models, a local English context helper, and context rules for 12 Bengali entries. No model weights were trained. The linked Scribd document could not be read reliably; its contents were not imported.</p><input id="filter" aria-label="Filter cases" placeholder="Search text, group, or Needs attention">'+''.join(cards)
page+="<script>document.querySelector('#filter').addEventListener('input',e=>document.querySelectorAll('article').forEach(a=>a.hidden=!a.dataset.search.includes(e.target.value.toLowerCase())))</script></html>"
(out/'review.html').write_text(page)
print(json.dumps({k:v for k,v in summary.items() if k!='manual_review_notes'},indent=2))
