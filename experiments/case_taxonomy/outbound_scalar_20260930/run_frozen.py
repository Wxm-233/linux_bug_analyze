"""Save frozen rule outputs before review; keep post-review fixes separate."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib, json, sys

HERE=Path(__file__).resolve().parent
RULES=HERE.parent
MODULES=['outbound_scalar_single_revision','representation_producer_v5']

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase',choices=['parent','fix'],required=True)
    ap.add_argument('--repo',type=Path,default=Path('/root/repos/linux'))
    args=ap.parse_args()
    freeze=HERE/'freeze_manifest.json'
    selection=HERE/'selection_pre.json'
    frozen=json.loads(freeze.read_text(encoding='utf-8'))
    for rec in frozen['files']:
        if sha(RULES/rec['path'])!=rec['sha256']:
            raise RuntimeError('frozen file changed: '+rec['path'])
    if sha(selection)!=frozen['selection_sha256']:
        raise RuntimeError('preselection changed')
    targets=json.loads(selection.read_text(encoding='utf-8'))['targets']
    if len(targets)>2:raise RuntimeError('target cap exceeded')
    out=HERE/'holdout'
    out.mkdir(exist_ok=True)
    parent_manifest=out/'parent_manifest_pre_review.json'
    if args.phase=='fix':
        pm=json.loads(parent_manifest.read_text(encoding='utf-8'))
        if pm['freeze_sha256']!=sha(freeze) or pm['selection_sha256']!=sha(selection):
            raise RuntimeError('parent manifest differs from freeze or selection')
        for rec in pm['records']:
            if sha(out/rec['output'])!=rec['sha256']:
                raise RuntimeError('parent raw output changed')
    manifest_path=parent_manifest if args.phase=='parent' else out/'fix_manifest_post_review.json'
    if manifest_path.exists():raise RuntimeError('refusing to replace manifest')
    sys.path.insert(0,str(RULES))
    loaded=[(name,importlib.import_module(name)) for name in MODULES]
    records=[]
    for target in targets:
        revision=target['old_revision'] if args.phase=='parent' else target['commit']
        for name,module in loaded:
            dest=out/(target['commit'][:12]+'_'+name+'_'+args.phase+'_raw.json')
            if dest.exists():raise RuntimeError('refusing to overwrite raw output')
            try:
                report=module.analyze_revision(args.repo,revision,target['source_path'])
                status='ok'
            except Exception as exc:
                report={'runner_error':type(exc).__name__+': '+str(exc)}
                status='runner_error'
            envelope={'target':target['commit'],'revision':revision,'source_path':target['source_path'],
                      'phase':args.phase,'module':name,'analysis':report}
            dest.write_text(json.dumps(envelope,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            records.append({'target':target['commit'],'revision':revision,'source_path':target['source_path'],
                            'module':name,'output':dest.name,'sha256':sha(dest),'runner_status':status})
    report={'phase':args.phase,'saved_at_utc':datetime.now(timezone.utc).isoformat(),
            'stage':'parent results saved before target body/patch/source review' if args.phase=='parent' else 'fix counterpart after parent save and source review',
            'freeze_sha256':sha(freeze),'selection_sha256':sha(selection),'records':records,
            'scope':'Purposeful metadata leads. Zero sites, insufficient evidence and errors are not normal/positive classifications.'}
    manifest_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('saved',len(records),args.phase,'raw reports and manifest')

if __name__=='__main__':main()
