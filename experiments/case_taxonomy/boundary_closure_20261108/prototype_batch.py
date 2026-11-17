"""Resumable prototype evidence scan. Full runs are delegated to Claude."""
import argparse
import multiprocessing as mp
from multiprocessing.connection import wait
import sys
from common import *
from prototype import Unit,macros,callback_collect
sys.path.insert(0,str(OLD))
import enumerate as enumeration

def options():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('arch',choices=ARCHES);p.add_argument('--limit',type=int,default=8)
    p.add_argument('--jobs',type=int,default=1,help='maximum concurrent units (default: 1)')
    p.add_argument('--profile');p.add_argument('--fixture',action='store_true')
    args=p.parse_args()
    if args.jobs<1:p.error('--jobs must be positive')
    return args

def context(args):
    check_criteria()
    code={n:sha(HERE/n) for n in ('criteria.md','common.py','prototype.py','prototype_batch.py')}
    if args.fixture:
        root=HERE/'prototype_src';build=None
        entries=[{'id':i,'source':root/f,'directory':root,'args':['-std=gnu11','-I'+str(root)]}
                 for i,f in enumerate(('arch/provider.c','public.c'))]
        inputs={'fixture':True,'files':{p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()},'tools':code}
        label='fixture'
    else:
        root=KSRC
        assert git('rev-parse','HEAD').strip()=='df2908090cda368b01ff43709f51890076c56157'
        assert not git('status','--porcelain=v1')
        if args.profile:
            profile=next(p for p in read(HERE/'config_matrix.json')['profiles'] if p['name']==args.profile)
            assert profile['arch']==args.arch
            build=Path(profile['output']);label=profile['name']
            record=read(HERE/f'build_validation/{label}.json')
            assert record['completed'] and record['config_sha256']==sha(build/'.config')
        else:
            build=Path('/root/work/boundary_build')/(args.arch+'_defconfig');label=args.arch+'_defconfig'
            expected=read(OLD/f'result_{args.arch}.json')['inputs']
            assert expected['config_sha256']==sha(build/'.config')
            assert expected['compile_commands_sha256']==sha(build/'compile_commands.json')
        assert (build/'status.txt').read_text().strip()=='success'
        database=build/'compile_commands.json'
        loaded=enumeration.load_entries(database)
        entries=[];excluded=[]
        for e in loaded:
            if not e.is_c:continue
            relative=enumeration.Paths(root,build).name(str(e.source))
            if relative.removeprefix('@build/').startswith(('scripts/','tools/')) or relative.endswith('.mod.c'):
                excluded.append({'id':e.number,'source':relative,'reason':'explicit_host_or_module_metadata'});continue
            entries.append({'id':e.number,'source':e.source,'directory':e.directory,'args':enumeration.parse_args(e)})
        headers={p.relative_to(build).as_posix():sha(p) for p in build.rglob('*.h') if p.is_file()}
        inputs={'fixture':False,'arch':args.arch,'kernel_head':git('rev-parse','HEAD').strip(),
                'build':str(build),'config_sha256':sha(build/'.config'),
                'compile_commands_sha256':sha(database),'generated_headers_sha256':enumeration.digest(headers),
                'tools':code,'excluded_units':excluded,'clang':enumeration.command(['clang','--version'])}
    fingerprint=enumeration.digest(inputs)
    output=HERE/'prototype_scan'/label/fingerprint
    return inputs,entries,root,build,output,fingerprint

def save_unit(out,row):
    p=out/'units'/f'{row["id"]:05d}.json.gz'
    temporary=p.with_suffix('.pending')
    with gzip.open(temporary,'wt',encoding='utf-8') as f:json.dump(row,f,ensure_ascii=False,separators=(',',':'))
    temporary.replace(p)

def unit_row(e,fingerprint):
    return {'id':e['id'],'source':str(e['source']),'input_digest':fingerprint,'status':'failed'}

def process_unit(e,root,build,out,fingerprint):
    row=unit_row(e,fingerprint)
    try:
        u=Unit(e['source'],e['args'],e['directory'],root,build)
        trace=u.preprocess(out/'traces'/f'{e["id"]:05d}.i.gz')
        row.update({'status':'ok','macros':macros(u,trace,compact=True),'callbacks':callback_collect(u)})
    except Exception as error:
        row['error']=repr(error)
    save_unit(out,row)
    return e['id'],row['status'],row.get('error')

def worker(e,root,build,out,fingerprint,connection,stop):
    try:
        result=process_unit(e,root,build,out,fingerprint)
        if result[1]!='ok':stop.set()
        # Error text may exceed the pipe buffer. Keep IPC bounded and read the
        # already-published failure record in the parent instead.
        connection.send(result[:2])
    finally:connection.close()

def parallel_batch(batch,root,build,out,fingerprint,jobs):
    # Fresh processes bound libclang/Python retention to one TU. Only small status
    # tuples cross the pipe; each worker publishes its own potentially large JSON.
    ctx=mp.get_context('spawn');stop=ctx.Event()
    todo=iter(batch);active={};reported={};next_report=0;failure=None
    def launch():
        nonlocal failure
        if stop.is_set():return
        e=next(todo,None)
        if e is None:return
        receive,send=ctx.Pipe(duplex=False)
        p=ctx.Process(target=worker,args=(e,root,build,out,fingerprint,send,stop))
        try:p.start()
        except Exception as error:
            receive.close();send.close();p.close()
            row=unit_row(e,fingerprint);row['error']=repr(error);save_unit(out,row)
            reported[e['id']]=(e['id'],'failed',row['error'])
            failure=row['error'];stop.set()
            return
        send.close();active[p.sentinel]=(p,receive,e)
    try:
        for _ in range(min(jobs,len(batch))):launch()
        while active:
            ready=wait(list(active))
            for sentinel in ready:
                p,receive,e=active.pop(sentinel);p.join()
                try:
                    if p.exitcode!=0:raise RuntimeError(f'Worker exited with code {p.exitcode}')
                    ident,status=receive.recv()
                    error=read(out/'units'/f'{ident:05d}.json.gz')['error'] if status!='ok' else None
                    result=ident,status,error
                except (EOFError,OSError,RuntimeError) as error:
                    # e.g. SIGKILL/OOM: no successful pipe reply is a failed unit,
                    # even if the worker died after publishing but before replying.
                    row=unit_row(e,fingerprint);row['error']=repr(error);save_unit(out,row)
                    result=e['id'],'failed',row['error']
                finally:receive.close();p.close()
                reported[e['id']]=result
                if result[1]!='ok':
                    stop.set()
                    if failure is None:failure=result[2]
            # Inspect every completion in this wave before launching replacements.
            while next_report<len(batch) and batch[next_report]['id'] in reported:
                result=reported.pop(batch[next_report]['id']);print(result[0],result[1],flush=True)
                next_report+=1
            for _ in ready:launch()
        while next_report<len(batch) and batch[next_report]['id'] in reported:
            result=reported.pop(batch[next_report]['id']);print(result[0],result[1],flush=True)
            next_report+=1
    finally:
        # Never terminate in-flight units on a peer failure: let them finish their
        # atomic writes. This also preserves completed files on parent interruption.
        stop.set()
        for p,receive,_ in active.values():
            p.join();receive.close();p.close()
    if failure is not None:raise SystemExit(failure)

def main():
    args=options();assert args.limit>0
    inputs,entries,root,build,out,fingerprint=context(args)
    (out/'units').mkdir(parents=True,exist_ok=True);(out/'traces').mkdir(exist_ok=True)
    (out/'inputs.json').write_text(json.dumps(inputs,ensure_ascii=False,indent=2)+'\n')
    pending=[]
    for e in entries:
        p=out/'units'/f'{e["id"]:05d}.json.gz'
        if p.exists():
            cached=read(p)
            assert cached['status']=='ok',f'Prior failed unit {p}; stop for user decision'
            assert cached['input_digest']==fingerprint
            del cached
        else:pending.append(e)
    print('output='+str(out),flush=True)
    print(f'cached={len(entries)-len(pending)}/{len(entries)}, this batch={min(args.limit,len(pending))}',flush=True)
    batch=pending[:args.limit]
    if args.jobs==1:
        for e in batch:
            ident,status,error=process_unit(e,root,build,out,fingerprint)
            print(ident,status,flush=True)
            if status!='ok':raise SystemExit(error)
    else:parallel_batch(batch,root,build,out,fingerprint,args.jobs)
    done=sum((out/'units'/f'{e["id"]:05d}.json.gz').exists() for e in entries)
    if done==len(entries):
        (out/'complete.txt').write_text('complete\n');print('complete',flush=True)
    else:print('repeat same command for next batch',flush=True)

if __name__=='__main__':main()
