"""Collect manually scoped old-version evidence; no model or oracle access."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

HERE=Path(__file__).resolve().parent
CASES=HERE.parent
REPO='/root/repos/linux'
VERSIONS={'export':'555a0ce4558d87d5b97c4321f34b19e051c7b0c1',
          'startup':'88b604263f3d6eedae0b1c2c3bbd602d1e2e8775'}
CACHE={}
SOURCES={}


def digest(data):return hashlib.sha256(data).hexdigest()


def source(unit,path):
    key=(unit,path)
    if key not in CACHE:
        raw=subprocess.check_output(['git','-C',REPO,'show',VERSIONS[unit]+':'+path])
        CACHE[key]=raw.decode('utf-8')
        SOURCES[unit+':'+path]={'revision':VERSIONS[unit],'path':path,'sha256':digest(raw)}
    return CACHE[key]


def document(unit,id,path,start,end,kind='source'):
    lines=source(unit,path).splitlines()
    assert 1<=start<=end<=len(lines),(path,start,end,len(lines))
    return {'id':id,'kind':kind,'path':path,'revision':VERSIONS[unit],
            'start_line':start,'end_line':end,
            'text':'\n'.join(f'{n}: {lines[n-1]}' for n in range(start,end+1))}


def window(unit,id,path,needle,before,after):
    lines=source(unit,path).splitlines()
    indices=[i+1 for i,l in enumerate(lines) if needle in l]
    if len(indices)!=1:raise ValueError('Ambiguous scoped anchor: '+path+':'+needle)
    n=indices[0]
    return document(unit,id,path,max(1,n-before),min(len(lines),n+after))


def function(unit,id,path,name):
    text=source(unit,path)
    pattern=r'(?m)^[^\n;{}#]*\b'+re.escape(name)+r'\s*\([^;{}]*?\)\s*\{'
    match=re.search(pattern,text)
    if not match:raise ValueError('Scoped function missing: '+path+':'+name)
    begin=match.end()-1
    depth=0;state='code';i=begin
    while i<len(text):
        c=text[i];n=text[i:i+2]
        if state=='block':
            if n=='*/':state='code';i+=2;continue
        elif state=='line':
            if c=='\n':state='code'
        elif state in ['"',"'"]:
            if c=='\\':i+=2;continue
            if c==state:state='code'
        elif n=='/*':state='block';i+=2;continue
        elif n=='//':state='line';i+=2;continue
        elif c in ['"',"'"]:state=c
        elif c=='{':depth+=1
        elif c=='}':
            depth-=1
            if depth==0:
                return document(unit,id,path,text.count('\n',0,match.start())+1,text.count('\n',0,i)+1)
        i+=1
    raise ValueError('Unclosed scoped function')


def configuration_document(unit,arch):
    if unit=='export':
        rel=f'die_arch_contract_20261013/profiles/old_{arch}_smp'
        receipt=json.loads((CASES/rel/'result.json').read_text())
    else:
        rel=f's390_arch_contract_20261013/runtime/profiles/old_{arch}'
        receipt=json.loads((CASES/rel/'build.json').read_text())
    assert receipt['revision']==VERSIONS[unit]
    p=CASES/rel/'kernel.config';raw=p.read_bytes();lines=raw.decode('utf-8').splitlines()
    keys=['X86_64','S390','SMP','SYSFS','NR_CPUS']
    if unit=='startup':keys+=['SCHED_SMT','SCHED_CORE','SCHED_TOPOLOGY','HOTPLUG_CPU']
    selected=[];positions=[]
    for key in keys:
        hits=[(n,l) for n,l in enumerate(lines,1) if l.startswith('CONFIG_'+key+'=') or l=='# CONFIG_'+key+' is not set']
        assert len(hits)<=1
        if hits:
            positions.append({'generated_line':len(selected)+1,'original_line':hits[0][0]})
            selected.append(hits[0][1])
    path=f'generated/config/{unit}_{arch}.txt'
    target=HERE/path;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('\n'.join(selected)+'\n')
    SOURCES[unit+':config:'+arch]={'path':str(p.relative_to(CASES)),'revision':VERSIONS[unit],
        'sha256':digest(raw),'generated_path':path,'line_map':positions,
        'note':'Selection from actual generated config, not requested flags or model labels.'}
    return {'id':'C_'+arch,'kind':'configuration','path':path,'revision':VERSIONS[unit],
        'start_line':1,'end_line':len(selected),
        'text':'\n'.join(f'{n}: {l}' for n,l in enumerate(selected,1))}


def export_documents():
    u='export'
    common=[document(u,'E_include','include/linux/topology.h',22,40),
        document(u,'E_fallback','include/linux/topology.h',175,218),
        document(u,'E_export','drivers/base/topology.c',1,len(source(u,'drivers/base/topology.c').splitlines())),
        document(u,'E_docs','Documentation/admin-guide/cputopology.rst',1,75,'documentation')]
    x86=[document(u,'E_x86','arch/x86/include/asm/topology.h',95,135),configuration_document(u,'x86')]
    s390=[document(u,'E_s390','arch/s390/include/asm/topology.h',1,len(source(u,'arch/s390/include/asm/topology.h').splitlines())),configuration_document(u,'s390')]
    return common,x86,s390


def startup_documents():
    u='startup'
    common=[function(u,'S_interface','include/linux/topology.h','cpu_smt_mask'),
        function(u,'S_notify','kernel/cpu.c','notify_cpu_starting'),
        function(u,'S_range','kernel/cpu.c','cpuhp_invoke_callback_range'),
        function(u,'S_dispatch','kernel/cpu.c','cpuhp_invoke_callback'),
        window(u,'S_table','kernel/cpu.c','[CPUHP_AP_SCHED_STARTING]',0,5),
        function(u,'S_starting','kernel/sched/core.c','sched_cpu_starting'),
        function(u,'S_core','kernel/sched/core.c','sched_core_cpu_starting'),
        function(u,'S_locks','kernel/sched/core.c','sched_core_lock')]
    x86=[window(u,'S_x86_header','arch/x86/include/asm/topology.h','#define topology_sibling_cpumask',0,4),
        function(u,'S_x86_callin','arch/x86/kernel/smpboot.c','smp_callin'),
        function(u,'S_x86_start','arch/x86/kernel/smpboot.c','start_secondary'),
        function(u,'S_x86_prepare','arch/x86/kernel/smpboot.c','set_cpu_sibling_map'),
        window(u,'S_x86_link','arch/x86/kernel/smpboot.c','#define link_mask',0,7),configuration_document(u,'x86')]
    s390=[window(u,'S_s390_header','arch/s390/include/asm/topology.h','#define topology_sibling_cpumask',0,4),
        function(u,'S_s390_start','arch/s390/kernel/smp.c','smp_start_secondary'),
        function(u,'S_s390_map','arch/s390/kernel/topology.c','cpu_thread_map'),
        function(u,'S_s390_update','arch/s390/kernel/topology.c','update_cpu_masks'),configuration_document(u,'s390')]
    return common,x86,s390


def main():
    if (HERE/'model_ledger.json').exists():raise RuntimeError('Requests already bound; do not regenerate inputs')
    requests=[]
    for unit,groups in [('export',export_documents()),('startup',startup_documents())]:
        common,x86,s390=groups
        for view,docs in [('x86',common+x86),('pair',common+x86+s390),('ablated',common)]:
            id=unit+'_'+view
            data={'id':id,'unit':unit,'view':view,'revision':VERSIONS[unit],
                'scope_note':'Manually selected old-version source regions and extracted actual config; no fix or runtime labels.',
                'documents':docs}
            relative='requests/'+id+'.json';p=HERE/relative;p.parent.mkdir(exist_ok=True)
            p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            requests.append({'id':id,'relative_path':relative,'sha256':digest(p.read_bytes())})
    (HERE/'source_selection.json').write_text(json.dumps(SOURCES,ensure_ascii=False,indent=2)+'\n')
    manifest={'max_requests':6,'max_total_tokens':80000,'max_output_tokens':3000,
        'hidden_input_reserve_tokens':8192,'requests':requests}
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'prepared_requests':len(requests),'fixed_old_versions':VERSIONS,
        'source_records':len(SOURCES),'model_calls':0}))


if __name__=='__main__':main()
