"""Prepare one isolated O= configuration; build is for Claude's later execution."""
import argparse
from datetime import datetime, timezone
from common import *

def load_config(path):
    values={}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            k,v=line.split('=',1); values[k[7:]]=v
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[9:-11]]='n'
    return values

def validate(profile,path):
    values=load_config(path)
    expected=profile['requests']|profile['expect']
    checks={n:{'expected':v,'actual':values.get(n,'n'),'passed':values.get(n,'n')==v} for n,v in expected.items()}
    return checks,all(r['passed'] for r in checks.values())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('name'); parser.add_argument('action',nargs='?',choices=['prepare','build'],default='prepare')
    parser.add_argument('--jobs',type=int,default=20)
    args=parser.parse_args()
    matrix=read(HERE/'config_matrix.json')
    if args.name=='list':
        for p in matrix['profiles']: print(p['name'],p['arch'],p['status'])
        return
    p=next(r for r in matrix['profiles'] if r['name']==args.name)
    if p['status'].startswith('blocked'):
        raise SystemExit(p['name']+': '+p['status']+'; '+p['remaining_limits'])
    check_criteria()
    assert git('rev-parse','HEAD').strip()=='df2908090cda368b01ff43709f51890076c56157'
    out=Path(p['output']).resolve()
    assert out.parent==Path('/root/work/boundary_build') and out.name=='closure_20261108_'+p['name']
    source_before=git('status','--porcelain=v1')
    assert not source_before,'kernel source tree is not clean'
    run_record={'profile':p['name'],'arch':p['arch'],'output':str(out),'commands':[],
                'matrix_sha256':sha(HERE/'config_matrix.json'),'kernel_head':git('rev-parse','HEAD').strip(),
                'criteria_sha256':check_criteria(),'source_status_before':source_before,
                'kernel_build_executed':False,'completed':False}
    dest=f'config_validation/{p["name"]}.json'
    def call(argv,filename):
        run_record['commands'].append(argv)
        with (out/filename).open('w',encoding='utf-8') as f:
            result=subprocess.run(argv,cwd=KSRC,text=True,stdout=f,stderr=subprocess.STDOUT)
        if result.returncode:
            run_record['failed_command']=argv; run_record['exit_code']=result.returncode
            run_record['last_lines']=(out/filename).read_text(errors='replace').splitlines()[-20:]
            write(dest,run_record)
            raise SystemExit('\n'.join(run_record['last_lines']))
    make=['make',f'O={out}',f'ARCH={p["arch"]}','LLVM=1']
    config=out/'.config'
    if args.action=='prepare':
        if config.exists():
            existing=HERE/dest
            if existing.is_file():
                saved=read(existing)
                if saved.get('completed') and saved.get('config_sha256')==sha(config):
                    checks,ok=validate(p,config)
                    assert ok,checks
                    if saved['matrix_sha256']!=run_record['matrix_sha256']:
                        saved['previous_matrix_sha256']=saved['matrix_sha256']
                        saved['matrix_sha256']=run_record['matrix_sha256']
                        saved['metadata_revalidation_checks']=checks
                        write(dest,saved)
                        (out/'closure_config_verified.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n')
                    print(p['name'],'already prepared and verified',sha(config));return
            raise SystemExit(f'Refuse to overwrite existing unverified configuration: {config}')
        out.mkdir(parents=True,exist_ok=True)
        call(make+['defconfig'],'defconfig.log')
        argv=[str(KSRC/'scripts/config'),'--file',str(config)]
        for n,v in p['requests'].items():
            argv += ['--enable' if v=='y' else '--disable',n] if v in ('y','n') else ['--set-val',n,v]
        call(argv,'scripts_config.log')
        call(make+['olddefconfig'],'olddefconfig.log')
        checks,ok=validate(p,config)
        run_record.update({'checks':checks,'config_sha256':sha(config),
                           'source_status_after':git('status','--porcelain=v1'),'completed':ok})
        run_record['completed_utc']=datetime.now(timezone.utc).isoformat()
        write(dest,run_record)
        assert ok,checks
        assert not run_record['source_status_after'],'source tree changed'
        (out/'closure_config_verified.json').write_text(json.dumps(run_record,ensure_ascii=False,indent=2)+'\n')
        print(p['name'],'olddefconfig verified',len(checks),'checks',sha(config));return
    assert args.jobs>0
    prepared=read(HERE/dest)
    assert prepared['completed'] and prepared['config_sha256']==sha(config)
    assert prepared['matrix_sha256']==run_record['matrix_sha256']
    checks,ok=validate(p,config); assert ok,checks
    run_record['kernel_build_executed']=True
    call(make+[f'-j{args.jobs}'],'build.log')
    call(['python3',str(KSRC/'scripts/clang-tools/gen_compile_commands.py'),'-d',str(out),'-o',str(out/'compile_commands.json')],'compile_commands.log')
    run_record.update({'completed':True,'config_sha256':sha(config),
                      'compile_commands_sha256':sha(out/'compile_commands.json'),
                      'compile_command_entries':len(read(out/'compile_commands.json')),
                      'source_status_after':git('status','--porcelain=v1')})
    assert not run_record['source_status_after']
    write(f'build_validation/{p["name"]}.json',run_record)
    (out/'status.txt').write_text('success\n')
    print(p['name'],'build success',run_record['compile_command_entries'])

if __name__=='__main__': main()
