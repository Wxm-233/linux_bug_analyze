"""Patch-informed syntax sampling only; never consult checker output."""
from pathlib import Path
from datetime import datetime,timezone
import subprocess,json,hashlib,re
from repr_v3_patch_challenge_strict_select import exact_pairs

HERE=Path(__file__).parent
def git(*args):return subprocess.run(['git','-C','/root/repos/linux',*args],capture_output=True,text=True,check=True).stdout
def main():
    poolpath=HERE/'repr_v4_metadata_pool_20260930.json'
    pool=json.loads(poolpath.read_text(encoding='utf-8'))
    metadata=json.loads((HERE/'repr_v4_selection_20260930_pre.json').read_text(encoding='utf-8'))
    excluded_paths={t['source_path'] for t in metadata['targets']}
    excluded_paths.update({'drivers/mmc/host/dw_mmc.c','drivers/scsi/hisi_sas/hisi_sas_v3_hw.c'})
    targets=[];used=set();examined=[]
    for item in pool['records']:
        sha=item['commit'];examined.append(sha)
        for path in item['paths']:
            if not path.startswith('drivers/') or not path.endswith('.c') or path in excluded_paths:continue
            directory=str(Path(path).parent)
            if directory in used:continue
            pairs=exact_pairs(git('show','--format=','--unified=0','--no-ext-diff',sha,'--',path).splitlines())
            # Named object macros exercise the frozen v4 extension. No source or
            # report is consulted to establish type, correctness or outcome.
            pairs=[p for p in pairs if re.fullmatch(r'[A-Za-z_]\w*',p['rhs'])]
            if not pairs:continue
            targets.append({'fix_commit':sha,'old_revision':git('rev-parse',sha+'^').strip(),
                'source_path':path,'subject':item['subject'],'date':item['date'],
                'matched_same_lhs_rhs_pairs':pairs})
            used.add(directory);break
        if len(targets)==2:break
    report={'selected_at_utc':datetime.now(timezone.utc).isoformat(),'examined_commits':examined,
        'cap':100,'excluded_source_paths':sorted(excluded_paths),'pool_sha256':hashlib.sha256(poolpath.read_bytes()).hexdigest(),'targets':targets,
        'selection':'Patch-informed syntax selection on the fixed metadata pool, independent of checker output; first two distinct C directories with same lhs and named-macro rhs conversion pair.',
        'interpretation_limit':'Not blind selection or prevalence. Pairing can mix functions or modes; review only after parent raw output saved.'}
    dest=HERE/'repr_v4_20260930'/'patch_selection_pre_run.json'
    if dest.exists():raise RuntimeError('selection already exists')
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('patch-informed selection saved:',len(targets),'targets;',len(examined),'commits examined')
if __name__=='__main__':main()
