"""Bounded real-TU comparison and Linux RSS measurements; no full scan."""
import argparse
import copy
import resource
import threading
import time
from unittest.mock import patch
import prototype_batch as batch
from common import *

EVIDENCE=HERE/'evidence/parallel'
PLAN=EVIDENCE/'real_plan.json'
ORIGINAL=batch.process_unit

def measured_unit(e,root,build,out,digest):
    started=time.monotonic()
    result=ORIGINAL(e,root,build,out,digest)
    metrics={'id':e['id'],'pid':os.getpid(),'status':result[1],
             'elapsed_seconds':time.monotonic()-started,
             'self_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             'preprocessor_peak_rss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
    (out/'resources'/f'{e["id"]:05d}.json').write_text(json.dumps(metrics,indent=2)+'\n')
    return result

batch.process_unit=measured_unit

def args_for(jobs):
    return argparse.Namespace(arch='riscv',profile=None,fixture=False,limit=4,jobs=jobs)

def frozen():
    return sha(HERE/'criteria_amendment1.md')==(HERE/'criteria_amendment1_sha256.txt').read_text().split()[0]

def prepare():
    assert frozen()
    if PLAN.exists():
        previous=read(PLAN)
        (Path(previous['run'])/'plan.json').write_bytes(PLAN.read_bytes())
    old=HERE/'prototype_scan/riscv_defconfig/34db2d428b48bd340af614ad9ecb1f9e437e721f5cb572cffd7fb6c2bb07c828'
    old_units=sorted((old/'units').glob('*.json.gz'))
    assert len(old_units)==17
    old_ids=[]
    for p in old_units:
        row=read(p);assert row['status']=='ok' and row['input_digest']==old.name
        old_ids.append(row['id'])
    inputs,entries,root,build,out,digest=batch.context(args_for(4))
    assert digest!=old.name
    selected=[e for e in entries if e['id'] not in old_ids][:4]
    assert len(selected)==4
    run=EVIDENCE/'real'/str(time.time_ns());run.mkdir(parents=True)
    plan={'old_output':str(old),'old_ids':old_ids,'old_files':inputs_manifest(p for p in old.rglob('*') if p.is_file()),
          'production_output':str(out),'input_digest':digest,'selected':[{'id':e['id'],'source':str(e['source'])} for e in selected],
          'total_entries':len(entries),'run':str(run),'tools':inputs['tools'],
          'criteria_sha256':check_criteria(),'amendment_sha256':sha(HERE/'criteria_amendment1.md')}
    write(PLAN.relative_to(HERE),plan)
    (run/'plan.json').write_bytes(PLAN.read_bytes())
    (EVIDENCE/'handoff_before.md').write_bytes((HERE.parents[3]/'交接文档.md').read_bytes())
    print(json.dumps({k:plan[k] for k in ('old_ids','selected','total_entries','run','production_output')},ensure_ascii=False),flush=True)

def meminfo():
    result={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key,value=line.split(':',1)
        if key in ('MemTotal','MemAvailable','SwapTotal','SwapFree'):result[key+'_kib']=int(value.split()[0])
    return result

def process_tree(pid):
    result={};todo=[pid]
    while todo:
        current=todo.pop()
        try:
            status={}
            for line in Path(f'/proc/{current}/status').read_text().splitlines():
                key,value=line.split(':',1)
                if key in ('VmRSS','VmHWM'):status[key]=int(value.split()[0])
            result[current]=status
            children=Path(f'/proc/{current}/task/{current}/children').read_text().split()
            todo.extend(int(c) for c in children)
        except (FileNotFoundError,ProcessLookupError,PermissionError):pass
    return result

def run(jobs):
    plan=read(PLAN);assert frozen()
    inputs,entries,root,build,_,digest=batch.context(args_for(jobs))
    assert digest==plan['input_digest']
    wanted=[s['id'] for s in plan['selected']]
    selected=[e for e in entries if e['id'] in wanted];assert [e['id'] for e in selected]==wanted
    out=Path(plan['run'])/('parallel' if jobs==4 else 'serial')
    assert not out.exists(),'Use a new prepare run; do not overwrite validation evidence'
    (out/'resources').mkdir(parents=True)
    before=meminfo();finished=threading.Event()
    samples={'samples':0,'peak_tree_rss_kib':0,'minimum_available_kib':before['MemAvailable_kib'],
             'minimum_swap_free_kib':before['SwapFree_kib'],'per_pid_peak_rss_kib':{}}
    def monitor():
        while True:
            tree=process_tree(os.getpid());memory=meminfo()
            samples['samples']+=1
            samples['peak_tree_rss_kib']=max(samples['peak_tree_rss_kib'],sum(p.get('VmRSS',0) for p in tree.values()))
            samples['minimum_available_kib']=min(samples['minimum_available_kib'],memory['MemAvailable_kib'])
            samples['minimum_swap_free_kib']=min(samples['minimum_swap_free_kib'],memory['SwapFree_kib'])
            for pid,status in tree.items():
                key=str(pid)
                samples['per_pid_peak_rss_kib'][key]=max(samples['per_pid_peak_rss_kib'].get(key,0),status.get('VmHWM',0))
            if finished.wait(.25):break
    sampler=threading.Thread(target=monitor);sampler.start();started=time.monotonic()
    try:
        with patch.object(batch,'options',return_value=args_for(jobs)),patch.object(batch,'context',return_value=(inputs,selected,root,build,out,digest)):
            batch.main()
    finally:
        finished.set();sampler.join()
        metrics={'jobs':jobs,'elapsed_seconds':time.monotonic()-started,'before':before,'after':meminfo(),**samples}
        (out/'run_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print('metrics='+json.dumps(metrics),flush=True)

def compare():
    plan=read(PLAN);base=Path(plan['run']);results=[]
    assert read(Path(plan['old_output'])/'inputs.json')['tools']['prototype_batch.py']==sha(EVIDENCE/'prototype_batch_before.py')
    assert plan['tools']=={name:sha(HERE/name) for name in plan['tools']}
    for entry in plan['selected']:
        ident=entry['id'];rows=[];traces=[];sizes=[]
        for mode in ('parallel','serial'):
            out=base/mode;row=read(out/'units'/f'{ident:05d}.json.gz')
            assert row['status']=='ok' and row['input_digest']==plan['input_digest']
            trace=row['macros']['preprocessor'];path=out/'traces'/f'{ident:05d}.i.gz'
            assert trace['trace_file']==str(path) and trace['trace_sha256']==sha(path)
            with gzip.open(path,'rb') as f:data=f.read()
            traces.append(data);sizes.append(len(data))
            normalized=copy.deepcopy(row)
            normalized['macros']['preprocessor']['trace_file']=f'@output/traces/{ident:05d}.i.gz'
            normalized['macros']['preprocessor']['trace_sha256']=hashlib.sha256(data).hexdigest()
            rows.append(normalized)
        assert traces[0]==traces[1],f'Trace bytes differ: {ident}'
        assert rows[0]==rows[1],f'Unit fields or list ordering differ: {ident}'
        results.append(entry|{'fields_equal':True,'trace_bytes_equal':True,'trace_bytes':sizes[0],
                              'normalized_json_sha256':batch.enumeration.digest(rows[0])})
    old=Path(plan['old_output'])
    assert plan['old_files']==inputs_manifest(p for p in old.rglob('*') if p.is_file())
    assert check_criteria()==plan['criteria_sha256'] and frozen()
    report={'passed':True,'units':results,'old_cached_units':len(plan['old_ids']),'old_cache_bytes_unchanged':True,
            'input_digest':plan['input_digest'],'run':plan['run'],
            'normalization':['preprocessor.trace_file: output-root mapping only',
                             'preprocessor.trace_sha256: each gzip verified, then decompressed bytes compared exactly'],
            'parallel_metrics':read(base/'parallel/run_metrics.json'),'serial_metrics':read(base/'serial/run_metrics.json'),
            'parallel_units':[read(p) for p in sorted((base/'parallel/resources').glob('*.json'))],
            'serial_units':[read(p) for p in sorted((base/'serial/resources').glob('*.json'))],
            'full_scan_elapsed_seconds':None,'all_units_peak_rss_kib':None}
    write('evidence/parallel/real_result.json',report)
    print('real comparison passed',len(results),'units; original 17 caches unchanged',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run','compare'))
    parser.add_argument('--jobs',type=int,choices=(1,4),default=4)
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action=='run':run(args.jobs)
    else:compare()
