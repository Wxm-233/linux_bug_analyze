"""Frozen rank/keyword strata; bounded single-run pilot with cumulative resume."""
import argparse, collections, hashlib, json, random, re, sys, time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from linux_bug_analyze.config import load_settings, resolve_api_key
from linux_bug_analyze.git_repository import GitRepository
from linux_bug_analyze.llm import create_openai_client
from linux_bug_analyze.screening import ScreenRunner, StopRun, PROMPT_VERSION
from linux_bug_analyze.reporting import write_text_atomic

def restore_budget(runner, old):
    """Unknown/in-flight reservations stay charged across process restarts."""
    assert old['max_requests']==runner.max_requests and old['token_budget']==runner.token_budget
    runner.requests=old['requests'];runner.charged_tokens=old['charged_tokens']
    runner.reported_tokens=old['reported_tokens'];runner.records=old['records']

def main():
    p=argparse.ArgumentParser();p.add_argument('--outdir',type=Path,required=True)
    p.add_argument('--settings',type=Path,required=True);p.add_argument('--run',action='store_true');a=p.parse_args()
    root=Path(__file__).resolve().parents[2];out=a.outdir.resolve();out.mkdir(parents=True,exist_ok=True)
    manifest=out/'manifest.json'
    if not manifest.exists():
        seen=set()
        for f in (root/'analysis_out').rglob('*'):
            if f.is_file() and re.fullmatch('[0-9a-f]{40}',f.stem):seen.add(f.stem)
            if f.is_file() and f.name in ('hashes.txt','selected_hashes.txt'):
                seen.update(re.findall(r'\b[0-9a-f]{40}\b',f.read_text(errors='replace')))
        groups=collections.defaultdict(list);patterns=[('representation',r'compat|endian|bitmap|word size|32.bit|64.bit'),('lifecycle',r'topolog|hotplug|online|offline|lifecycle'),('geometry',r'page size|pagesize|granul|align|mtu'),('capability',r'acpi|iommu|smmu|capabil|permission')]
        audit=root/'candidate_hashes.txt.audit.jsonl'
        with audit.open() as f:
            summary=json.loads(next(f))
            for line in f:
                r=json.loads(line)
                if r['hash'] in seen:continue
                band=min(4,r['input_index']*5//summary['scanned'])
                category=next((k for k,pat in patterns if re.search(pat,r['subject'],re.I)),'other')
                groups[(band,category)].append({'hash':r['hash'],'subject':r['subject'],'band':band,'stratum':category})
        rng=random.Random(20260921);selected=[];sizes={}
        for key,rows in sorted(groups.items()):
            rng.shuffle(rows);selected+=rows[:20];sizes[str(key)]=len(rows)
        rng.shuffle(selected)
        data={'seed':20260921,'method':'five chronological scan-rank bands x five priority subject-keyword groups; 20 per cell, no replacement; not population-proportional',
              'excluded_seen':len(seen),'population_sha256':hashlib.sha256(audit.read_bytes()).hexdigest(),'cell_sizes':sizes,
              'max_requests':600,'token_budget':4000000,'max_tokens':1200,'samples':selected}
        assert len(selected)==500 and len({r['hash'] for r in selected})==500
        manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    data=json.loads(manifest.read_text());print('frozen_samples',len(data['samples']),flush=True)
    if not a.run:return
    # Prevent simultaneous processes from sharing a budget or overwriting responses.
    import fcntl
    lock=(out/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    settings=load_settings(a.settings,required=True)
    context=settings.context_md.read_text() if settings.context_md else ''
    identity={'model':settings.model,'base_url':settings.base_url,'prompt_version':PROMPT_VERSION,
              'context_sha256':hashlib.sha256(context.encode()).hexdigest(),'max_diff_chars':settings.max_diff_chars,
              'source_hashes':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (root/'linux_bug_analyze').glob('*.py')}}
    identity_path=out/'identity.json'
    if identity_path.exists():assert json.loads(identity_path.read_text())==identity,'configuration changed; do not reuse pilot'
    else:identity_path.write_text(json.dumps(identity,indent=2)+'\n')
    client=create_openai_client(resolve_api_key(None,settings.api_key_file),settings.base_url)
    ledger=out/'runs'/str(time.time_ns())
    runner=ScreenRunner(client,out,model=settings.model,max_requests=600,token_budget=4000000,max_tokens=1200,ledger=ledger)
    usage=out/'usage.json'
    if usage.exists():
        restore_budget(runner,json.loads(usage.read_text()))
    repo=GitRepository(settings.linux_dir);repo.validate();start=time.monotonic();status='completed';rows=[];failures=[];consecutive=0
    try:
        for sample in data['samples']:
            commit=repo.get_commit(sample['hash'],settings.max_diff_chars if settings.max_diff_chars is not None else 20000)
            attempts=[r for r in runner.records if r['hash']==sample['hash']]
            exhausted=len(attempts)>=2 and all(r.get('error_type')=='ValueError' for r in attempts[-2:])
            try:
                if exhausted:raise StopRun('isolated validation failure')
                decision=runner.screen(commit,context)
            except StopRun:
                attempts=[r for r in runner.records if r['hash']==sample['hash']]
                if len(attempts)<2 or not all(r.get('error_type')=='ValueError' for r in attempts[-2:]):raise
                failures.append({'hash':sample['hash'],'reason':'two validation failures; manual review required'})
                consecutive+=1
                decision={'relevance':'uncertain','needs_review':True,'reason':'格式校验失败，未获得有效模型判定','evidence':[]}
                if consecutive>=3:raise StopRun('three consecutive samples failed validation')
            else:consecutive=0
            rows.append({**sample,'decision':decision})
            write_text_atomic(out/'failed_review.json',json.dumps(failures,ensure_ascii=False,indent=2))
            write_text_atomic(out/'selected_hashes.txt',''.join(r['hash']+'\n' for r in rows if r['decision']['relevance']!='unrelated' or r['decision']['needs_review']))
            print(len(rows),sample['hash'],decision['relevance'],flush=True)
    except StopRun as e:status=str(e)
    except KeyboardInterrupt:status='interrupted'
    finally:
        runner.save_usage(status)
        write_text_atomic(out/'summary.json',json.dumps({'status':status,'processed':len(rows),'valid_results':len(rows)-len(failures),'validation_failures':len(failures),'counts':dict(collections.Counter(r['decision']['relevance'] for r in rows)),
          'wall_seconds_this_run':time.monotonic()-start,'requests_cumulative':runner.requests,'tokens_cumulative':runner.charged_tokens},ensure_ascii=False,indent=2))
    print(status,flush=True)
if __name__=='__main__':main()
