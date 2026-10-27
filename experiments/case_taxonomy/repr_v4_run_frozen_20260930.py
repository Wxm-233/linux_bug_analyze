"""Run parent sources with an explicitly frozen rule and save before review."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,sys

HERE=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--freeze',type=Path,required=True)
    p.add_argument('--out-dir',type=Path,required=True)
    p.add_argument('--repo',type=Path,default=Path('/root/repos/linux'))
    args=p.parse_args()
    frozen=json.loads(args.freeze.read_text(encoding='utf-8'))
    for item in frozen['files']:
        path=HERE/item['path']
        if digest(path)!=item['sha256']:raise RuntimeError('frozen dependency changed: '+item['path'])
    sys.path.insert(0,str(HERE))
    from representation_producer_v4 import analyze_revision
    sel=json.loads(args.selection.read_text(encoding='utf-8'))
    if len(sel['targets'])>2:raise RuntimeError('predeclared target cap exceeded')
    args.out_dir.mkdir(parents=True,exist_ok=True)
    records=[]
    for item in sel['targets']:
        sha=item.get('fix_commit',item.get('commit'))
        dest=args.out_dir/(sha[:12]+'_parent_raw.json')
        if dest.exists():raise RuntimeError('refusing to overwrite frozen output')
        try:
            report=analyze_revision(args.repo,item['old_revision'],item['source_path'])
            status='ok'
        except Exception as exc:
            report={'runner_error':type(exc).__name__+': '+str(exc),'revision':item['old_revision'],'source_file':item['source_path']}
            status='runner_error'
        dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        records.append({'commit':sha,'source_path':item['source_path'],'old_revision':item['old_revision'],
                        'output':dest.name,'sha256':digest(dest),'runner_status':status})
    manifest={'stage':'parent-only outputs saved before root result/patch/body review',
        'saved_at_utc':datetime.now(timezone.utc).isoformat(),'selection_sha256':digest(args.selection),
        'freeze_sha256':digest(args.freeze),'records':records,'sampling_limit':sel.get('selection',sel.get('interpretation_limit'))}
    (args.out_dir/'raw_manifest_pre_review.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('saved',len(records),'parent outputs and manifest')
if __name__=='__main__':main()
