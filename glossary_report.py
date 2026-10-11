"""Create a reviewable report; execution success is not semantic accuracy."""
import csv
import html
import json
from pathlib import Path
import re
import sys

directory = Path(sys.argv[1])
rows = [json.loads(line) for line in (directory / 'translations.jsonl').read_text().splitlines()]
entries = {e['id']: e for e in json.loads(Path('slang_glossary.json').read_text())['entries']}
audit_path = directory / 'audit-notes.json'
audit = json.loads(audit_path.read_text()) if audit_path.exists() else {}
control_pass, control_fail = 0, []
for row in rows:
    result = row['context']
    expected = row['expected']
    if row['origin'] == 'contrast control':
        if expected is None:
            passed = result['text'] == row['source']
        elif expected == 'uncertain':
            passed = result['status'] == 'uncertain' and result['text'] == row['source']
        else:
            passed = bool(re.search(expected, result['text'], re.I))
        row['check'] = 'control pass' if passed else 'control failed'
        if passed: control_pass += 1
        else: control_fail.append(row['id'])
    else:
        row['check'] = 'needs bilingual review'
    if result['status'] == 'literal' and row['origin'] != 'contrast control':
        row['check'] += '; check whether slang was left unchanged'
    if row.get('translation_stats', {}).get('output_cap_reached'):
        row['check'] += '; translation reached output limit'
    if re.search(r'(.)\1{11,}', row['translation']) or re.search(r'(?<!\S)(\S+)(?:\s+\1){7,}', row['translation']):
        row['check'] += '; repeated translation output'
    if row['id'] in audit:
        row['check'] += '; known issue: ' + audit[row['id']]
    if result['status'] == 'uncertain' or result.get('possible_unexpanded_terms'):
        row['check'] += '; inspect interpretation'

summary = {'total_cases':len(rows), 'glossary_entries_exercised':len([r for r in rows if r['id'] in entries]),
           'known_review_issues':audit,
           'controls_passed':control_pass, 'controls_failed':control_fail,
           'uncertain_cases':[r['id'] for r in rows if r['context']['status']=='uncertain'],
           'note':'Control checks cover English interpretation only. Bengali outputs require bilingual review. Source examples are development cases, not a held-out accuracy benchmark.'}
(directory / 'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
with (directory / 'review.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['Expression','Input','Interpreted English','Bangla','Decision','Reason','Review'])
    for r in rows:
        writer.writerow([r['term'],r['source'],r['context']['text'],r['translation'],r['context']['status'],r['context']['reason'],r['check']])

e=html.escape
body=[]
for r in rows:
    definition=entries.get(r['id'],{}).get('definition','Literal or variation control')
    body.append(f'''<article data-search="{e((r['term']+' '+r['source']+' '+r['check']).lower(),quote=True)}">
    <div class="top"><h2>{e(r['term'])}</h2><span>{e(r['check'])}</span></div>
    <p class="definition">{e(definition)}</p><div class="grid">
    <div><label>Original</label><p>{e(r['source'])}</p></div>
    <div><label>Interpreted English</label><p>{e(r['context']['text'])}</p></div>
    <div><label>Bangla output</label><p lang="bn">{e(r['translation'])}</p></div></div>
    <small>{e(r['context']['status'])}: {e(r['context']['reason'])}</small></article>''')
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Setu — full glossary review</title><style>
body{font:16px/1.6 system-ui,sans-serif;background:#f5f4ef;color:#193d32;margin:0;padding:32px;max-width:1250px;margin:auto}
h1{font-size:32px}article{background:white;border:1px solid #dae2d8;padding:22px;border-radius:16px;margin:16px 0}
.top{display:flex;justify-content:space-between;gap:16px;align-items:center}.top h2{font-size:20px;margin:0}.top span{font-size:12px;color:#6e5932}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:24px}.grid p{white-space:pre-wrap}label{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#65776b}
.definition,small{color:#65776b;font-size:13px}input{font:inherit;padding:12px;width:min(600px,90%);border-radius:8px;border:1px solid #bdcdbd;position:sticky;top:12px;background:white}
@media(max-width:750px){.grid{grid-template-columns:1fr}body{padding:16px}.top{align-items:start;flex-direction:column}}
</style><h1>সেতু · Full glossary review</h1>
<p>Every glossary entry is exercised below. These are development examples, not an independent accuracy score. A successful run does not prove a correct translation.</p>'''
page+=f'<p><strong>{summary["glossary_entries_exercised"]} glossary entries · {len(rows)} total cases · {control_pass} English control checks passed.</strong> Review the Bangla wording with a bilingual speaker.</p>'
page+='<input aria-label="Filter report" placeholder="Search a term, sentence, or “inspect”…" id="filter">'+''.join(body)
page+='''<script>document.getElementById('filter').addEventListener('input',e=>{let q=e.target.value.toLowerCase();document.querySelectorAll('article').forEach(a=>a.hidden=!a.dataset.search.includes(q))})</script></html>'''
(directory/'review.html').write_text(page)
print(json.dumps(summary,indent=2))
