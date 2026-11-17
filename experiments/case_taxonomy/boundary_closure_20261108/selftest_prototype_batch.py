"""Small regression checks for dispatch, checkpointing and failed workers."""
import contextlib
import io
import time
from unittest.mock import patch
import prototype_batch as batch
from common import *

ORIGINAL=batch.process_unit
ROOT=HERE/'prototype_src'
TEST=HERE/'evidence/parallel/scheduler'

def controlled_unit(e,root,build,out,digest):
    scenario=read(out/'scenario.json')
    (out/f'{e["id"]}.started').touch()
    if scenario['kind'] in ('failed','large','exit','eof'):
        if e['id']==0:
            deadline=time.monotonic()+20
            while not all((out/f'{i}.started').exists() for i in range(4)):
                assert time.monotonic()<deadline,'workers did not start'
                time.sleep(.01)
            if scenario['kind'] in ('exit','eof'):os._exit(23 if scenario['kind']=='exit' else 0)
        else:
            deadline=time.monotonic()+20
            while not (out/'units/00000.json.gz').exists():
                assert time.monotonic()<deadline,'failure checkpoint was not saved'
                time.sleep(.01)
    if scenario['kind']=='large' and e['id']==0:
        with patch.object(batch,'Unit',side_effect=RuntimeError('X'*262144)):
            return ORIGINAL(e,root,build,out,digest)
    return ORIGINAL(e,root,build,out,digest)

# Spawn imports this module in each worker, reproducing this test-only wrapper.
batch.process_unit=controlled_unit

def main():
    check_criteria()
    trial=TEST/str(time.time_ns());trial.mkdir(parents=True)
    checks=[]
    for kind in ('success','failed','large','exit','eof'):
        out=trial/kind;out.mkdir();(out/'units').mkdir();(out/'traces').mkdir()
        (out/'scenario.json').write_text(json.dumps({'kind':kind}))
        entries=[{'id':i,'source':ROOT/'public.c','directory':ROOT,
                  'args':['-std=gnu11','-I'+str(ROOT)]} for i in range(8)]
        if kind=='failed':entries[0]['args'].append('-intentional-invalid-option')
        digest=batch.enumeration.digest({'test':kind})
        # Exercise main(), including resume checks and complete marker policy.
        args=batch.argparse.Namespace(arch='riscv',fixture=True,profile=None,limit=8,jobs=4)
        ctx=({'fixture':True,'test':kind},entries,ROOT,None,out,digest)
        output=io.StringIO()
        with patch.object(batch,'options',return_value=args),patch.object(batch,'context',return_value=ctx):
            with contextlib.redirect_stdout(output):
                try:batch.main()
                except SystemExit:
                    assert kind!='success'
                else:assert kind=='success'
        ids=sorted(int(p.name.split('.')[0]) for p in (out/'units').glob('*.json.gz'))
        expected=list(range(8 if kind=='success' else 4))
        assert ids==expected,(kind,ids)
        assert not list((out/'units').glob('*.pending'))
        for ident in ids:
            row=read(out/'units'/f'{ident:05d}.json.gz')
            assert row['input_digest']==digest
            assert row['status']==('failed' if kind!='success' and ident==0 else 'ok')
            if kind=='large' and ident==0:assert len(row['error'])>262144
        assert (out/'complete.txt').exists()==(kind=='success')
        statuses=[line for line in output.getvalue().splitlines() if line and line[0].isdigit()]
        assert [int(line.split()[0]) for line in statuses]==expected,statuses
        before=inputs_manifest((out/'units').glob('*.json.gz'))
        with patch.object(batch,'options',return_value=args),patch.object(batch,'context',return_value=ctx):
            with contextlib.redirect_stdout(io.StringIO()):
                if kind=='success':batch.main()
                else:
                    try:batch.main()
                    except AssertionError as error:assert 'Prior failed unit' in str(error)
                    else:raise AssertionError('failed cache was reused')
        assert before==inputs_manifest((out/'units').glob('*.json.gz'))
        checks.extend([kind+'_atomic_results',kind+'_ordered_statuses',kind+'_resume'])
    result={'passed':True,'checks':checks,'output':str(trial)}
    write('evidence/parallel/scheduler_result.json',result)
    print('batch selftest passed',len(checks),'checks')

if __name__=='__main__':main()
