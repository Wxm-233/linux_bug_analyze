"""Summarize classification outputs without treating model labels as ground truth."""
import argparse,collections,json,statistics
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True);a=p.parse_args();out=a.outdir
m=json.loads((out/'manifest.json').read_text());u=json.loads((out/'usage.json').read_text())
failed_path=out/'failed_review.json';failed=json.loads(failed_path.read_text()) if failed_path.exists() else []
fail_ids={r['hash'] for r in failed};rows=[];cells=collections.defaultdict(collections.Counter)
for s in m['samples']:
    path=out/'results'/(s['hash']+'.json')
    if path.exists():
        r=json.loads(path.read_text());rows.append(r)
        cells[(s['band'],s['stratum'])][r['decision']['relevance']]+=1
    elif s['hash'] in fail_ids:cells[(s['band'],s['stratum'])]['validation_failed']+=1
    else:cells[(s['band'],s['stratum'])]['pending']+=1
raw=collections.Counter(r['model_decision']['relevance'] for r in rows)
final=collections.Counter(r['decision']['relevance'] for r in rows)
changed=[r for r in rows if r['model_decision']['relevance']!=r['decision']['relevance']]
elapsed=[r['elapsed_seconds'] for r in u['records'] if 'elapsed_seconds' in r]
summary={'status':u['status'],'planned':len(m['samples']),'valid':len(rows),'format_failed':len(fail_ids),
    'pending':len(m['samples'])-len(rows)-len(fail_ids),'model_counts':dict(raw),'program_counts':dict(final),
    'decision_changed_by_program':len(changed),'requests':u['requests'],'reported_tokens':u['reported_tokens'],
    'charged_tokens_including_unknown_or_inflight':u['charged_tokens'],'api_seconds_sum':sum(elapsed),
    'request_median_seconds':statistics.median(elapsed) if elapsed else None,
    'cells':[{'band':k[0],'stratum':k[1],**dict(v)} for k,v in sorted(cells.items())],
    'limitations':['equal cell quotas are not proportional sampling','no human gold labels; cannot calculate precision or recall','unknown usage remains charged','related/uncertain are review leads, not confirmed defects']}
(out/'pilot-report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k not in ('cells','limitations')},indent=2))
